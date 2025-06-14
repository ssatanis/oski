import os
import traceback
import json
from typing import List, Optional, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from google import genai 
from pydantic import BaseModel, Field

from core.config.config import settings
from core.utils.minio_client import MinIOClient
from core.vector_store.qdrant_client import QdrantClient
from core.utils.gemini_utils import load_gemini_client

from core.utils.video_processor import get_resnet_feature_extractor

from core.utils.embedding_utils import (
    load_clip_model_and_processor,
    load_sentence_transformer_model
)
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever
from core.utils.audio_processor import (
    load_whisper_model,
    load_diarization_model,
    load_audio_emotion_classification_model
)
from core.utils.embedding_utils import ( 
    load_sentence_transformer_model,
    load_clip_model_and_processor,
    load_clap_model_and_processor
)
from core.agents.reflector_agent import ReflectorOutput 
from core.agents.scorer_agent import ScorerOutput

from backend.routers.v1.base import router as api_v1_router 
from backend.database.database import create_db_and_tables

# Global constants 
ACTION_VOCABULARY_FILE_PATH = "./data/action_vocabulary.json"
global_action_vocabulary: Optional[Dict[str, str]] = None

app = FastAPI(
    title="Multi-Agent OSCE Video Assessment API",
    description="API for the Planner-Executor-Scorer-Reflector pipeline for OSCE video assessment.",
    version="0.1.0"
)

# CORS
origins = ["*"] # Allows all origins. TODO: list specific origins.

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]
)


# Application state for models and clients
app.state.models = {}
app.state.clients = {}
app.state.retrievers = {}

class PipelineInput(BaseModel):
    rubric_question: str = Field(..., min_length=5, description="The rubric question to assess.")
    video_id: str = Field(..., description="The unique ID of the pre-indexed video.")

class ToolOutputSchema(BaseModel):
    tool_name: str
    output: Any 

class PipelineAssessmentResult(BaseModel):
    rubric_question: str
    video_id: str
    planner_output: List[str] # List of selected tool names
    tools_used: List[str]
    executor_output: Dict[str, Any] # Tool name to its output
    scorer_output: Optional[ScorerOutput]
    reflector_output: Optional[ReflectorOutput]

@app.on_event("startup")
async def startup_event():
    """
    Load all necessary models and initialize clients when the application starts.
    """
    print("--- Application Startup: Initializing Models and Clients ---")
    
    create_db_and_tables()

    try:
        # General Clients
        app.state.clients["minio"] = MinIOClient()
        app.state.clients["qdrant"] = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key,
            use_https=settings.qdrant.use_https
        )
        app.state.clients["gemini"] = load_gemini_client() # Your existing function

        # Models for Keyframe Processing
        app.state.models["resnet_model"], app.state.models["resnet_transform"] = get_resnet_feature_extractor()
        app.state.models["clip_model"], app.state.models["clip_processor"] = load_clip_model_and_processor()
        app.state.models["clap_model"], app.state.models["clap_processor"] = load_clap_model_and_processor()
        app.state.models["whisper_model"] = load_whisper_model()
        app.state.models["diarization_model"] = load_diarization_model()
        app.state.models["audio_emotion_classification_model"] = load_audio_emotion_classification_model()
        app.state.models["sentence_transformer"] = load_sentence_transformer_model()

        # Retrievers (depend on Qdrant client)
        app.state.retrievers["video_keyframe"] = VideoKeyframeRetriever(
            client=app.state.clients["qdrant"]
        )
        app.state.retrievers["audio_segment"] = AudioSegmentRetriever(
            client=app.state.clients["qdrant"]
        )

        global global_action_vocabulary
        try:
            if os.path.exists(ACTION_VOCABULARY_FILE_PATH):
                with open(ACTION_VOCABULARY_FILE_PATH, "r") as f:
                    global_action_vocabulary = json.load(f)

                app.state.action_vocabulary = global_action_vocabulary
                print(f"Successfully loaded action vocabulary from {ACTION_VOCABULARY_FILE_PATH}")
            else:
                print(f"Warning: Action vocabulary file not found at {ACTION_VOCABULARY_FILE_PATH}. TemporalActionSegmentationTool might not work as expected if it relies on this global.")
                app.state.action_vocabulary = None 
        except Exception as e:
            print(f"Error loading action vocabulary: {e}")
            # Decide if this is a fatal error for your app
        print("--- Models, Clients, and Global Data Initialized Successfully ---")

    except Exception as e:
        print(f"FATAL: Error during application startup: {e}")
        app.state.action_vocabulary = None 
        traceback.print_exc()

app.include_router(api_v1_router, prefix="/api/v1", tags=["V1"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
