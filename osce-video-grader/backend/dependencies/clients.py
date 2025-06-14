from google import genai 
from fastapi import Depends, HTTPException, status, Request 

from core.utils.minio_client import MinIOClient 
from core.vector_store.qdrant_client import QdrantClient 
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever

def get_minio_client_dependency(request: Request) -> MinIOClient:
    """FastAPI dependency to get the initialized MinIO Client instance."""
    minio_client = request.app.state.clients.get("minio")

    if not minio_client:
        print("ERROR: MinIO client not found in application state.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="MinIO service could not be initialized."
        )
    
    return minio_client 

def get_qdrant_client_dependency(request: Request) -> QdrantClient:
    """FastAPI dependency to get the initialized Qdrant Client instance."""
    qdrant_client = request.app.state.clients.get("qdrant")

    if not qdrant_client:
        print("ERROR: Qdrant client not found in application state.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Qdrant service could not be initialized."
        )
    
    return qdrant_client 

def get_gemini_client_dependency(request: Request) -> genai.Client:
    """FastAPI dependency to get the initialized Gemini Client instance."""
    gemini_client = request.app.state.clients.get("gemini")

    if not gemini_client:
        print("ERROR: Gemini client not found in application state.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Gemini client could not be initialized."
        )
    
    return gemini_client

def get_video_keyframe_retriever_dependency(request: Request) -> VideoKeyframeRetriever:
    """FastAPI dependency to get the initialized VideoKeyframeRetriever instance."""
    video_keyframe_retriever = request.app.state.retrievers.get("video_keyframe")
    
    if not video_keyframe_retriever:
        print("ERROR: VideoKeyframeRetriever not found in the application state.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="VideoKeyframeRetriever service could not be initialized."
        )
    
    return video_keyframe_retriever

def get_audio_segment_retriever_dependency(request: Request) -> AudioSegmentRetriever:
    """FastAPI dependency to get the initialized AudioSegmentRetriever instance."""
    audio_segment_retriever = request.app.state.retrievers.get("audio_segment")
    
    if not audio_segment_retriever:
        print("ERROR: AudioSegmentRetriever not found in the application state.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="AudioSegmentRetriever service could not be initialized."
        )
    
    return audio_segment_retriever