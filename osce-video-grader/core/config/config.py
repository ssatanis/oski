from pydantic import Field 
from pydantic_settings import BaseSettings, SettingsConfigDict 
from dotenv import load_dotenv, find_dotenv 

_ = load_dotenv(find_dotenv())

class GeminiConfig(BaseSettings):
    """Configuration for the Gemini API."""
    api_key: str = Field(..., validation_alias="GEMINI_API_KEY")

class QDrantConfig(BaseSettings):
    """Configuration for the Qdrant Vector Store."""
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333 
    api_key: str = Field("", validation_alias="QDRANT_API_KEY")
    use_https: bool = False 

    audio_segments_collection_name: str = "osce-grader-audio-segments-v1"
    video_keyframes_collection_name: str = "osce-grader-video-keyframes-v1"

class MinIOConfig(BaseSettings):
    """Configuration for the MinIO Object Store."""
    model_config = SettingsConfigDict(env_prefix="MINIO_")

    endpoint: str = "localhost:9000"
    access_key: str = Field("minioadmin", validation_alias="MINIO_ACCESS_KEY")
    secret_key: str = Field("minioadmin", validation_alias="MINIO_SECRET_KEY")

    audio_segments_bucket_name: str = "osce-grader-audio-bucket-v1"
    video_keyframes_bucket_name: str = "osce-grader-keyframes-bucket-v1"
    original_videos_bucket_name: str = "osce-grader-original-videos-bucket-v1"
    extracted_audios_bucket_name: str = "osce-grader-extracted-audios-bucket-v1"
    metadata_bucket_name: str = "osce-grader-metadata-bucket-v1"

class HuggingFaceConfig(BaseSettings):
    """Configuration for hugging face."""
    access_token: str = Field(..., validation_alias="HF_ACCESS_TOKEN")

class Settings(BaseSettings):
    """Main settings class to hold all service configurations."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    qdrant: QDrantConfig = QDrantConfig()
    minio: MinIOConfig = MinIOConfig()
    gemini: GeminiConfig = GeminiConfig()
    hf: HuggingFaceConfig = HuggingFaceConfig()

settings = Settings()