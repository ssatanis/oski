import os 
from typing import List, Optional, Dict, Any 

from google import genai 
from transformers import (
    ClapModel,
    ClapProcessor,
    CLIPModel,
    CLIPProcessor 
)
from sentence_transformers import SentenceTransformer 
from qdrant_client.http.models import Filter as QdrantFilter, FieldCondition, MatchValue

from core.tools.base import Tool, ToolCategory
from core.vector_store.qdrant_client import QdrantClient
from core.utils.minio_client import MinIOClient  
from core.utils.cache_manager import JsonCache
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever
from core.tools.repository import (
    KeyframeCaptionerTool, 
    AudioTranscriptExtractorTool, 
    PoseAnalyzerTool, 
    SceneInteractionAnalyzerTool, 
    ObjectDetectorTool, 
    TemporalActionSegmentationTool
)
from core.vector_store.schemas import SearchResult 
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentMetadata 
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeMetadata
from core.utils.embedding_utils import (
    generate_clip_text_embedding,
    generate_sentence_embedding,
    generate_clap_text_embedding
)
from core.vector_store.utils import (
    retrieve_relevant_keyframes, 
    retrieve_relevant_audio_segments
)

class Executor:
    DEFAULT_AUDIO_SEGMENT_RETRIEVER_SCORE_THRESHOLD = 0.6 
    DEFAULT_VIDEO_KEYFRAME_RETRIEVER_SCORE_THRESHOLD = 0.65
    TEMPORAL_CACHE_CATEGORY = "temporal_action_segmenter_outputs"

    def __init__(
        self, 
        gemini_client: genai.Client, 
        minio_client: MinIOClient, 
        qdrant_client: QdrantClient, 
        clap_model: ClapModel, 
        clap_processor: ClapProcessor, 
        clip_model: CLIPModel, 
        clip_processor: CLIPProcessor, 
        sentence_transformers_model: SentenceTransformer,
        tool_repository: List[Tool],
        cache_manager: Optional[JsonCache] = None 
    ):
        self.gemini_client = gemini_client
        self.minio_client = minio_client
        self.qdrant_client = qdrant_client
        self.clap_model = clap_model
        self.clap_processor = clap_processor
        self.clip_model = clip_model
        self.clip_processor = clip_processor
        self.sentence_transformers_model = sentence_transformers_model
        self.tool_repository = tool_repository
        
        self.tool_map = {tool.TOOL_NAME: tool for tool in tool_repository}

        # Initialize retrievers 
        self.video_keyframe_retriever = VideoKeyframeRetriever(
            client=self.qdrant_client
        )

        self.audio_segment_retriever = AudioSegmentRetriever(
            client=self.qdrant_client
        )

        self.cache_manager = cache_manager if cache_manager is not None else JsonCache()

    def _get_tool_instance(self, tool_name: str) -> Optional[Tool]:
        tool_class = self.tool_map.get(tool_name)

        if not tool_class:
            print(f"Warning: Tool '{tool_name}' not found in the tool repository.")
            return None
        
        try:
            if tool_name == AudioTranscriptExtractorTool.TOOL_NAME:
                return tool_class(
                    minio_client=self.minio_client
                )
            
            elif tool_name in [
                KeyframeCaptionerTool.TOOL_NAME, 
                ObjectDetectorTool.TOOL_NAME, 
                PoseAnalyzerTool.TOOL_NAME, 
                SceneInteractionAnalyzerTool.TOOL_NAME
            ]:
                return tool_class(
                    gemini_client=self.gemini_client, 
                    minio_client=self.minio_client
                )
            elif tool_name == TemporalActionSegmentationTool.TOOL_NAME:
                return tool_class(
                    gemini_client=self.gemini_client
                )
            else:
                print(f"Warning: Could not instantiate tool '{tool_name}'.")
                return None
            
        except Exception as e:
            print(f"Error instantiating tool '{tool_name}': {e}")
            return None
        
    def run(
        self, 
        rubric_question: str, 
        selected_tools: List[Tool],
        video_file_path: Optional[str] = None, 
        video_id: Optional[str] = None, 
        action_vocabulary: Optional[Dict[str, str]] = None 
    ):
        tool_outputs = {}
        retrieved_audio_segments_cache: Optional[List[SearchResult[AudioSegmentMetadata]]] = None 
        retrieved_video_keyframes_cache: Optional[List[SearchResult[VideoKeyframeMetadata]]] = None 

        if not video_id:
            print("Error: video_id must be provided to Executor.")
            return {"error": "video_id is missing."}


        selected_tool_names = [tool.TOOL_NAME for tool in selected_tools]

        search_filter = QdrantFilter(
            must=[
                FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id)
                )
            ]
        )

        for tool_name in selected_tool_names:
            tool_instance = self._get_tool_instance(tool_name)

            if not tool_instance:
                tool_outputs[tool_name] = None 
                continue 

            print(f"\nExecutor: Preparing to run tool '{tool_name}' for rubric question: '{rubric_question}'")

            try:
                tool_category = tool_instance.TOOL_CATEGORY

                if tool_category == ToolCategory.AUDIO:
                    if retrieved_audio_segments_cache is None:
                        print("Executor: Retrieving audio segments...")

                        query_clap_emb = generate_clap_text_embedding(
                            text=rubric_question, 
                            model=self.clap_model, 
                            processor=self.clap_processor
                        )

                        query_sentence_emb = generate_sentence_embedding(
                            text_input=rubric_question, 
                            model=self.sentence_transformers_model
                        )

                        retrieved_audio_cache = retrieve_relevant_audio_segments(
                            rubric_question=rubric_question,
                            retriever=self.audio_segment_retriever,
                            minio_client=self.minio_client,
                            search_filter=search_filter,
                            query_clap_emb=query_clap_emb, 
                            query_sentence_emb=query_sentence_emb,
                            score_threshold=self.DEFAULT_AUDIO_SEGMENT_RETRIEVER_SCORE_THRESHOLD
                        )

                        print(f"Executor: Retrieved {len(retrieved_audio_cache)} relevant audio segments.")
                        
                    tool_outputs[tool_name] = tool_instance.run(
                        retrieved_audio_segments_results=retrieved_audio_cache
                    )

                elif tool_category == ToolCategory.VISUAL: 
                    if retrieved_video_keyframes_cache is None: 
                        print(f"Executor: Retrieving video keyframes for '{rubric_question}'...")

                        query_clip_emb = generate_clip_text_embedding( 
                            text=rubric_question, 
                            model=self.clip_model,
                            processor=self.clip_processor
                        )

                        query_sentence_emb = generate_sentence_embedding(
                            text_input=rubric_question, 
                            model=self.sentence_transformers_model
                        )

                        retrieved_video_keyframes_cache = retrieve_relevant_keyframes(
                            rubric_question=rubric_question, 
                            query_clip_emb=query_clip_emb, 
                            query_sentence_emb=query_sentence_emb, 
                            retriever=self.video_keyframe_retriever, 
                            minio_client=self.minio_client, 
                            search_filter=search_filter,
                            score_threshold=self.DEFAULT_VIDEO_KEYFRAME_RETRIEVER_SCORE_THRESHOLD
                        )

                        print(f"Executor: Retrieved {len(retrieved_video_keyframes_cache)} relevant video keyframes.")

                    tool_outputs[tool_name] = tool_instance.run(
                        retrieved_keyframes_result=retrieved_video_keyframes_cache
                    ) 

                elif tool_category == ToolCategory.TEMPORAL:
                    # Use the generic cache for the temporal tool
                    cached_data = self.cache_manager.get_item(
                        category=self.TEMPORAL_CACHE_CATEGORY,
                        key=video_id # Use video_id as the key within this category
                    )
                    if cached_data is not None:
                        print(f"Executor: Using cached output for '{tool_instance.TOOL_NAME}' (video_id: {video_id}).")
                        tool_outputs[tool_instance.TOOL_NAME] = cached_data
                    else:
                        print(f"Executor: Running '{tool_instance.TOOL_NAME}' for video_id: {video_id} (will cache).")
                        if not video_file_path or not os.path.exists(video_file_path):
                            raise FileNotFoundError(f"Video file not found: {video_file_path} for temporal tool.")
                        if not action_vocabulary:
                            raise ValueError("Action vocabulary needed for temporal segmentation.")
                        
                        output = tool_instance.run(video_file_path=video_file_path, action_vocabulary=action_vocabulary)
                        
                        self.cache_manager.set_item(
                            category=self.TEMPORAL_CACHE_CATEGORY,
                            key=video_id,
                            value=output
                        )
                        tool_outputs[tool_instance.TOOL_NAME] = output

            except Exception as e:
                print(f"Error running tool '{tool_name}': {e}")
                tool_outputs[tool_name] = None
                continue

        print("\nExecutor: Completed running all selected tools.")
        return tool_outputs