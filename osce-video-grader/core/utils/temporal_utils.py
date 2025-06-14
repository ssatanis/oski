import json 
from typing import List, Tuple, Type, Union, Dict  

import cv2
import numpy as np  
from PIL import Image
import matplotlib.pyplot as plt
from moviepy.video.io.VideoFileClip import VideoFileClip

DEFAULT_NUM_CLIPS = 25
DEFAULT_CLIP_STRIDE = 2 # in seconds 

def generate_overlapping_clip_time_segments(
    video_file_path: str, 
    num_clips: int = DEFAULT_NUM_CLIPS, 
    clip_stride: int = DEFAULT_CLIP_STRIDE
):
    """
    Splits a video into at most `num_clips` overlapping clips, each of duration D, 
    where D is chosen so that:
        T = ceil((L - D) / clip_stride) + 1 <= num_clips 

    Args: 
        video_path (str): Path to the input video file 
        num_clips (int): The maximum number of overlapping clips. 
        clip_stride (float): Time in seconds between the start of the i th clip and the (i + 1)th clip. 
                                This must satisfy 0 < clip_stride <= D (once D is computed). 
    
    Returns:
        clips (List[Tuple[float, float]]): A list of (start_time, end_time) tuples, in seconds, for each clip. 
                                            Consecutive clips overlap by (D - clip_stride) seconds.
    """
    # Compute video length (in seconds)
    cap = cv2.VideoCapture(video_file_path)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_file_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()

    if fps <= 0 or total_frames <= 0:
        raise RuntimeError("Unable to determine video length (FPS or frame count is invalid).")

    video_duration = total_frames / fps # total duration of the video (in seconds)

    # Calculate the effective duration of each clip 
    clip_length = (video_duration + (num_clips - 1) * clip_stride) / num_clips 

    segments = []
    current_start_time = 0.0 

    for i in range(num_clips):
        start_time = current_start_time 
        end_time = start_time + clip_length 

        if i == num_clips - 1:
            end_time = video_duration 
        else:
            end_time = min(end_time, video_duration)

        segments.append((round(start_time, 2), round(end_time, 2)))

        # Determine the start time for the next clip 
        if i < num_clips - 1:
            current_start_time = end_time - clip_stride 

            # Ensure the next start time is not negative 
            current_start_time = max(0, current_start_time)

            current_start_time = min(current_start_time, video_duration)

    return segments 

def sample_frames_from_clip(
    video_obj: VideoFileClip, 
    start_time: float, 
    end_time: float, 
    K: int 
) -> List[np.ndarray]:
    """Uniformly samples K keyframes from a given clip segment of a video.
    
    Args:
        video_obj: The video object.
        start_time (float): The start time of the clip in seconds. 
        end_time (float): The end time of the clip in seconds. 
        K (int): The number of keyframes to sample.

    Returns:
        list: A list of K numpy arrays, each representing a frame. 
    """
    frames = []
    clip_duration = end_time - start_time 
    video_total_duration = video_obj.duration 

    # Handle effectively zero-duration clips 
    if clip_duration < 1e-5:
        # For a zero-duration clip, all K frames will be the same.
        # Sample at start_time (or as close as possible and valid).
        # Ensure the sample time is valid for get_frame (>=0 and < video_total_duration)
        sample_t = start_time
        if sample_t >= video_total_duration and video_total_duration > 0:
            sample_t = video_total_duration - 0.001 # Small offset from the end
        elif sample_t >= video_total_duration:
             sample_t = 0.0
        sample_t = max(0.0, sample_t) # Ensure not negative

        try:
            frame = video_obj.get_frame(sample_t)
            # Use .copy() if these frames might be modified or to ensure distinct objects
            return [frame.copy() for _ in range(K)]
        
        except Exception as e:
            print(f"Warning: Could not get frame for near-zero-duration clip [{start_time:.2f}, {end_time:.2f}] at {sample_t:.3f}. Error: {e}")
            return []
        
    segment_duration = clip_duration / K 
    for i in range(K):
        # Midpoint of the i-th segment within the clip's relative time
        time_within_clip = (i + 0.5) * segment_duration
        absolute_timestamp = start_time + time_within_clip

        # Defensive clamping (though theoretically less needed with this sampling method)
        safe_timestamp = max(0.0, absolute_timestamp)
        if safe_timestamp >= video_total_duration and video_total_duration > 0:
            safe_timestamp = video_total_duration - 0.001 
        elif safe_timestamp >= video_total_duration : # video_total_duration is 0 or tiny
            safe_timestamp = 0.0
        
        # Ensure it's within the original clip segment's bounds after any clamping
        safe_timestamp = max(start_time, min(safe_timestamp, end_time - 1e-6 if end_time > start_time else end_time))


        try:
            frame_data = video_obj.get_frame(safe_timestamp)
            frames.append(frame_data)
        except IndexError: # MoviePy can raise IndexError if time is out of bounds
            print(f"Warning: IndexError getting frame at {safe_timestamp:.4f} (orig {absolute_timestamp:.4f}) for clip [{start_time:.2f}-{end_time:.2f}]. Video duration {video_total_duration:.2f}.")
        except Exception as e:
            print(f"Warning: Failed to get frame at {safe_timestamp:.4f} (orig {absolute_timestamp:.4f}) for clip [{start_time:.2f}-{end_time:.2f}]. Error: {e}")

    return frames

def create_image_grid(
    frames_list: List[np.ndarray], 
    N: int
) -> Union[Image.Image, None]:
    """
    Combines a list of K frames (K = N*N) into an N x N grid image. 

    Args:
        frames_list: A list of K NumPy arrays, each representing a frame. 
                        K must be equal to N * N. 
        N: The dimension of the grid. 

    Returns: 
        Image.Image: A Pillow Image object representing the grid, or None if an error occurred. 
    """
    K = len(frames_list)

    if K != N * N: 
        print(f"Error: Number of frames ({K}) does not match required K={N*N} for an {N}*{N} grid.")
        return None 
    
    try: 
        frame_height, frame_width, n_channels = frames_list[0].shape 
        if n_channels not in [3, 4]: # RGB or RGBA 
            print(f"Warning: Unexpected number of channels ({n_channels}) in frame. Assuming RGB if 3, RGBA if 4.")
    
    except Exception as e:
        print(f"Error getting frame dimensions: {e}")
        return None 
    
    # Create a blank canvas for the grid 
    grid_image_np = np.zeros((N * frame_height, N * frame_width, n_channels), dtype=np.uint8)

    for i, frame_np in enumerate(frames_list):
        if frame_np.shape != (frame_height, frame_width, n_channels): 
            print(f"Warning: Frame {i} has inconsistent dimensions. Skipping. Expected {frame_height}x{frame_width}x{n_channels}, got {frame_np.shape}")
            # Optionally, fill with black or a placeholder
            continue 

        row = i // N 
        col = i % N 

        y_offset = row * frame_height 
        x_offset = col * frame_width 

        grid_image_np[y_offset : y_offset + frame_height, x_offset : x_offset + frame_width, :] = frame_np 
    
    try:
        if n_channels == 4: 
            grid_image_pil = Image.fromarray(grid_image_np, "RGBA")
        else: 
            grid_image_pil = Image.fromarray(grid_image_np, "RGB") 

        return grid_image_pil 
    
    except Exception as e: 
        print(f"Error converting NumPy grid to Pillow Image: {e}")
        return None
    
def process_video_to_grids(
    video_file_path: str, 
    K: int,
    num_clips: int = DEFAULT_NUM_CLIPS,
    clip_stride: float = DEFAULT_CLIP_STRIDE
) -> List[Tuple[Image.Image, Tuple[float, float]]]:
    """
    Processes a video to generate clip time segments, sample frames from each clip, 
    and combine sampled frames into an N x N grid for clip-wise temporal action segmentation. 

    Args:
        video_file_path (str): The path to the input video. 
        K (int): The number of keyframes to be sampled from each clip. K must be a perfect square (K = N*N). 
        num_clips (int): The total number of clips to used from the video. 
        clip_stride (float): The clip stride.

    Returns: 
        List[Image.Image]: A list of tuples containing the start_time, end_time, and Pillow image object, 
                            where each image is an N x N grid for a clip. 
                            Returns None if errors occur or no grids can be generated. 
    """
    try:
        # Generate clip time segments 
        try: 
            clip_time_segments = generate_overlapping_clip_time_segments(
                video_file_path=video_file_path, 
                num_clips=num_clips, 
                clip_stride=clip_stride 
            )

        except Exception as e: 
            print(f"Error: Clip time segments could not be generated: {e}.")
            return None 
        
        grid_images_result = []
        N = np.sqrt(K) 
        
        for i, (start_time, end_time) in enumerate(clip_time_segments):
            video_obj = VideoFileClip(video_file_path)

            # Sample frames from each clip
            sampled_frames = sample_frames_from_clip(
                video_obj, 
                start_time=start_time, 
                end_time=end_time, 
                K=K 
            ) 
            
            # Create the image grid from the list of sampled frames 
            grid_image = create_image_grid(
                frames_list=sampled_frames, 
                N=int(N)
            )

            grid_images_result.append((grid_image, (start_time, end_time)))

        return grid_images_result

    except Exception as e:
        print(f"An error occurred: {e}")
        return None 
    
def plot_video_clip_grids(grid_data: List[Tuple[Image.Image, tuple[float, float]]], n_cols: int):
    """
    Plots the generated video image grids in a grid layout with titles.

    Args:
        grid_data: A list of tuples, with each tuple containing
                   (Pillow_Image, (start_time, end_time)). This is the
                   output of the process_video_to_grids function.
        n_cols: The desired number of columns in the plot layout.
    """
    if not grid_data:
        print("No grid data to plot.")
        return

    num_grids = len(grid_data)
    # Calculate the number of rows needed
    n_rows = int(np.ceil(num_grids / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 5, n_rows * 3))
    
    # Flatten the axes array to easily iterate over it, regardless of its shape
    if num_grids == 1:
        axes_flat = [axes]
    else:
        axes_flat = axes.flatten()

    for i, (grid_image, (start_t, end_t)) in enumerate(grid_data):
        ax = axes_flat[i]
        
        # Display the grid image
        ax.imshow(grid_image)
        
        # Set the title for the subplot with the clip's timestamp
        ax.set_title(f"Clip {i+1}: {start_t:.2f}s - {end_t:.2f}s", fontsize=12)
        
        # Hide the x and y axes for a cleaner look
        ax.axis('off')

    # Hide any unused subplots if the number of grids isn't a perfect multiple of n_cols
    for i in range(num_grids, len(axes_flat)):
        axes_flat[i].axis('off')

    # Adjust layout to prevent titles from overlapping
    plt.tight_layout()
    
    # Show the plot
    plt.show()

def load_action_vocabulary(
    action_vocabulary_path: str
) -> Dict[str, str]:
    """
    Loads the action vocabulary from a JSON file.
    Args:
        action_vocabulary_path (str): Path to the JSON file containing the action vocabulary.
    Returns:
        Dict[str, str]: A dictionary mapping action labels to their descriptions.
    """                 
    try:
        with open(action_vocabulary_path, 'r') as file:
            action_vocabulary = json.load(file)
        return action_vocabulary
    
    except FileNotFoundError:
        print(f"Error: Action vocabulary file '{action_vocabulary_path}' not found.")
        return {}
    
def get_action_labels_list(
    action_vocabulary: Dict[str, str]
):
    """
    Extracts the action labels from the action vocabulary dictionary.
    
    Args:
        action_vocabulary (Dict[str, str]): The action vocabulary dictionary.
        
    Returns:
        List[str]: A list of action labels.
    """
    if not isinstance(action_vocabulary, dict):
        raise ValueError("action_vocabulary must be a dictionary.")
    
    return list(action_vocabulary.keys())

def get_action_label_mappings(
    action_labels_list: List[str]
):
    """
    Creates mappings from action labels to IDs and vice versa.
    
    Args:
        action_labels_list (List[str]): A list of action labels.
        
    Returns:
        Tuple[Dict[str, int], Dict[int, str]]: A tuple containing two dictionaries:
            - action_label_to_id_map: Maps action labels to unique IDs.
            - id_to_action_label_map: Maps unique IDs back to action labels.
    """
    if not isinstance(action_labels_list, list):
        raise ValueError("action_labels_list must be a list.")
    
    action_label_to_id_map = {lbl: idx for idx, lbl in enumerate(action_labels_list)}
    id_to_action_label_map = {v: k for k, v in action_label_to_id_map.items()}
    
    return action_label_to_id_map, id_to_action_label_map

def get_action_labels_successors_map(
    action_labels_list: List[str]
) -> Dict[str, List[str]]:
    """
    Creates a mapping of action labels to their successors.
    
    Args:
        action_labels_list (List[str]): A list of action labels.
        
    Returns:
        Dict[str, List[str]]: A dictionary mapping each action label to a list of its successors.
    """
    action_labels_successors_map = {
        "greeting_patient": ["explaining_procedure", "background_or_transition"],
        "explaining_procedure": ["history_taking", "background_or_transition"],
        "history_taking": ["hand_hygiene", "background_or_transition"],
        "hand_hygiene": ["inspecting_hands_or_nails", "background_or_transition"],
        "inspecting_hands_or_nails": ["palpating_pulses", "background_or_transition"],
        "palpating_pulses": ["palpating_abdomen", "inspecting_general_body_region", "background_or_transition"],
        "palpating_abdomen": ["inspecting_eyes", "background_or_transition"],
        "inspecting_eyes": ["inspecting_mouth", "background_or_transition"],
        "inspecting_mouth": ["applying_blood_pressure_cuff", "background_or_transition"],
        "applying_blood_pressure_cuff": ["using_sphygmomanometer", "background_or_transition"],
        "using_sphygmomanometer": ["using_thermometer", "background_or_transition"],
        "using_thermometer": ["using_pulse_oximeter", "background_or_transition"],
        "using_pulse_oximeter": ["palpating_neck_lymph_nodes_thyroid", "background_or_transition"],
        "palpating_neck_lymph_nodes_thyroid": ["palpating_limbs_for_edema", "background_or_transition"],
        "palpating_limbs_for_edema": ["positioning_patient", "using_reflex_hammer", "background_or_transition"],
        "positioning_patient": ["using_stethoscope", "background_or_transition"],
        "using_stethoscope": ["documenting_notes", "background_or_transition"],
        "documenting_notes": ["discussing_findings_with_patient", "active_listening", "background_or_transition"],
        "inspecting_ears_external": ["inspecting_eyes", "using_otoscope", "background_or_transition"],
        "inspecting_general_body_region": ["palpating_pulses", "palpating_abdomen", "background_or_transition"],
        "using_otoscope": ["inspecting_ears_external", "background_or_transition"],
        "using_ophthalmoscope": ["inspecting_eyes", "background_or_transition"],
        "using_reflex_hammer": ["palpating_limbs_for_edema", "background_or_transition"],
        "active_listening": ["documenting_notes", "background_or_transition"],
        "discussing_findings_with_patient": ["background_or_transition"], # Once the student is discussing findings, the exam is effectively over.
        "background_or_transition": [
            a for a in action_labels_list if a != "background_or_transition"
        ], # Stay in 'background_or_transition' or transition to any other action 
        "no_action": [
            a for a in action_labels_list if a != "no_action"
        ] # Stay in 'no_action' or transition to any other action
    }

    return action_labels_successors_map 

def generate_action_labelling_prompt(
    start_time: float, 
    end_time: float,
    action_vocabulary: Dict[str, str] 
):
    vocab_string = "\n\n".join([f"ACTION LABEL: {action_key}\nDESCRIPTION: {action_description}" for action_key, action_description in action_vocabulary.items()])
    clip_duration = end_time - start_time 

    prompt = f"""
    You are an advanced AI video analysis system specializing in temporal action recognition. Your purpose is to identify the primary action occurring within a short video clip. 
    This classification will be used as a building block for creating a complete temporal action segmentation of a longer video. 
    Accuracy, consistency, and adherence to the specified format are critical.

    ## INPUT DESCRIPTION 
    You will be provided with two pieces of information: the visual data and its timing context.

    **A: Visual Data: The Keyframe Grid:** 

    The image you are analyzing is an N x N grid of video clip frames. These frames are extracted uniformly and sequentially from a video clip.

    **Crucially, this grid represents time.** It must be read like a book:
    - **From left-to-right, then top-to-bottom.**
    - The top-left frame is the EARLIEST moment in the clip.
    - The bottom-right frame is the LATEST moment in the clip.

    **B. Timing Context: The Clip's Duration**

    This grid of frames was extracted from the following time segment of the main video:
    - **Start Time:** `{start_time}` seconds
    - **End Time:** `{end_time}` seconds
    - **Total Clip Duration:** `{clip_duration}` seconds

    Your analysis must consider this temporal progression to understand the action's flow.

    ## YOUR TASK
    Analyze the provided grid of keyframes to determine the **single, most dominant action** represented. 
    "Dominant action" means the action that is most central to the clip's narrative or is sustained for the longest duration.

    ## ACTION VOCpABULARY 
    You MUST choose one action from the following predefined list. This list includes a special `no_action` category for when no specific action is taking place.

    Action Vocabulary:

    {vocab_string}

    ## REASONING GUIDELINES
    To make your decision, follow these principles:
    - **Analyze Temporal Progression:** Pay close attention to the sequence of frames. How does a subject's posture or position change from one frame to the next?
    - **Synthesize Holistically:** Do not base your decision on a single frame alone. The correct label should be a summary of the entire sequence.
    - **Identify the Dominant Action:** If multiple minor actions are present, focus on the one that best summarizes the entire clip's duration.
    - **Focus on the Verb:** Your primary goal is to label the action (the *verb*), not the objects or the scene (the *nouns*).

    ## OUTPUT FORMAT 
    You MUST provide your response as a single action label from the action vocabulary.
    Do not include any other text, explanation, Markdown formatting, or conversational filler. 

    **Example Output:**
    {list(action_vocabulary.keys())[0]}

    **Example Output:** 
    {list(action_vocabulary.keys())[5]}
    """

    return prompt

if __name__ == "__main__":
    video_file_path = "sample_osce_videos/osce-physical-exam-demo-video-1.mp4"

    # Test clip time segments generation 
    clip_time_segments = generate_overlapping_clip_time_segments(video_file_path)
    for i, (start, end) in enumerate(clip_time_segments):
        print(f"Clip {i + 1}: Start = {start}s, End = {end}s")

    # Test frame sampling from the first clip
    video_obj = VideoFileClip(video_file_path)

    N = 3 
    K = N**2 

    sampled_frames = sample_frames_from_clip(
        video_obj, 
        start_time=clip_time_segments[0][0], 
        end_time=clip_time_segments[0][1], 
        K=K 
    )

    assert len(sampled_frames) == K, f"Expected {K} frames, got {len(sampled_frames)}"
    print(f"Sampled {len(sampled_frames)} frames from clip [{clip_time_segments[0][0]}s, {clip_time_segments[0][1]}s].")

    # Testing image grid creation
    grid_image = create_image_grid(sampled_frames, N)
    if grid_image is not None:
        print(f"Created image grid of size {grid_image.size} for {N}x{N} frames.")
    else:
        print("Failed to create image grid.")

    # Testing the full video clip image grid processing pipeline 
    grids = process_video_to_grids(
        video_file_path=video_file_path, 
        K=K
    )

    if grids is not None:
        assert len(grids) == len(clip_time_segments), "Number of grids should match number of clips."
        print(f"Generated {len(grids)} grid images from the video.")
    else:
        print("Failed to process video into grid images.")

    # Testing loading of action vocabulary 
    action_vocabulary_path = "data/action_vocabulary.json"
    action_vocabulary = load_action_vocabulary(action_vocabulary_path)
    if action_vocabulary:
        print(f"Loaded action vocabulary with {len(action_vocabulary)} actions.")
    else:
        print("Failed to load action vocabulary.")

    # Testing action labelling prompt generation
    if action_vocabulary:
        try: 
            start_time = 0.0
            end_time = 10.0
            prompt = generate_action_labelling_prompt(
                start_time=start_time, 
                end_time=end_time, 
                action_vocabulary=action_vocabulary
            )
            print("Successfully generated action labelling prompt.")
        except Exception as e:
            print(f"Error generating action labelling prompt: {e}")