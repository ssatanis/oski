import os 
import json 
import time 

from core.vector_store.qdrant_client import QdrantClient
from core.utils.minio_client import MinIOClient  
from core.vector_store.retrievers.video_keyframe_retriever import VideoKeyframeRetriever
from core.vector_store.retrievers.audio_segment_retriever import AudioSegmentRetriever
from core.utils.gemini_utils import load_gemini_client
from core.tools.repository import tool_repository
from core.config.config import settings
from core.utils.embedding_utils import (
    load_sentence_transformer_model,
    load_clip_model_and_processor,
    load_clap_model_and_processor
)
from core.agents.planner_agent import Planner 
from core.agents.executor_agent import Executor 
from core.agents.reflector_agent import Reflector 
from core.agents.scorer_agent import Scorer 
        
if __name__ == "__main__":
    try:
        print("\nInitializing clients, retrievers, and models...")
        qdrant_generic_client = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key,
            use_https=settings.qdrant.use_https
        )

        minio_client = MinIOClient()

        video_keyframe_retriever = VideoKeyframeRetriever(
            client=qdrant_generic_client
        )

        audio_segment_retriever = AudioSegmentRetriever(
            client=qdrant_generic_client
        )

        clip_model, clip_processor = load_clip_model_and_processor()
        sentence_transformers_model = load_sentence_transformer_model()
        clap_model, clap_processor = load_clap_model_and_processor()

        gemini_client = load_gemini_client()

        print("Initialization successful.")

    except Exception as e:
        print(f"Error initializing Qdrant components: {e}")
        raise

    VIDEO_FILE_PATH = os.path.join("./sample_osce_videos", "osce-physical-exam-demo-video-1.mp4")
    VIDEO_ID = "46dc4868-15e9-4f27-b277-726bf9f0023c" # Already indexed
    action_vocabulary = json.load(open("./data/action_vocabulary.json", "r+"))

    start = time.time()

    # Run the end to end pipeline 
    rubric_question = "Did the student use the stethoscope?"

    # Planner
    planner_agent = Planner(
        gemini_client=gemini_client, 
        tool_repository=tool_repository
    )

    # selected_tools = planner_agent.run(rubric_question=rubric_question)
    selected_tools = tool_repository

    print("Planner output: ", selected_tools)

    # Executor 
    executor_agent = Executor(
        gemini_client=gemini_client, 
        minio_client=minio_client, 
        qdrant_client=qdrant_generic_client,
        clap_model=clap_model, 
        clap_processor=clap_processor, 
        clip_model=clip_model, 
        clip_processor=clip_processor, 
        sentence_transformers_model=sentence_transformers_model,
        tool_repository=tool_repository
    )

    executor_output = executor_agent.run(
        rubric_question=rubric_question, 
        selected_tools=selected_tools, 
        video_file_path=VIDEO_FILE_PATH, 
        video_id=VIDEO_ID, 
        action_vocabulary=action_vocabulary
    )

    print("Executor output: ", executor_output)

    # Scorer 
    scorer_agent = Scorer(gemini_client=gemini_client)

    scorer_output = scorer_agent.run(
        rubric_question=rubric_question, 
        evidence_from_executor=executor_output
    )

    print("Scorer output: ", scorer_output)

    # Reflector
    reflector_agent = Reflector(
        gemini_client=gemini_client, 
        scorer_formatter_func=scorer_agent._format_evidence_for_prompt
    )

    reflector_output = reflector_agent.run(
        rubric_question=rubric_question,
        evidence_from_executor=executor_output, 
        scorer_output=scorer_output
    )

    print("Reflector output: ", reflector_output)

    reflector_output = reflector_agent.run(
        rubric_question="Did the student palpate the four quadrants of the abdomen?",
        evidence_from_executor=executor_output, 
        scorer_output=scorer_output
    )

    print("Reflector output (false input): ", reflector_output)

    end = time.time()

    print(f"Time elapsed: {end - start} seconds.")

    




