from pydantic_settings import BaseSettings 

class DatabaseSettings(BaseSettings):
    url: str = "sqlite:///./osce_assessment_app_backend.db"

class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()

settings = Settings()