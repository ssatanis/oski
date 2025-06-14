import io 
import traceback 
from pathlib import Path
from typing import Optional 

from sqlalchemy.orm import Session 
from fastapi import HTTPException 

from core.utils.minio_client import MinIOClient
from core.utils.video_processor import VideoMetadata
from backend.schemas.video import VideoCreate
from backend.database.database import VideoModel

def save_video_to_minio(
    video_file_path: str, 
    video_filename: str, 
    minio_client: MinIOClient 
):
    try:
        with open(video_file_path, "rb") as f_vid_stream_handle: 
            video_content_bytes = f_vid_stream_handle.read()
            video_stream_for_minio = io.BytesIO(video_content_bytes)
            video_data_length = len(video_content_bytes)

            minio_original_video_path = minio_client.store_original_video(
                video_data_stream=video_stream_for_minio, 
                video_data_length=video_data_length, 
                original_filename=video_filename
            )

            if not minio_original_video_path:
                raise Exception("Failed to store video file in MinIO.")
            
            return minio_original_video_path
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None 
    
def save_audio_to_minio(
    audio_file_path: str, 
    video_filename: str, 
    video_id: str, 
    minio_client: MinIOClient 
): 
    try: 
        with open(audio_file_path, "rb") as f_audio_stream_handle: 
            audio_content_bytes = f_audio_stream_handle.read()
            audio_stream_for_minio = io.BytesIO(audio_content_bytes)
            audio_data_length = len(audio_content_bytes)

        extracted_audio_format = Path(audio_file_path).suffix.lstrip(".").lower()
        
        if not extracted_audio_format:
            extracted_audio_format = "wav"

        minio_extracted_audio_path = minio_client.store_extracted_audio(
            audio_data_stream=audio_stream_for_minio, 
            audio_data_length=audio_data_length, 
            video_id=video_id, 
            original_video_filename=video_filename, 
            audio_format=extracted_audio_format
        )

        if not minio_extracted_audio_path:
            raise Exception("Failed to store audio file in MinIO.")
        
        return minio_extracted_audio_path
        
    except Exception as e:
        print(f"An error occurred: {str(e)}") 
        return None 
    
def save_video_in_db(
    db: Session, 
    video_id: str, 
    video_metadata: VideoMetadata, 
    video_filename: str, 
    minio_video_path: str, 
    minio_audio_path: Optional[str]
):
    db_video_data = VideoCreate(
        id=video_id, 
        filename=video_filename, 
        duration_seconds=video_metadata["duration_seconds"], 
        fps=video_metadata["fps"], 
        resolution_height=video_metadata["resolution_height"],
        resolution_width=video_metadata["resolution_width"], 
        size_bytes=video_metadata["size_bytes"], 
        minio_video_path=minio_video_path, 
        minio_audio_path=minio_audio_path
    )
    db_video_data_dict = db_video_data.model_dump(exclude_none=True)

    db_video = VideoModel(
        **db_video_data_dict
    )

    try: 
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        print(f"Video metadata saved to DB for ID: {db_video.id}")

        return db_video_data_dict 

    except Exception as e:
        db.rollback()

        if "UNIQUE constraint failed: videos.id" in str(e) or \
               ("violates unique constraint" in str(e) and "videos_pkey" in str(e)):
            raise HTTPException(status_code=409, detail=f"Video with ID '{video_id}' already exists.")
            
        print(f"Database error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save video metadata to database: {str(e)}")
    