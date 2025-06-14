import streamlit as st
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

# Configure page
st.set_page_config(
    page_title="OSCE Video Assessment System",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .tool-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
    }
    .evidence-box {
        background-color: #f0f2f6;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .grade-display {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .grade-0 { background-color: #ffebee; color: #c62828; }
    .grade-1 { background-color: #fff3e0; color: #ef6c00; }
    .grade-2 { background-color: #fff8e1; color: #f57f17; }
    .grade-3 { background-color: #f3e5f5; color: #7b1fa2; }
    .grade-4 { background-color: #e8f5e8; color: #2e7d32; }
    .grade-5 { background-color: #e0f2f1; color: #00695c; }
    .workflow-step {
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
    }
    .workflow-step.active {
        border-color: #4CAF50;
        background-color: #f0f8f0;
    }
    .workflow-step.completed {
        border-color: #2196F3;
        background-color: #e3f2fd;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'assessment_results' not in st.session_state:
    st.session_state.assessment_results = None
if 'workflow_status' not in st.session_state:
    st.session_state.workflow_status = {
        'planner': 'pending',
        'executor': 'pending',
        'reflector': 'pending',
        'generator': 'pending',
        'consensus': 'pending'
    }
if 'tool_outputs' not in st.session_state:
    st.session_state.tool_outputs = {}

# Header
st.markdown("""
<div class="main-header">
    <h1>🎥 OSCE Video Assessment System</h1>
    <p>Multi-Agent Planner-Executor-Reflector-Generate-Consensus Framework</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Video upload
    st.subheader("📹 Video Input")
    uploaded_video = st.file_uploader(
        "Upload OSCE Video",
        type=['mp4', 'avi', 'mov', 'mkv'],
        help="Upload the OSCE examination video for assessment"
    )
    
    if uploaded_video:
        st.success(f"✅ Video uploaded: {uploaded_video.name}")
        st.video(uploaded_video)
    
    # Rubric question input
    st.subheader("📝 Rubric Question")
    rubric_question = st.text_area(
        "Enter the rubric question:",
        value="Did the student greet the patient?",
        height=100,
        help="Enter the specific rubric question to assess"
    )
    
    # Model configuration
    st.subheader("🤖 Model Settings")
    clip_model = st.selectbox("CLIP Model", ["ViT-B/32", "ViT-L/14", "RN50x64"])
    clap_model = st.selectbox("CLAP Model", ["CLAP-base", "CLAP-large"])
    llm_model = st.selectbox("LLM Model", ["GPT-4", "Claude-3", "Gemini-Pro"])
    
    # Processing parameters
    st.subheader("⚡ Processing Parameters")
    top_k_keyframes = st.slider("Top-K Keyframes", 1, 20, 5)
    top_k_audio = st.slider("Top-K Audio Segments", 1, 20, 3)
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🔄 Assessment Workflow")
    
    # Workflow status display
    workflow_steps = [
        ("🧠 Planner", "Analyzes rubric question and determines tool strategy"),
        ("⚡ Executor", "Invokes selected tools and gathers evidence"),
        ("🔍 Reflector", "Evaluates evidence quality and sufficiency"),
        ("📝 Generator", "Generates grade and rationale from evidence"),
        ("🤝 Consensus", "Refines answer through majority voting (optional)")
    ]
    
    for i, (step_name, description) in enumerate(workflow_steps):
        step_key = step_name.split()[1].lower()
        status = st.session_state.workflow_status[step_key]
        
        status_class = "workflow-step"
        if status == "active":
            status_class += " active"
        elif status == "completed":
            status_class += " completed"
        
        status_icon = "⏳" if status == "pending" else "🔄" if status == "active" else "✅"
        
        st.markdown(f"""
        <div class="{status_class}">
            <h4>{status_icon} {step_name}</h4>
            <p>{description}</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.header("🎯 Quick Actions")
    
    # Start assessment button
    if st.button("🚀 Start Assessment", type="primary", use_container_width=True):
        if uploaded_video and rubric_question:
            # Simulate assessment process
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate workflow steps
            steps = ['planner', 'executor', 'reflector', 'generator', 'consensus']
            for i, step in enumerate(steps):
                st.session_state.workflow_status[step] = 'active'
                status_text.text(f"Running {step.title()}...")
                time.sleep(1)
                progress_bar.progress((i + 1) / len(steps))
                st.session_state.workflow_status[step] = 'completed'
            
            # Generate mock results
            st.session_state.assessment_results = {
                "grade": 3,
                "rationale": "The student demonstrated partial greeting behavior. They made eye contact and said 'Hello' but did not introduce themselves by name or explain their role, which are important components of a complete patient greeting.",
                "audio_evidence": "Transcript: 'Hello, how are you feeling today?'",
                "video_evidence": "Keyframe analysis shows student making eye contact and verbal interaction at timestamp 00:15",
                "retrieved_audio_segments": ["Segment 1: 00:10-00:20", "Segment 2: 00:45-00:55"],
                "retrieved_video_keyframes": ["Frame 1: 00:15", "Frame 2: 00:18", "Frame 3: 00:22"]
            }
            
            # Mock tool outputs
            st.session_state.tool_outputs = {
                "keyframe_retrieval": {
                    "retrieved_frames": 5,
                    "timestamps": ["00:15", "00:18", "00:22", "00:35", "00:42"],
                    "similarity_scores": [0.89, 0.85, 0.82, 0.78, 0.75]
                },
                "audio_retrieval": {
                    "retrieved_segments": 3,
                    "timestamps": ["00:10-00:20", "00:45-00:55", "01:20-01:30"],
                    "similarity_scores": [0.92, 0.87, 0.81]
                },
                "scene_captioner": {
                    "captions": [
                        "A medical student in white coat standing beside patient bed",
                        "Student making eye contact with elderly patient",
                        "Student gesturing while speaking to patient"
                    ]
                },
                "object_detector": {
                    "detected_objects": ["person", "medical_coat", "stethoscope", "bed", "clipboard"],
                    "confidence_scores": [0.98, 0.95, 0.87, 0.92, 0.89]
                },
                "transcriber": {
                    "transcripts": [
                        "Hello, how are you feeling today?",
                        "I'm going to examine you now",
                        "Please let me know if you feel any discomfort"
                    ]
                },
                "temporal_segmentation": {
                    "action_segments": [
                        {"start": "00:10", "end": "00:25", "action": "greeting_interaction"},
                        {"start": "00:30", "end": "00:50", "action": "examination_preparation"},
                        {"start": "00:55", "end": "01:15", "action": "physical_examination"}
                    ]
                }
            }
            
            status_text.text("Assessment completed!")
            st.success("✅ Assessment completed successfully!")
            st.rerun()
        else:
            st.error("Please upload a video and enter a rubric question first.")
    
    # Reset button
    if st.button("🔄 Reset Assessment", use_container_width=True):
        st.session_state.assessment_results = None
        st.session_state.workflow_status = {key: 'pending' for key in st.session_state.workflow_status}
        st.session_state.tool_outputs = {}
        st.rerun()

# Results section
if st.session_state.assessment_results:
    st.header("📊 Assessment Results")
    
    # Grade display
    grade = st.session_state.assessment_results["grade"]
    st.markdown(f"""
    <div class="grade-display grade-{grade}">
        Grade: {grade}/5
    </div>
    """, unsafe_allow_html=True)
    
    # Rationale
    st.subheader("💭 Rationale")
    st.markdown(f"""
    <div class="evidence-box">
        {st.session_state.assessment_results["rationale"]}
    </div>
    """, unsafe_allow_html=True)
    
    # Evidence tabs
    evidence_tabs = st.tabs(["🎵 Audio Evidence", "🎬 Video Evidence", "📊 Tool Outputs"])
    
    with evidence_tabs[0]:
        st.subheader("Audio Evidence")
        st.write("**Transcribed Audio:**")
        st.code(st.session_state.assessment_results["audio_evidence"])
        
        st.write("**Retrieved Audio Segments:**")
        for segment in st.session_state.assessment_results["retrieved_audio_segments"]:
            st.write(f"• {segment}")
    
    with evidence_tabs[1]:
        st.subheader("Video Evidence")
        st.write("**Visual Analysis:**")
        st.code(st.session_state.assessment_results["video_evidence"])
        
        st.write("**Retrieved Video Keyframes:**")
        for frame in st.session_state.assessment_results["retrieved_video_keyframes"]:
            st.write(f"• {frame}")
    
    with evidence_tabs[2]:
        st.subheader("Detailed Tool Outputs")
        
        # Tool output expandable sections
        tools = [
            ("🔍 Keyframe Retrieval", "keyframe_retrieval"),
            ("🎵 Audio Segment Retrieval", "audio_retrieval"),
            ("📸 Scene Captioner", "scene_captioner"),
            ("🎯 Object Detector", "object_detector"),
            ("📝 Transcriber", "transcriber"),
            ("⏱️ Temporal Segmentation", "temporal_segmentation")
        ]
        
        for tool_name, tool_key in tools:
            with st.expander(tool_name):
                if tool_key in st.session_state.tool_outputs:
                    tool_data = st.session_state.tool_outputs[tool_key]
                    
                    if tool_key == "keyframe_retrieval":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Retrieved Frames", tool_data["retrieved_frames"])
                        with col2:
                            st.metric("Avg Similarity", f"{sum(tool_data['similarity_scores'])/len(tool_data['similarity_scores']):.3f}")
                        
                        df = pd.DataFrame({
                            "Timestamp": tool_data["timestamps"],
                            "Similarity Score": tool_data["similarity_scores"]
                        })
                        st.dataframe(df, use_container_width=True)
                    
                    elif tool_key == "audio_retrieval":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Retrieved Segments", tool_data["retrieved_segments"])
                        with col2:
                            st.metric("Avg Similarity", f"{sum(tool_data['similarity_scores'])/len(tool_data['similarity_scores']):.3f}")
                        
                        df = pd.DataFrame({
                            "Timestamp Range": tool_data["timestamps"],
                            "Similarity Score": tool_data["similarity_scores"]
                        })
                        st.dataframe(df, use_container_width=True)
                    
                    elif tool_key == "scene_captioner":
                        for i, caption in enumerate(tool_data["captions"], 1):
                            st.write(f"**Caption {i}:** {caption}")
                    
                    elif tool_key == "object_detector":
                        df = pd.DataFrame({
                            "Object": tool_data["detected_objects"],
                            "Confidence": tool_data["confidence_scores"]
                        })
                        st.dataframe(df, use_container_width=True)
                    
                    elif tool_key == "transcriber":
                        for i, transcript in enumerate(tool_data["transcripts"], 1):
                            st.write(f"**Segment {i}:** {transcript}")
                    
                    elif tool_key == "temporal_segmentation":
                        df = pd.DataFrame(tool_data["action_segments"])
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("No output available for this tool")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    OSCE Video Assessment System | Multi-Agent Framework for Medical Education
</div>
""", unsafe_allow_html=True)
