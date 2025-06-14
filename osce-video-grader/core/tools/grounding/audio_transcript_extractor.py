import os
import time  
from typing import List, Dict, Any

from PIL import Image
from qdrant_client.http.models import Filter as QdrantFilter, FieldCondition, MatchValue

from core.utils.gemini_utils import (
    load_gemini_client,
    GeminiImageBatchProcessor
)
from core.prompts.gemini import OSCE_KEYFRAME_CAPTIONER_PROMPT
from core.utils.embedding_utils import (
    load_clap_model_and_processor,
    load_sentence_transformer_model,
    generate_clap_text_embedding,
    generate_sentence_embedding,
    DEFAULT_CLAP_EMBEDDING_DIM, 
    DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM
)
from core.vector_store.schemas import SearchResult
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever, AudioSegmentMetadata
from core.utils.minio_client import MinIOClient 
from core.vector_store.utils import retrieve_relevant_audio_segments
from core.config.config import settings 
from core.vector_store.qdrant_client import QdrantClient
from core.tools.base import Tool, ToolCategory

def format_audio_transcript_output(
    retrieved_audio_segments_results: List[SearchResult[AudioSegmentMetadata]],
    minio_client: MinIOClient
) -> List[dict]:
    """
    Format the audio segments and their transcripts into a structured output.

    Args:
        audio_segments (List[SearchResult]): List of retrieved audio segments.

    Returns:
        List[dict]: Formatted output with start time, end time, audio segment ID, and transcript.   
    """
    audio_transcripts_tool_output = []

    for seg in retrieved_audio_segments_results:
        meta = seg.metadata
        audio_segment_url = minio_client.get_presigned_url(meta.minio_path)

        audio_transcripts_tool_output.append({
            "start_time": meta.start_time,
            "end_time": meta.end_time,
            "audio_segment_id": seg.id,
            "transcript": meta.transcript, 
            "audio_segment_url": audio_segment_url
        })

    return audio_transcripts_tool_output

class AudioTranscriptExtractorTool(Tool):
    TOOL_NAME = "audio_transcript_extractor"
    TOOL_CATEGORY = ToolCategory.AUDIO
    TOOL_DESCRIPTION = (
        "This tool extracts diarized transcripts from retrieved relevant audio segments. ",
        "The output is a list of the transcripts for each audio segment and their corresponding start and end times. ",
        "The output will be used used to provide evidence for the student's performance in the OSCE video on a specific rubric question related to communication between the student and the patient.",
    )

    def __init__(
        self, 
        minio_client: MinIOClient
    ):
        super().__init__(
            name=self.TOOL_NAME,
            category=self.TOOL_CATEGORY, 
            description=self.TOOL_DESCRIPTION
        )

        self.minio_client = minio_client

    def run(
        self, 
        retrieved_audio_segments_results: List[SearchResult[AudioSegmentMetadata]]
    ):
        try: 
            if not retrieved_audio_segments_results:
                raise ValueError("No audio segments retrieved.")

            formatted_output = format_audio_transcript_output(
                retrieved_audio_segments_results,
                minio_client=self.minio_client
            )
            return formatted_output
        
        except Exception as e:
            print(f"An error occured while running the {self.name} tool: {e}")
            return None
        

if __name__ == "__main__":
    try:
        # Load models 
        clap_model, clap_processor = load_clap_model_and_processor()
        sentence_transformers_model = load_sentence_transformer_model()
        gemini_client = load_gemini_client()

        minio_client = MinIOClient()
        qdrant_generic_client = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key,
            use_https=settings.qdrant.use_https
        )

        audio_segment_retriever = AudioSegmentRetriever(
            client=qdrant_generic_client,
            audio_segment_embedding_vector_size=DEFAULT_CLAP_EMBEDDING_DIM,
            audio_segment_transcript_embedding_vector_size=DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM
        )
    except Exception as e:
        print(f"Failed to initialize embedding models and retriever: {e}")
        exit(1)

    start = time.time()

    video_file_path = os.path.join("../sample_osce_videos", "osce-physical-exam-demo-video-1.mp4")

    # Retrieve relevant keyframes 
    rubric_question = "Did the student use a stethoscope?"

    query_clap_emb = generate_clap_text_embedding(rubric_question, clap_model, clap_processor)
    query_sentence_emb = generate_sentence_embedding(rubric_question, sentence_transformers_model)

    search_filter = QdrantFilter(
        must=[
            FieldCondition(
                key="video_id",
                match=MatchValue(value="46dc4868-15e9-4f27-b277-726bf9f0023c")
            )
        ]
    )

    retrieved_audio_segments_results = retrieve_relevant_audio_segments(
        rubric_question=rubric_question, 
        query_clap_emb=query_clap_emb, 
        query_sentence_emb=query_sentence_emb,
        retriever=audio_segment_retriever,
        minio_client=minio_client,
        search_filter=search_filter, 
        search_strategy="transcript",
        show_results=True,
        score_threshold=0.65
    )

    print(retrieved_audio_segments_results)

    # formatted_audio_transcripts = format_audio_transcript_output(retrieved_audio_segments_results)
    # print(formatted_audio_transcripts)

    audio_transcript_extractor_tool = AudioTranscriptExtractorTool(minio_client=minio_client)
    audio_transcript_extractor_output = audio_transcript_extractor_tool.run(retrieved_audio_segments_results)
    print(audio_transcript_extractor_output)

    end = time.time()
    print(f"Time taken to generate keyframe captions: {end - start:.2f} seconds")

