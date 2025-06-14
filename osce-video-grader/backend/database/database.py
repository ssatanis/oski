import uuid
from datetime import datetime  

from sqlalchemy import (
    create_engine, 
    Column, 
    String, 
    Float, 
    Integer, 
    DateTime
)
from sqlalchemy.orm import sessionmaker 
from sqlalchemy.ext.declarative import declarative_base 

from backend.config.config import settings 

SQLALCHEMY_DATABASE_URL = settings.database.url

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database models 
class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, index=True, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    minio_video_path = Column(String, unique=True, nullable=False)
    minio_audio_path = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"Filename: {self.filename}\nID: {self.id}\nDuration: {self.duration_seconds} seconds\nCreated At: {self.created_at}"
    
# Function to create database tables 
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency for the DB session 
def get_db():
    db = SessionLocal()

    try: 
        yield db 
    finally:
        db.close()

    
