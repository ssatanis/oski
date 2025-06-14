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
from core.utils.minio_client import MinIOClient 
from core.prompts.gemini import OSCE_KEYFRAME_CAPTIONER_PROMPT
from core.utils.embedding_utils import (
    load_clip_model_and_processor,
    load_sentence_transformer_model,
    generate_clip_text_embedding,
    generate_sentence_embedding,
    DEFAULT_CLIP_EMBEDDING_DIM, 
    DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM
)
from core.tools.schemas import KeyframeDescriptionOutput
from core.vector_store.schemas import SearchResult
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever, VideoKeyframeMetadata 
from core.utils.minio_client import MinIOClient 
from core.vector_store.utils import retrieve_relevant_keyframes, load_pil_images_from_retrieved_results
from core.config.config import settings 
from core.vector_store.qdrant_client import QdrantClient
from core.tools.base import Tool, ToolCategory

def generate_keyframes_caption_evidence_with_gemini(
        gemini_client, 
        pil_images: List[Image.Image], 
):
    """
    Generate captions for keyframes using Gemini.

    Args:
        client: The Gemini client instance.
        pil_images (List[Image.Image]): List of PIL images representing keyframes.

    Returns:
        List[KeyframeDescriptionOutput]: List of descriptions for each keyframe.
    """
    try:
        gemini_image_processor = GeminiImageBatchProcessor(
            client=gemini_client,
            prompt_template=OSCE_KEYFRAME_CAPTIONER_PROMPT,
            output_schema=KeyframeDescriptionOutput,
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
    
def format_keyframe_captioner_output(
    retrieved_keyframes_results: List[SearchResult[VideoKeyframeMetadata]], 
    keyframe_description_results: List[KeyframeDescriptionOutput],
    minio_client: MinIOClient
):
    keyframe_captioner_tool_output = []

    for retrieved_result, keyframe_description in zip(retrieved_keyframes_results, keyframe_description_results):
        keyframe_image_url = minio_client.get_presigned_url(retrieved_result.metadata.minio_path)

        keyframe_captioner_tool_output.append({
            "keyframe_id": retrieved_result.id,
            "keyframe_image_url": keyframe_image_url,
            "timestamp": retrieved_result.metadata.timestamp,
            "keyframe_description": keyframe_description["description"]
        })

    return keyframe_captioner_tool_output 

class KeyframeCaptionerTool(Tool):
    TOOL_NAME = "keyframe_captioner"
    TOOL_CATEGORY = ToolCategory.VISUAL 
    TOOL_DESCRIPTION = (
        "This tool returns concise and semantically rich descriptions for each retrieved relevant keyframe, ", 
        "which will be used to provide visual evidence for the assessment of the OSCE video against a specific rubric question."
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
            prompt_template=OSCE_KEYFRAME_CAPTIONER_PROMPT,
            output_schema=KeyframeDescriptionOutput,
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

            keyframe_description_results = self.gemini_batch_image_processor.process_batch(
                pil_images=pil_images, 
                response_format="json"
            )
        
            formatted_output = format_keyframe_captioner_output(
                retrieved_keyframes_results=retrieved_keyframes_result, 
                keyframe_description_results=keyframe_description_results,
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

    # print(retrieved_keyframes_results)

    # pil_images = load_pil_images_from_retrieved_results(
    #     results=retrieved_keyframes_results, 
    #     minio_client=minio_client
    # )

    # print(f"Number of keyframes retrieved: {len(pil_images)}")

    # # Generate captions for keyframes using Gemini
    # keyframe_description_results = generate_keyframes_caption_evidence_with_gemini(
    #     gemini_client=gemini_client, 
    #     pil_images=pil_images
    # )

    # formatted_output = format_keyframe_captioner_output(
    #     retrieved_keyframes_results=retrieved_keyframes_results, 
    #     keyframe_description_results=keyframe_description_results
    # )
    # print(formatted_output)

    keyframe_captioner_tool = KeyframeCaptionerTool(
        gemini_client=gemini_client, 
        minio_client=minio_client
    )

    keyframe_captioner_output = keyframe_captioner_tool.run(
        retrieved_keyframes_result=retrieved_keyframes_results
    )

    print(keyframe_captioner_output)

    end = time.time()
    print(f"Time taken to generate keyframe captions: {end - start:.2f} seconds")

