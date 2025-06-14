import uuid 
from datetime import datetime 
from typing import Optional, List 

from pydantic import BaseModel, ConfigDict

class VideoBase(BaseModel):
    filename: Optional[str] = None 
    duration_seconds: Optional[float] = None 
    fps: Optional[float] = None 
    resolution_width: Optional[int] = None 
    resolution_height: Optional[int] = None 
    size_bytes: Optional[int] = None 

class VideoCreate(VideoBase):
    id: Optional[str] = None 
    filename: str 
    minio_video_path: str 
    minio_audio_path: Optional[str] = None 

class VideoUpdate(VideoBase):
    pass

class VideoInDBBase(VideoBase):
    id: Optional[str] = None 
    filename: str 
    minio_video_path: str 
    minio_audio_path: Optional[str] = None 
    created_at: datetime 
    updated_at: datetime 

    model_config = ConfigDict(from_attributes=True)

class VideoResponse(VideoInDBBase):
    minio_audio_url: Optional[str] 
    minio_video_url: Optional[str]

class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int 
    skip: int 
    limit: int 


