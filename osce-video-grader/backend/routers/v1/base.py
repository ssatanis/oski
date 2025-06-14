import os
import io 
import uuid
import time
import traceback
import json
import shutil
from pathlib import Path 
from tempfile import mkdtemp
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
from PIL import Image
from google import genai
from fastapi import (
    File, 
    UploadFile, 
    HTTPException, 
    Depends, 
    Form, 
    Query,
    APIRouter,
    Request, 
    status 
)
import uvicorn
from google import genai 
from pydantic import BaseModel, Field, conint 
from sqlalchemy.orm import Session 

from core.config.config import settings
from core.utils.minio_client import MinIOClient
from core.vector_store.qdrant_client import QdrantClient
from core.utils.gemini_utils import load_gemini_client

from core.utils.video_processor import extract_keyframes_by_clustering, get_resnet_feature_extractor

from core.tools.grounding.keyframe_captioner import KeyframeDescriptionOutput
from core.utils.gemini_utils import GeminiImageBatchProcessor
from core.utils.embedding_utils import (
    generate_clip_image_embeddings_batch,
    generate_sentence_embeddings_batch
)
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever
from core.utils.audio_processor import extract_audio, process_audio_segments
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever
from core.utils.audio_processor import (
    extract_audio, 
    process_audio_segments,
    DEFAULT_SAMPLING_RATE
)
from core.utils.embedding_utils import (
    generate_clip_image_embeddings_batch,
    generate_sentence_embeddings_batch,
    generate_clap_audio_embeddings_batch
)
from core.vector_store.utils import (
    index_keyframes, 
    index_audio_segments
)
from core.prompts.gemini import OSCE_KEYFRAME_CAPTIONER_PROMPT
from core.tools.base import Tool 
from core.tools.repository import tool_repository
from core.agents.base_agent import (
    Planner, 
    Scorer, 
    Executor, 
    Reflector
)
from core.agents.reflector_agent import ReflectorOutput 
from core.agents.scorer_agent import ScorerOutput
from core.utils.video_processor import get_video_metadata

from backend.constants import DEFAULT_NUM_KEYFRAMES_TO_EXTRACT
from backend.database.database import get_db, VideoModel
from backend.helpers import (
    save_audio_to_minio,
    save_video_to_minio,
    save_video_in_db
)
from backend.schemas.video import (
    VideoListResponse,
    VideoResponse,
    VideoInDBBase
)
from backend.dependencies.clients import (
    get_minio_client_dependency, 
    get_qdrant_client_dependency, 
    get_gemini_client_dependency,
    get_audio_segment_retriever_dependency, 
    get_video_keyframe_retriever_dependency
)

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

router = APIRouter(
    tags=["V1"]
)

@router.get("/healthcheck")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}

@router.post("/index_video", status_code=201)
async def index_video_endpoint(
    request: Request, # Inject the current Request object to access the app.state object 
    video_file: UploadFile = File(..., description="The video file to be processed and indexed."),
    video_id: Optional[str] = Form(None, description="Optional custom video ID. Auto-generated if not provided."),
    num_keyframes_to_extract: int = Form(DEFAULT_NUM_KEYFRAMES_TO_EXTRACT, description="Number of keyframes to extract.", ge=1, le=100), # Added ge and le for validation
    db: Session = Depends(get_db), 
    minio_client: MinIOClient = Depends(get_minio_client_dependency), 
    gemini_client: genai.Client = Depends(get_gemini_client_dependency),
    audio_segment_retriever: AudioSegmentRetriever = Depends(get_audio_segment_retriever_dependency), 
    video_keyframe_retriever: VideoKeyframeRetriever = Depends(get_video_keyframe_retriever_dependency)
):
    """
    Processes a video file to extract, describe, embed, and index keyframes and audio segments.
    A unique `video_id` will be generated if not provided.
    `num_keyframes_to_extract` can be specified in the form data.
    """
    start_time_total = time.time()
    processing_video_id = video_id if video_id else str(uuid.uuid4())
    print(f"\n--- Starting Video Indexing for video_id: {processing_video_id} ---")
    print(f"Number of keyframes to extract: {num_keyframes_to_extract}")


    temp_dir = mkdtemp()
    # Ensure filename from UploadFile is sanitized or use a fixed name for robustness
    original_filename = video_file.filename if video_file.filename else "uploaded_video"
    base, ext = os.path.splitext(original_filename)
    safe_filename = "".join(c if c.isalnum() or c in ['.', '_'] else '_' for c in base) + (ext if ext else ".mp4")
    video_file_path = os.path.join(temp_dir, safe_filename)

    extracted_audio_file_path = None

    try:
        print(f"Saving uploaded video to: {video_file_path}")
        with open(video_file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        print(f"Video saved successfully.")

        # Extract the video metadata 
        video_metadata = get_video_metadata(video_file_path)
                
        # --- Retrieve necessary models and clients from app.state ---
        resnet_model = request.app.state.models["resnet_model"]
        resnet_transform = request.app.state.models["resnet_transform"]
        clip_model = request.app.state.models["clip_model"]
        clip_processor = request.app.state.models["clip_processor"]
        sentence_transformers_model = request.app.state.models["sentence_transformer"]

        whisper_model = request.app.state.models["whisper_model"]
        diarization_model = request.app.state.models["diarization_model"]
        audio_emotion_classification_model = request.app.state.models["audio_emotion_classification_model"]
        clap_model = request.app.state.models["clap_model"]
        clap_processor = request.app.state.models["clap_processor"]

        # Keyframe extraction and indexing
        print(f"\n--- Extracting Keyframes from '{video_file_path}' ---")
        kf_start_time = time.time()
        extracted_keyframes_data: List[Tuple[Image.Image, float]] = extract_keyframes_by_clustering(
            video_path=video_file_path,
            num_keyframes=num_keyframes_to_extract,
            resnet_model=resnet_model,
            resnet_transform=resnet_transform,
            frame_sample_rate=1,
            batch_size=64,
            embedding_method="resnet"
        )
        print(f"Keyframe extraction completed in {time.time() - kf_start_time:.2f} seconds.")

        if not extracted_keyframes_data:
            print("No keyframes extracted. Skipping keyframe indexing.")
        else:
            print(f"Successfully extracted {len(extracted_keyframes_data)} keyframes.")
            keyframe_pil_images = [pil_image for (pil_image, _) in extracted_keyframes_data]

            print("Generating keyframe descriptions with Gemini...")
            desc_start_time = time.time()
            gemini_image_processor = GeminiImageBatchProcessor(
                client=gemini_client,
                prompt_template=OSCE_KEYFRAME_CAPTIONER_PROMPT,
                output_schema=KeyframeDescriptionOutput,
                rate_limit_calls=10,
                rate_limit_period=60,
                max_retries=5,
                max_backoff=120,
                max_workers=4,
            )
            keyframe_descriptions_raw = gemini_image_processor.process_batch(keyframe_pil_images)
            keyframe_descriptions = []
            for desc_data in keyframe_descriptions_raw:
                if isinstance(desc_data, dict): keyframe_descriptions.append(desc_data)
                elif hasattr(desc_data, 'model_dump'): keyframe_descriptions.append(desc_data.model_dump())
                else: keyframe_descriptions.append({"description": str(desc_data)})
            print(f"Keyframe description generation took {time.time() - desc_start_time:.2f} seconds.")

            print("Generating CLIP embeddings for keyframes...")
            clip_emb_start_time = time.time()
            keyframe_images_clip_embeddings = generate_clip_image_embeddings_batch(
                pil_images=keyframe_pil_images, model=clip_model, processor=clip_processor,
            )
            print(f"CLIP embedding generation took {time.time() - clip_emb_start_time:.2f} seconds.")

            print("Generating Sentence embeddings for keyframe descriptions...")
            sent_emb_start_time = time.time()
            keyframe_descriptions_sent_embeddings = generate_sentence_embeddings_batch(
                texts=[d.get("description", "") for d in keyframe_descriptions], model=sentence_transformers_model
            )
            print(f"Sentence embedding generation took {time.time() - sent_emb_start_time:.2f} seconds.")

            print("Indexing keyframes...")
            index_kf_start_time = time.time()
            index_keyframes(
                video_id=processing_video_id,
                extracted_keyframes_data=extracted_keyframes_data,
                keyframe_images_clip_embeddings=keyframe_images_clip_embeddings,
                keyframe_descriptions_sent_embeddings=keyframe_descriptions_sent_embeddings,
                keyframe_descriptions=keyframe_descriptions,
                minio_client=minio_client,
                video_keyframe_retriever=video_keyframe_retriever
            )
            print(f"Keyframe indexing took {time.time() - index_kf_start_time:.2f} seconds.")

        # Audio extraction and indexing 
        print(f"\n--- Extracting and Processing Audio from '{video_file_path}' ---")
        audio_start_time = time.time()

        print("Extracting audio track...")
        extracted_audio_file_path = extract_audio(
            video_path=video_file_path
        )

        if not extracted_audio_file_path or not os.path.exists(extracted_audio_file_path):
            print("Audio extraction failed. Skipping audio indexing.")
        else:
            print(f"Audio extracted to: {extracted_audio_file_path}")

            print("Processing audio segments (transcription, diarization, emotion)...")
            extracted_audio_segments = process_audio_segments(
                audio_path=extracted_audio_file_path,
                whisper_model=whisper_model,
                diarization_model=diarization_model,
                audio_emotion_classification_model=audio_emotion_classification_model,
                sampling_rate=DEFAULT_SAMPLING_RATE
            )
            audio_proc_time = time.time()
            print(f"Audio segment processing took {audio_proc_time - audio_start_time:.2f} seconds (excluding embeddings).")


            if not extracted_audio_segments:
                print("No audio segments processed. Skipping audio indexing.")
            else:
                print(f"Successfully processed {len(extracted_audio_segments)} audio segments.")
                print("Generating CLAP embeddings for audio segments...")
                clap_emb_start_time = time.time()

                clap_audio_data_list = []

                for segment in extracted_audio_segments:
                    if "audio" in segment and isinstance(segment["audio"], np.ndarray):
                         clap_audio_data_list.append(segment["audio"])
                    else:
                        print(f"Warning: Missing or invalid audio data for CLAP for a segment. Skipping.")

                print("CLAP audio data list: ", clap_audio_data_list)

                audio_segments_clap_embeddings = [] # Initialize
                if clap_audio_data_list:
                    audio_segments_clap_embeddings = generate_clap_audio_embeddings_batch(
                        audio_data_list=clap_audio_data_list, 
                        model=clap_model, 
                        processor=clap_processor,
                    )
                    print(f"CLAP audio embedding generation took {time.time() - clap_emb_start_time:.2f} seconds.")
                else:
                    print("No valid audio data found for CLAP embedding generation.")


                print("Generating Sentence embeddings for audio transcripts...")
                audio_sent_emb_start_time = time.time()
                audio_segments_transcript_sentence_embeddings = generate_sentence_embeddings_batch(
                    texts=[segment.get("transcript", "") for segment in extracted_audio_segments], model=sentence_transformers_model,
                )
                print(f"Sentence transcript embedding generation took {time.time() - audio_sent_emb_start_time:.2f} seconds.")

                print(audio_segments_clap_embeddings, audio_segments_transcript_sentence_embeddings)

                clap_embeddings_exist = audio_segments_clap_embeddings is not None and len(audio_segments_clap_embeddings) > 0
                transcript_embeddings_exist = audio_segments_transcript_sentence_embeddings is not None and len(audio_segments_transcript_sentence_embeddings) > 0

                if clap_embeddings_exist or transcript_embeddings_exist:
                    print("Indexing audio segments...")
                    index_audio_start_time = time.time()
                    index_audio_segments(
                        video_id=processing_video_id,
                        processed_audio_segments=extracted_audio_segments,
                        audio_segments_clap_embeddings=audio_segments_clap_embeddings if clap_embeddings_exist else [],
                        audio_segments_transcript_sentence_embeddings=audio_segments_transcript_sentence_embeddings if transcript_embeddings_exist else [],
                        minio_client=minio_client,
                        audio_segment_retriever=audio_segment_retriever
                    )
                    print(f"Audio segment indexing took {time.time() - index_audio_start_time:.2f} seconds.")
                else:
                    print("Skipping audio segment indexing as no embeddings were generated.")
                    if not clap_embeddings_exist:
                        print("Reason: CLAP embeddings are missing or empty.")
                    if not transcript_embeddings_exist:
                        print("Reason: Transcript sentence embeddings are missing or empty.")


        total_processing_time = time.time() - start_time_total
        print(f"--- Video Indexing for '{processing_video_id}' completed in {total_processing_time:.2f} seconds ---")

        # Save the video data in the database 
        minio_video_path = save_video_to_minio(
            video_file_path=video_file_path, 
            video_filename=original_filename, 
            minio_client=minio_client 
        )

        minio_audio_path = save_audio_to_minio(
            audio_file_path=extracted_audio_file_path, 
            video_filename=original_filename, 
            video_id=processing_video_id, 
            minio_client=minio_client 
        )

        saved_video = save_video_in_db(
            db=db, 
            video_id=processing_video_id, 
            video_metadata=video_metadata, 
            video_filename=original_filename, 
            minio_video_path=minio_video_path, 
            minio_audio_path=minio_audio_path
        )        

        return {
            "video_id": processing_video_id,
            "message": "Video processed and indexed successfully.",
            "video": saved_video,
            "num_keyframes_extracted_actual": len(extracted_keyframes_data) if extracted_keyframes_data else 0,
            "num_keyframes_requested": num_keyframes_to_extract,
            "processing_time_seconds": round(total_processing_time, 2)
        }

    except ValueError as ve: # Catch Pydantic validation errors for Form data
        print(f"Validation error for form data: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    
    except Exception as e:
        print(f"Error during video indexing for video_id '{processing_video_id}': {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during video processing: {str(e)}")

    finally:
        if os.path.exists(temp_dir):
            print(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
        if video_file and hasattr(video_file, 'file') and not video_file.file.closed:
            video_file.file.close()

@router.post(
    "/assess_video",
    response_model=PipelineAssessmentResult
)
async def assess_video_pipeline(
    request: Request, # Inject the current Request object to access the app.state object 
    payload: PipelineInput,
    use_all_tools: bool = Query(False, description="If true, bypass Planner and run Executor with all available tools."),
    minio_client: MinIOClient = Depends(get_minio_client_dependency), 
    qdrant_client: QdrantClient = Depends(get_qdrant_client_dependency), 
    gemini_client: genai.Client = Depends(get_gemini_client_dependency)
):
    """
    Runs the full multi-agent assessment pipeline for a given rubric question and video ID.
    """
    start_pipeline_time = time.time()
    print(f"\n--- Starting Assessment Pipeline for video_id: {payload.video_id} ---")
    print(f"Rubric Question: {payload.rubric_question}")

    # --- Retrieve necessary clients and models from app.state ---
    clap_model = request.app.state.models["clap_model"]
    clap_processor = request.app.state.models["clap_processor"]
    clip_model = request.app.state.models["clip_model"]
    clip_processor = request.app.state.models["clip_processor"]
    sentence_transformers_model = request.app.state.models["sentence_transformer"]

    # Initialize the agents 
    planner_agent = Planner(
        gemini_client=gemini_client,
        tool_repository=tool_repository # Global tool_repository
    )

    # Executor needs more models
    executor_agent = Executor(
        gemini_client=gemini_client,
        minio_client=minio_client,
        qdrant_client=qdrant_client,
        clap_model=clap_model,
        clap_processor=clap_processor,
        clip_model=clip_model,
        clip_processor=clip_processor,
        sentence_transformers_model=sentence_transformers_model,
        tool_repository=tool_repository,
        # cache_manager=JsonCache() # Initialize or get from app.state if shared
    )

    scorer_agent = Scorer(gemini_client=gemini_client)

    reflector_agent = Reflector(
        gemini_client=gemini_client,
        scorer_formatter_func=scorer_agent._format_evidence_for_prompt # Pass the method directly
    )

    # Run the Planner
    print("\n1. Running Planner...")
    selected_tools: Optional[List[Tool]] = None
    planner_selected_tool_names: List[str] = []
    try:
        selected_tools = planner_agent.run(rubric_question=payload.rubric_question)
        if selected_tools:
            planner_selected_tool_names = [tool.TOOL_NAME for tool in selected_tools]
            print(f"Planner selected tools: {planner_selected_tool_names}")
        else:
            print("Planner did not select any tools or encountered an error.")

    except Exception as e:
        print(f"Error during Planner execution: {e}")
        traceback.print_exc()
        # TODO: Decide how to handle Planner failure 
        selected_tools = []

    if not selected_tools: # Check again in case planner_agent.run returned None then error was caught
        print("Warning: No tools selected by Planner. Executor will likely produce no evidence.")
        selected_tools = []


    # Run the Executor 
    print("\n2. Running Executor...")
    executor_output: Dict[str, Any] = {}

    action_vocab_for_executor: Optional[Dict[str, str]] = request.app.state.action_vocabulary 

    try:
        if use_all_tools:
            # Using the whole tool repository
            executor_output = executor_agent.run(
                rubric_question=payload.rubric_question,
                selected_tools=tool_repository, # selected_tools from Planner
                video_id=payload.video_id,
                action_vocabulary=action_vocab_for_executor, # Pass the loaded vocab
                video_file_path="./sample_osce_videos/testvideo.mp4"
            )
        else:
            executor_output = executor_agent.run(
                rubric_question=payload.rubric_question,
                selected_tools=selected_tools, # selected_tools from Planner
                video_id=payload.video_id,
                action_vocabulary=action_vocab_for_executor, # Pass the loaded vocab
                video_file_path="./sample_osce_videos/testvideo.mp4"
            )

        print(f"Executor output: {json.dumps(executor_output, indent=2, default=str)}")
    except Exception as e:
        print(f"Error during Executor execution: {e}")
        traceback.print_exc()

    # Run the Scorer
    print("\n3. Running Scorer...")
    scorer_result_dict: Optional[Dict] = None # Store as dict for Pydantic model
    try:
        if executor_output: # Only run scorer if there's some evidence
            scorer_result_dict = scorer_agent.run(
                rubric_question=payload.rubric_question,
                evidence_from_executor=executor_output
            )
            if scorer_result_dict:
                print(f"Scorer output: {scorer_result_dict}")
            else:
                print("Scorer did not produce an output (e.g. LLM error, validation error).")
        else:
            print("Skipping Scorer as Executor produced no output.")
            # Create a default "no evidence" score
            scorer_result_dict = ScorerOutput(
                grade=0,
                rationale="No evidence was generated by the executor for this rubric question."
            ).model_dump()

    except Exception as e:
        print(f"Error during Scorer execution: {e}")
        traceback.print_exc()
        # scorer_result_dict will remain None or its last state

    # --- Run Reflector ---
    print("\n4. Running Reflector...")
    reflector_result_dict: Optional[Dict] = None
    try:
        if scorer_result_dict: 
            reflector_result_dict = reflector_agent.run(
                rubric_question=payload.rubric_question,
                evidence_from_executor=executor_output,
                scorer_output=scorer_result_dict # Pass the dict from scorer_agent.run
            )
            if reflector_result_dict:
                print(f"Reflector output: {reflector_result_dict}")
            else:
                print("Reflector did not produce an output.")
        else:
            print("Skipping Reflector as Scorer produced no output.")
    except Exception as e:
        print(f"Error during Reflector execution: {e}")
        traceback.print_exc()
        # reflector_result_dict will remain None or its last state

    end_pipeline_time = time.time()
    total_pipeline_time = end_pipeline_time - start_pipeline_time
    print(f"Assessment Pipeline Completed in {total_pipeline_time:.2f} seconds")

    # Prepare the final response using Pydantic models for validation and structure
    final_response = PipelineAssessmentResult(
        rubric_question=payload.rubric_question,
        video_id=payload.video_id,
        tools_used=[tool.TOOL_NAME for tool in tool_repository] if use_all_tools else planner_selected_tool_names,
        planner_output=planner_selected_tool_names,
        executor_output=executor_output if executor_output else {},
        scorer_output=ScorerOutput(**scorer_result_dict) if scorer_result_dict else None,
        reflector_output=ReflectorOutput(**reflector_result_dict) if reflector_result_dict else None
    )

    return final_response


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"), 
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"), 
    db: Session = Depends(get_db),
    minio_client: MinIOClient = Depends(get_minio_client_dependency)
):
    """Retrieves a list of all videos with their metadata."""
    try:
        videos_query = db.query(VideoModel).order_by(VideoModel.created_at.desc())

        total_videos = videos_query.count()

        db_videos = videos_query.offset(skip).limit(limit).all()

        response_videos = []
        if not db_videos:
            return VideoListResponse(
                videos=[], 
                total=0, 
                skip=skip, 
                limit=limit 
            ) 
        
        for db_video in db_videos:
            video_data_pydantic = VideoInDBBase.from_orm(db_video)
            
            video_url_presigned = None 
            if video_data_pydantic.minio_video_path:
                video_url_presigned = minio_client.get_presigned_url(db_video.minio_video_path)
                if not video_url_presigned:
                    print(f"Warning: Could not generate presigned URL for video: {db_video.minio_video_path}")

            audio_url_presigned = None 
            if video_data_pydantic.minio_audio_path:
                audio_url_presigned = minio_client.get_presigned_url(db_video.minio_audio_path)
                if not audio_url_presigned:
                    print(f"Warning: Could not generate presigned URL for audio: {db_video.minio_audio_path}")

            response_videos.append(
                VideoResponse(
                    **video_data_pydantic.model_dump(),
                    minio_video_url=video_url_presigned, 
                    minio_audio_url=audio_url_presigned
                )
            )

        return VideoListResponse(
            videos=response_videos, 
            total=total_videos, 
            skip=skip, 
            limit=limit
        )

    except Exception as e:
        print(f"Error fetching list of videos: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail="An error occurred while fetching videos."
        )

@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video_details_by_id(
    video_id: str, 
    db: Session = Depends(get_db), 
    minio_client: MinIOClient = Depends(get_minio_client_dependency)
):
    """Retrieves details for a specific video by its ID."""
    try:
        # Validate if the video_id is a valid UUID string 
        _ = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid video ID format."
        )
    
    db_video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if db_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Video with ID '{video_id}' not found."
        )
    
    video_data_pydantic = VideoInDBBase.from_orm(db_video)
    
    video_url_presigned = None 
    if video_data_pydantic.minio_video_path:
        video_url_presigned = minio_client.get_presigned_url(db_video.minio_video_path)
        if not video_url_presigned:
            print(f"Warning: Could not generate presigned URL for video: {db_video.minio_video_path}")

    audio_url_presigned = None 
    if video_data_pydantic.minio_audio_path:
        audio_url_presigned = minio_client.get_presigned_url(db_video.minio_audio_path)
        if not audio_url_presigned:
            print(f"Warning: Could not generate presigned URL for audio: {db_video.minio_audio_path}")

    return VideoResponse(
        **video_data_pydantic.model_dump(),
        minio_video_url=video_url_presigned, 
        minio_audio_url=audio_url_presigned
    )

@router.delete("/videos/{video_id}", status_code=status.HTTP_200_OK)
async def delete_video_details_by_id(
    video_id: str, 
    db: Session = Depends(get_db), 
    minio_client: MinIOClient = Depends(get_minio_client_dependency)
):
    """Deletes a video by its ID."""
    try:
        # Validate if the video_id is a valid UUID string 
        _ = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid video ID format."
        )
    
    db_video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if db_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Video with ID '{video_id}' not found."
        )
    
    if db_video.minio_audio_path:
        if minio_client.delete_object(db_video.minio_audio_path):
            print(f"Deleted extracted audio from MinIO: {db_video.minio_audio_path}")
        else:
            print(f"Warning: Failed to delete extracted audio {db_video.minio_audio_path} from MinIO.")

    if db_video.minio_video_path:
        if minio_client.delete_object(db_video.minio_video_path):
            print(f"Deleted video from MinIO: {db_video.minio_video_path}")
        else:
            print(f"Warning: Failed to delete video {db_video.minio_video_path} from MinIO.")

    # TODO: Maybe delete the Qdrant vectors for the video (from the video keyframes collection and audio segments collection)

    try: 
        db.delete(db_video)
        db.commit()
        print(f"Deleted video from database for ID: {video_id}")
    except Exception as e:
        db.rollback()
        print(f"Error deleting video from database for {video_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to delete video from database."
        )    
    
    return {
        "status": True, 
        "message": f"Successfully deleted video: {video_id}"
    }

    