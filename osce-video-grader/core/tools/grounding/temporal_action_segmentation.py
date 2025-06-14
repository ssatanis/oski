import os 
import time 
from typing import List, Dict, Any, Tuple 

import numpy as np 
from google import genai 
from moviepy.video.io.VideoFileClip import VideoFileClip 

from core.utils.gemini_utils import (
    load_gemini_client,
    generate_image_content_gemini_with_retry 
)

from core.utils.temporal_utils import (
    generate_overlapping_clip_time_segments, 
    sample_frames_from_clip, 
    create_image_grid, 
    process_video_to_grids, 
    plot_video_clip_grids, 
    generate_action_labelling_prompt,
    load_action_vocabulary, 
    get_action_labels_list, 
    get_action_label_mappings, 
    get_action_labels_successors_map
)
from core.utils.viterbi_decoding_utils import (
    build_transition_matrix, 
    build_soft_emission_matrix, 
    viterbi_decode, 
    plot_viterbi_results,
    reconstruct_temporal_action_sequence
)
from core.tools.base import Tool, ToolCategory

def generate_temporal_action_segments_grid_wise(
    video_file_path: str,
    action_vocabulary: Dict[str, str], 
    gemini_client: genai.Client, 
    num_segments: int = 25, 
    clip_stride: float = 2, 
    grid_dimension: int = 3
):
    num_keyframe_samples = grid_dimension ** 2

    # Process video to grids 
    grid_images_result = process_video_to_grids(
        video_file_path=video_file_path, 
        num_clips=num_segments, 
        clip_stride=clip_stride, 
        K=num_keyframe_samples 
    )

    temporal_sequence: List[Tuple[str, Tuple[float, float]]] = []

    for grid_image, (start_time, end_time) in grid_images_result: 
        # Generate the action labelling prompt 
        action_labelling_prompt = generate_action_labelling_prompt(
            start_time=start_time, 
            end_time=end_time,
            action_vocabulary=action_vocabulary
        )

        # Predict the action label 
        action_label = generate_image_content_gemini_with_retry(
            client=gemini_client, 
            pil_image=grid_image, 
            prompt_text=action_labelling_prompt
        )

        temporal_sequence.append((action_label, (start_time, end_time)))

    action_labels_list = get_action_labels_list(action_vocabulary)
    action_label_to_id_map, id_to_action_label_map = get_action_label_mappings(action_labels_list) 
    action_labels_successors_map = get_action_labels_successors_map(action_labels_list)
    num_action_labels = len(action_labels_list)

    transition_matrix = build_transition_matrix(
        action_labels_list=action_labels_list, 
        action_label_to_id_map=action_label_to_id_map, 
        allowed_successors_map=action_labels_successors_map, 
        p_self=0.5 
    )

    log_transition_matrix = np.log(transition_matrix + 1e-12)

    log_emission_matrix = build_soft_emission_matrix(
        temporal_sequence=temporal_sequence, 
        action_label_to_id_map=action_label_to_id_map
    )

    num_segments = len(temporal_sequence)
    num_action_labels = len(action_label_to_id_map)

    # Uniform initial distribution
    logPi = np.log(np.full((num_action_labels,), 1.0 / num_action_labels, dtype=float))

    # Predict the best path using Viterbi decoding 
    best_path = viterbi_decode(
        logPi=logPi,
        log_transition_matrix=log_transition_matrix,
        log_emission_matrix=log_emission_matrix
    )

    # Reconstruct the smoothed temporal sequence 
    smoothed_temporal_sequence = reconstruct_temporal_action_sequence(
        best_path_ids=best_path, 
        original_input_sequence=temporal_sequence, 
        id_to_action_label_map=id_to_action_label_map, 
        merge_consecutive=True
    )

    return smoothed_temporal_sequence 

def format_temporal_action_segmentation_output(
    temporal_action_sequence: List[Tuple[str, Tuple[float, float]]]
) -> List[Tuple[str, Tuple[float, float]]]:
    """
    Format the output of temporal action segments.
    """
    formatted_segments = []

    for action_label, (start_time, end_time) in temporal_action_sequence:
        formatted_segments.append({
            "action_label": action_label, 
            "start_time": start_time,
            "end_time": end_time
        })

    return formatted_segments 

class TemporalActionSegmentationTool(Tool):
    TOOL_NAME = "temporal_action_segmenter"
    TOOL_CATEGORY = ToolCategory.TEMPORAL
    TOOL_DESCRIPTION = (
        "This tool segments the OSCE video into temporal action segments based on a predefined action vocabulary. ",
        "The output is a list of detected actions with their start and end times. ",
        "The output will be used to provide evidence for the student's performance in the OSCE video against a specific rubric question related to the student's actions and procedural accuracy during the examination."
    )

    def __init__(
        self, 
        gemini_client: genai.Client
    ):
        super().__init__(
            name=self.TOOL_NAME, 
            category=self.TOOL_CATEGORY, 
            description=self.TOOL_DESCRIPTION
        )

        self.gemini_client = gemini_client

    def run(
        self, 
        video_file_path: str,
        action_vocabulary: Dict[str, str],
        num_segments: int = 25,
        clip_stride: float = 2,
        grid_dimension: int = 3
    ):
        try:
            if not os.path.exists(video_file_path):
                raise FileNotFoundError(f"Video file not found: {video_file_path}")

            if not action_vocabulary:
                raise ValueError("Action vocabulary is empty or not provided.")

            temporal_action_segments = generate_temporal_action_segments_grid_wise(
                video_file_path=video_file_path, 
                action_vocabulary=action_vocabulary, 
                gemini_client=self.gemini_client, 
                num_segments=num_segments, 
                clip_stride=clip_stride, 
                grid_dimension=grid_dimension
            )

            formatted_output = format_temporal_action_segmentation_output(temporal_action_segments)
            return formatted_output

        except Exception as e:
            print(f"An error occurred while running the {self.name} tool: {e}")
            return None
        

if __name__ == "__main__":
    video_file_path = os.path.join(
        "./sample_osce_videos", 
        "osce-physical-exam-demo-video-1.mp4"
    )

    action_vocabulary_file_path = os.path.join(
        "./data", 
        "action_vocabulary.json"
    )

    start = time.time()

    action_vocabulary = load_action_vocabulary(action_vocabulary_file_path)

    # # Generate the temporal action segments grid-wise
    # gemini_client = load_gemini_client()

    # temporal_action_segments = generate_temporal_action_segments_grid_wise(
    #     video_file_path=video_file_path, 
    #     action_vocabulary=action_vocabulary, 
    #     gemini_client=gemini_client, 
    #     num_segments=25, 
    #     clip_stride=2, 
    #     grid_dimension=3
    # )

    # print("Temporal Action Segments:")
    # for action_label, (start_time, end_time) in temporal_action_segments:
    #     print(f"Action: {action_label}, Start: {start_time:.2f}s, End: {end_time:.2f}s")

    # formatted_segments = format_temporal_action_segmentation_output(temporal_action_segments)
    # print(formatted_segments)

    temporal_action_segmentation_tool = TemporalActionSegmentationTool(
        gemini_client=load_gemini_client()
    )
    temporal_action_segmentation_tool_output = temporal_action_segmentation_tool.run(
        video_file_path=video_file_path, 
        action_vocabulary=action_vocabulary, 
        num_segments=25, 
        clip_stride=2, 
        grid_dimension=3
    )

    print(temporal_action_segmentation_tool_output)

    end = time.time()
    print(f"Time taken for temporal action segmentation: {end - start:.2f} seconds")
