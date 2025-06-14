import io 
from typing import List, Tuple, Dict, Literal, Optional  

import uuid 
import numpy as np 
import soundfile as sf 
from PIL import Image 
from qdrant_client.http.models import Filter as QdrantFilter, FieldCondition, MatchValue

from core.utils.video_processor import plot_keyframes
from core.utils.audio_processor import ProcessedAudioSegment
from core.vector_store.schemas import SearchResult
from core.utils.minio_client import MinIOClient
from core.utils.audio_processor import DEFAULT_SAMPLING_RATE
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeMetadata, VideoKeyframeRetriever
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever, AudioSegmentMetadata 

def index_keyframes(
    video_id: str,
    extracted_keyframes_data: List[Tuple[Image.Image, float]],
    keyframe_images_clip_embeddings: np.ndarray, 
    keyframe_descriptions_sent_embeddings: np.ndarray, 
    keyframe_descriptions: List[Dict[str, str]],
    minio_client: MinIOClient,
    video_keyframe_retriever: VideoKeyframeRetriever
):
    """End-to-end function for indexing keyframes into the vector store."""
    successfully_indexed_count = 0

    try:
        for i, (pil_image, timestamp) in enumerate(extracted_keyframes_data):
            keyframe_image_clip_emb = keyframe_images_clip_embeddings[i]
            keyframe_desc_sent_emb = keyframe_descriptions_sent_embeddings[i]
            keyframe_desc_text = keyframe_descriptions[i]["description"]

            keyframe_id = str(uuid.uuid4())

            # Store keyframe image in MinIO 
            img_byte_arr = io.BytesIO()
            pil_image.save(
                img_byte_arr,
                format='JPEG',
                quality=85
            )
            image_bytes = img_byte_arr.getvalue()

            minio_path = minio_client.store_video_keyframe(
                image_data=image_bytes, 
                keyframe_id=keyframe_id, 
                image_format="JPEG"
            )

            if not minio_path:
                print(f"Failed to store keyframe image in MinIO for keyframe {i + 1}. Skipping.")
                continue
            else:
                print(f"Stored keyframe image in MinIO at path: {minio_path}") 

            # Prepare video keyframe metadata and index 
            video_keyframe_metadata = VideoKeyframeMetadata(
                id=keyframe_id,
                video_id=video_id,
                frame_number=i,
                timestamp=timestamp,
                description=keyframe_desc_text,
                minio_path=minio_path
            )

            success_indexing = video_keyframe_retriever.index_keyframe(
                keyframe_id=keyframe_id,
                keyframe_image_embedding=keyframe_image_clip_emb,
                keyframe_description_embedding=keyframe_desc_sent_emb,
                metadata=video_keyframe_metadata
            )

            if success_indexing:
                successfully_indexed_count += 1
                print(f"Successfully indexed keyframe {i + 1} with ID: {keyframe_id}")
            else:
                print(f"Failed to index keyframe {i + 1} with ID: {keyframe_id}. Skipping.")

        return True 
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False 
    

def retrieve_relevant_keyframes(
    rubric_question: str, 
    retriever: VideoKeyframeRetriever,
    query_clip_emb: np.ndarray, 
    query_sentence_emb: np.ndarray,  
    search_filter: QdrantFilter, 
    search_strategy: Literal["hybrid", "clip", "description"] = "description",
    top_k: int = 5, 
    hybrid_clip_search_weight: float = 0.3, 
    hybrid_description_search_weight: float = 0.7,
    show_results: bool = False, 
    display_keyframes: bool = False,
    minio_client: Optional[MinIOClient] = None, 
    score_threshold: Optional[float] = None
):
    """
    End-to-end function for retrieving relevant keyframes based on a rubric question.

    Args:
        rubric_question (str): Rubric question. 
        retriever: The video keyframe retriever instance. 
        query_clip_emb: The query's CLIP text embedding. 
        query_sentence_emb: The query's sentence transformers embedding. 
        search_filter: The search filter for retrieval from the Qdrant vector store. 
        search_strategy (str): The search strategy for retrieval i.e. 
                            "clip" (retrieves based on CLIP embeddings similarity between query and keyframes), 
                            "description" (retrieves based on sentence embeddings match between query and keyframe descriptions), 
                            "hybrid" (combines both with re-ranking.).
        top_k (int): The number of keyframes to retrieve. 
        hybrid_clip_search_weight (float): The weight for CLIP (if using hybrid retrieval).
        hybrid_description_search_weight (float): The weight for description (if using hybrid retrieval).
        show_results (bool): Determines whether to print the results of the retrieved keyframes. 
        display_keyframes (bool): Determines whether to plot the retrieved keyframes.
        minio_client: The MinIO client for retrieving keyframe files. Required for plottng keyframes.
    """
    try:
        if search_strategy == "hybrid":
            search_results: List[SearchResult[VideoKeyframeMetadata]] = retriever.search_keyframes_hybrid(
                query_text=rubric_question, 
                query_clip_embedding=query_clip_emb, 
                query_description_embedding=query_sentence_emb, 
                limit=top_k, 
                search_filter=search_filter,
                clip_weight=hybrid_clip_search_weight, 
                description_weight=hybrid_description_search_weight
            )
        else:
            search_results: List[SearchResult[VideoKeyframeMetadata]] = retriever.search_keyframes_by_description( 
                query_sentence_embedding=query_sentence_emb, 
                limit=top_k, 
                search_filter=search_filter
            )


        if not search_results:
            print(f"No relevant keyframes found for query: '{rubric_question}'")
            return []
        
        # Filter results based on score threshold if provided
        if score_threshold is not None:
            search_results = [
                result for result in search_results 
                if result.score >= score_threshold
            ]
        
        # Debugging
        keyframe_images_to_plot: List[Tuple[Image.Image, float]] = []

        if show_results:
            for i, result in enumerate(search_results):
                print(f"\n  --- Result {i+1} ---")
                print(f"    Keyframe ID: {result.id}")
                print(f"    Score: {result.score:.4f}") # This is the re-ranked score
                print(f"    Timestamp: {result.metadata.timestamp:.2f}s")
                print(f"    MinIO Path: {result.metadata.minio_path}")
                print(f"    Video ID: {result.metadata.video_id}")
                print(f"    Generated Description: {result.metadata.description}") # Print preview

        if display_keyframes:
            if not minio_client:
                print("MinIO Client is required to plot the keyframes.") 
            else: 
                for i, result in enumerate(search_results):
                    # Fetch image from MiniIO for plotting 
                    try: 
                        path_parts = result.metadata.minio_path.split("/", 1)

                        if len(path_parts) == 2:
                            bucket_name, object_name = path_parts 

                            image_bytes = minio_client.retrieve_object_data(
                                bucket_name, 
                                object_name 
                            )

                            if image_bytes: 
                                pil_img = Image.open(io.BytesIO(image_bytes))
                                keyframe_images_to_plot.append((pil_img, result.metadata.timestamp))
                            
                            else:
                                print(f"Could not retrieve image data from MinIO for: {result.metadata.minio_path}")

                    except Exception as e:
                        print(f"Error retrieving/processing image from {result.metadata.minio_path}")

                plot_keyframes(
                    keyframe_images_to_plot, 
                    max_cols=5, 
                    fig_title=f"Top retrieved keyframes for: {rubric_question}"
                )
            
        return search_results
    
    except Exception as e:
        print(f"Error during video keyframe retrieval: {e}")
        return None 
    
def load_pil_images_from_retrieved_results(results: List[SearchResult[VideoKeyframeMetadata]], minio_client: MinIOClient) -> List[Image.Image]:
    """
    Load PIL images from the retrieved keyframe results using MinIO client.

    Args:
        results: List of search results containing keyframe metadata.
        minio_client: The MinIO client to retrieve images.

    Returns:
        List of PIL Image objects.
    """
    pil_images = []
    
    for result in results:
        try:
            path_parts = result.metadata.minio_path.split("/", 1)

            if len(path_parts) == 2:
                bucket_name, object_name = path_parts 

                image_bytes = minio_client.retrieve_object_data(
                    bucket_name, 
                    object_name 
                )

                if image_bytes: 
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    pil_images.append(pil_img)
                else:
                    print(f"Could not retrieve image data from MinIO for: {result.metadata.minio_path}")

        except Exception as e:
            print(f"Error retrieving/processing image from {result.metadata.minio_path}: {e}")

    return pil_images

def index_audio_segments(
    video_id: str,
    processed_audio_segments: List[ProcessedAudioSegment],
    audio_segments_clap_embeddings: np.ndarray, 
    audio_segments_transcript_sentence_embeddings: np.ndarray, 
    minio_client: MinIOClient,
    audio_segment_retriever: AudioSegmentRetriever, 
    sampling_rate: int = DEFAULT_SAMPLING_RATE
):
    """End-to-end function for indexing audio segments into the vector store."""
    successfully_indexed_count = 0

    try:
        for i, audio_segment in enumerate(processed_audio_segments):
            audio_segment_clap_embedding = audio_segments_clap_embeddings[i]
            audio_segments_transcript_sentence_embedding = audio_segments_transcript_sentence_embeddings[i]

            segment_id = str(uuid.uuid4())

            minio_path = minio_client.store_audio_segment(
                audio_segment["audio"], 
                sampling_rate, 
                segment_id
            )

            if not minio_path:
                print(f"Failed to store audio segment in MinIO for segment {i + 1}. Skipping.")
                continue
            else:
                print(f"Stored audio segment in MinIO at path: {minio_path}") 

            # Prepare audio segment metadata and index 
            audio_segment_metadata = AudioSegmentMetadata(
                id=segment_id,
                minio_path=minio_path, 
                video_id=video_id,
                start_time=audio_segment["start"], 
                end_time=audio_segment["end"],
                duration=audio_segment["end"]-audio_segment["end"], 
                sample_rate=sampling_rate, 
                transcript=audio_segment["transcript"], 
                emotion=audio_segment["emotion"],
                emotion_confidence_score=audio_segment["emotion_confidence_score"]
            )

            success_indexing = audio_segment_retriever.index_segment(
                segment_id=segment_id,
                audio_segment_embedding=audio_segment_clap_embedding,
                audio_segment_transcript_embedding=audio_segments_transcript_sentence_embedding,
                metadata=audio_segment_metadata
            )

            if success_indexing:
                successfully_indexed_count += 1
                print(f"Successfully indexed audio segment {i + 1} with ID: {segment_id}")
            else:
                print(f"Failed to index audio segment {i + 1} with ID: {segment_id}. Skipping.")

        return True 
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False 

def retrieve_relevant_audio_segments(
    rubric_question: str, 
    retriever: AudioSegmentRetriever,
    query_clap_emb: np.ndarray, 
    query_sentence_emb: np.ndarray,  
    search_filter: QdrantFilter, 
    search_strategy: Literal["hybrid", "clap", "transcript"] = "transcript",
    top_k: int = 5, 
    hybrid_clap_search_weight: float = 0.3, 
    hybrid_transcript_search_weight: float = 0.7,
    show_results: bool = False, 
    minio_client: Optional[MinIOClient] = None, 
    score_threshold: Optional[float] = None
):
    """
    End-to-end function for retrieving relevant audio segments based on the rubric question.

    Args:
        rubric_question (str): Rubric question. 
        retriever: The video keyframe retriever instance. 
        query_clap_emb: The query's CLIP text embedding. 
        query_sentence_emb: The query's sentence transformers embedding. 
        search_filter: The search filter for retrieval from the Qdrant vector store. 
        search_strategy: The search strategy for retrieval i.e. 
                            "clap" (retrieves based on CLAP embeddings similarity between query and audio segments), 
                            "transcript" (retrieves based on sentence embeddings match between query and audio segment transcripts), 
                            "hybrid" (combines both with re-ranking.).
        top_k: The number of audio segments to retrieve. 
        hybrid_clap_search_weight: The weight for CLAP based search.
        hybrid_transcript_search_weight: The weight for transcript based search.
        show_results: Determines whether to print the results for the retrieved audio segments. 
        minio_client: The MinIO client. Required if audio segment files need to be fetched.
    """
    try:
        if search_strategy == "hybrid":
            search_results: List[SearchResult[AudioSegmentMetadata]] = retriever.search_audio_segments_hybrid(
                query_text=rubric_question, 
                query_clap_embedding=query_clap_emb, 
                query_sentence_embedding=query_sentence_emb, 
                limit=top_k, 
                search_filter=search_filter,
                clap_weight=hybrid_clap_search_weight,
                transcript_weight=hybrid_transcript_search_weight,
            )
        else:
            search_results: List[SearchResult[AudioSegmentMetadata]] = retriever.search_audio_segments_by_transcript( 
                query_sentence_embedding=query_sentence_emb, 
                limit=top_k, 
                search_filter=search_filter
            )


        if not search_results:
            print(f"No relevant audio segments found for query: '{rubric_question}'")
            return []
        
        # Filter results based on score threshold if provided
        if score_threshold is not None:
            search_results = [
                result for result in search_results 
                if result.score >= score_threshold
            ]

        if show_results:
            for i, result in enumerate(search_results):
                print(f"\n  --- Result {i+1} ---")
                print(f"    Audio segment ID: {result.id}")
                print(f"    Score: {result.score:.4f}") # This is the re-ranked score
                print(f"    Start time: {result.metadata.start_time:.2f}s")
                print(f"    End time: {result.metadata.end_time:.2f}s")
                print(f"    Duration: {result.metadata.duration:.2f}s")
                print(f"    End time: {result.metadata.end_time:.2f}s")
                print(f"    MinIO Path: {result.metadata.minio_path}")
                print(f"    Video ID: {result.metadata.video_id}")
                print(f"    Transcript: {result.metadata.transcript}") 
                print(f"    Emotion: {result.metadata.emotion}") 
                print(f"    Emotion confidence score: {result.metadata.emotion_confidence_score}") 
                print(f"    Sampling rate: {result.metadata.sample_rate}") 
                # Print preview 

        return search_results

    except Exception as e:
        print(f"Error during audio segment retrieval: {e}")
        return None 