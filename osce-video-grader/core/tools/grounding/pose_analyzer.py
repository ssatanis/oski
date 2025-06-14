import os
import time  
from typing import List, Dict, Any

from PIL import Image
from google import genai 
from qdrant_client.http.models import Filter as QdrantFilter, FieldCondition, MatchValue

from core.utils.gemini_utils import (
    load_gemini_client,
    GeminiImageBatchProcessor
)
from core.prompts.gemini import OSCE_KEYFRAME_POSE_ANALYZER_PROMPT
from core.utils.embedding_utils import (
    load_clip_model_and_processor,
    load_sentence_transformer_model,
    generate_clip_text_embedding,
    generate_sentence_embedding,
    DEFAULT_CLIP_EMBEDDING_DIM, 
    DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM
)
from core.tools.schemas import PoseAnalysisOutput
from core.vector_store.schemas import SearchResult
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever, VideoKeyframeMetadata
from core.utils.minio_client import MinIOClient 
from core.vector_store.utils import retrieve_relevant_keyframes, load_pil_images_from_retrieved_results
from core.config.config import settings 
from core.vector_store.qdrant_client import QdrantClient
from core.tools.base import Tool, ToolCategory

def generate_scene_interaction_evidence_with_gemini(
        gemini_client, 
        pil_images: List[Image.Image], 
):
    """
    Generate captions for keyframes using Gemini.

    Args:
        client: The Gemini client instance.
        pil_images (List[Image.Image]): List of PIL images representing keyframes.

    Returns:
        List[PoseAnalysisOutput]: List of descriptions for each keyframe.
    """
    try:
        gemini_image_processor = GeminiImageBatchProcessor(
            client=gemini_client,
            prompt_template=OSCE_KEYFRAME_POSE_ANALYZER_PROMPT,
            output_schema=PoseAnalysisOutput,
            rate_limit_calls=10,
            rate_limit_period=60,
            max_retries=5,
            max_backoff=120,
            max_workers=4,
        )

        results = gemini_image_processor.process_batch(
            pil_images=pil_images, 
            response_format="json"
        )

        return results 
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    
def format_pose_analysis_output(
    retrieved_keyframes_results: List[SearchResult[VideoKeyframeMetadata]], 
    pose_analysis_results: List[PoseAnalysisOutput],
    minio_client: MinIOClient
):
    pose_analyzer_tool_output = []

    for kf_res, poses in zip(retrieved_keyframes_results, pose_analysis_results):
        ts = kf_res.metadata.timestamp
        kf_id = kf_res.id
        image_url = minio_client.get_presigned_url(kf_res.metadata.minio_path)

        for entry in poses["detected_poses"]:
            pose_analyzer_tool_output.append({
                "timestamp": ts,
                "keyframe_id": kf_id,
                "keyframe_image_url": image_url,
                "person_label": entry["person_label"],
                "pose": entry["pose"],
                "gaze": entry["gaze_direction"],
            })

    return pose_analyzer_tool_output

class PoseAnalyzerTool(Tool):
    TOOL_NAME = "pose_analyzer"
    TOOL_CATEGORY = ToolCategory.VISUAL 
    TOOL_DESCRIPTION = (
        "This tool analyzes keyframes from an OSCE video to detect poses and gaze directions of individuals. ",
        "The output of this tool is a list of detected poses and gaze directions for each keyframe. ",
        "The output will be used to provide evidence for the student's performance in the OSCE video based on a specific rubric question related to student and patient positioning and interaction."
    )

    def __init__(
        self, 
        gemini_client: genai.Client, 
        minio_client: MinIOClient
    ):
        super().__init__(
            name=self.TOOL_NAME, 
            category=self.TOOL_CATEGORY, 
            description=self.TOOL_DESCRIPTION
        )

        self.gemini_batch_image_processor = GeminiImageBatchProcessor(
            client=gemini_client,
            prompt_template=OSCE_KEYFRAME_POSE_ANALYZER_PROMPT,
            output_schema=PoseAnalysisOutput,
            rate_limit_calls=10,
            rate_limit_period=60,
            max_retries=5,
            max_backoff=120,
            max_workers=4,
        )
        self.minio_client = minio_client  

    def run(
        self, 
        retrieved_keyframes_result: List[SearchResult[VideoKeyframeMetadata]]
    ) -> List[Dict[str, Any]]:
        try:
            pil_images = load_pil_images_from_retrieved_results(
                results=retrieved_keyframes_result, 
                minio_client=self.minio_client
            )

            pose_analysis_results = self.gemini_batch_image_processor.process_batch(
                pil_images=pil_images, 
                response_format="json"
            )
        
            formatted_output = format_pose_analysis_output(
                retrieved_keyframes_results=retrieved_keyframes_result, 
                pose_analysis_results=pose_analysis_results,
                minio_client=self.minio_client
            )
            return formatted_output

        except Exception as e: 
            print(f"An error occurred while running the {self.name} tool: {e}.")
            return None 



if __name__ == "__main__":
    try:
        # Load models 
        clip_model, clip_processor = load_clip_model_and_processor()
        sentence_transformers_model = load_sentence_transformer_model()
        gemini_client = load_gemini_client()

        minio_client = MinIOClient()
        qdrant_generic_client = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key,
            use_https=settings.qdrant.use_https
        )

        video_keyframe_retriever = VideoKeyframeRetriever(
            client=qdrant_generic_client,
            keyframe_image_embedding_vector_size=DEFAULT_CLIP_EMBEDDING_DIM,
            keyframe_description_embedding_vector_size=DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM
        )
    except Exception as e:
        print(f"Failed to initialize embedding models and retriever: {e}")
        exit(1)

    start = time.time()

    video_file_path = os.path.join("../sample_osce_videos", "osce-physical-exam-demo-video-1.mp4")

    # Retrieve relevant keyframes 
    rubric_question = "Did the student use a stethoscope?"

    query_clip_emb = generate_clip_text_embedding(rubric_question, clip_model, clip_processor)
    query_sentence_emb = generate_sentence_embedding(rubric_question, sentence_transformers_model)

    search_filter = QdrantFilter(
        must=[
            FieldCondition(
                key="video_id",
                match=MatchValue(value="46dc4868-15e9-4f27-b277-726bf9f0023c")
            )
        ]
    )

    retrieved_keyframes_results = retrieve_relevant_keyframes(
        rubric_question=rubric_question, 
        query_clip_emb=query_clip_emb, 
        query_sentence_emb=query_sentence_emb,
        retriever=video_keyframe_retriever,
        minio_client=minio_client,
        search_filter=search_filter, 
        score_threshold=0.65, 
        display_keyframes=True
    )

    print(retrieved_keyframes_results)

    pil_images = load_pil_images_from_retrieved_results(
        results=retrieved_keyframes_results, 
        minio_client=minio_client
    )

    print(f"Number of keyframes retrieved: {len(pil_images)}")

    # # Generate captions for keyframes using Gemini
    # pose_analysis_results = generate_scene_interaction_evidence_with_gemini(
    #     gemini_client=gemini_client, 
    #     pil_images=pil_images
    # )

    # print(pose_analysis_results)

    # formatted_results = format_pose_analysis_output(
    #     retrieved_keyframes_results=retrieved_keyframes_results, 
    #     pose_analysis_results=pose_analysis_results
    # )
    # print(formatted_results)

    pose_analyzer_tool = PoseAnalyzerTool(
        gemini_client=gemini_client, 
        minio_client=minio_client
    )

    pose_analyzer_output = pose_analyzer_tool.run(
        retrieved_keyframes_result=retrieved_keyframes_results
    )

    print(pose_analyzer_output)

    end = time.time()
    print(f"Time taken to generate keyframe captions: {end - start:.2f} seconds")

