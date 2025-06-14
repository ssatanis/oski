import os
import time  
from typing import List, Tuple, Optional, TypedDict 

import cv2
import torch
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances # To find closest point to centroid
import matplotlib.pyplot as plt
from transformers import CLIPModel, CLIPProcessor
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms

from core.utils.helpers import get_device 

# constants 
DEFAULT_FRAME_SAMPLE_RATE = 1 
DEFAULT_FPS = 30.0
DEFAULT_CLIP_MODEL_NAME = "openai/clip-vit-base-patch16" # Default CLIP model from Hugging Face
DEFAULT_RESNET_MODEL_NAME = 'resnet34' # Default ResNet model for feature extraction

class VideoMetadata(TypedDict):
    duration_seconds: float 
    fps: float 
    resolution_width: int 
    resolution_height: int 
    size_bytes: int 
    frame_count: int 

def get_video_metadata(video_file_path: str) -> Optional[VideoMetadata]:
    """Extracts metadata (duration, fps, resolution, size) from the video file."""
    if not os.path.exists(video_file_path):
        print(f"Error: Video file not found at {video_file_path}")
        return None
    
    if os.path.getsize(video_file_path) == 0:
        print(f"Error: Video file at {video_file_path} is empty.")
        return None

    cap: Optional[cv2.VideoCapture] = None

    try:
        cap = cv2.VideoCapture(video_file_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file with OpenCV: {video_file_path}")
            return None

        fps_cv: float = cap.get(cv2.CAP_PROP_FPS)
        frame_count_cv: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) 
        width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  
        height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate duration, handle cases where fps or frame_count might be zero or invalid
        duration_seconds: float = 0.0
        if fps_cv > 0 and frame_count_cv > 0:
            duration_seconds = frame_count_cv / fps_cv
        elif frame_count_cv == 0 and fps_cv == 0:
             print(f"Warning: OpenCV reported 0 FPS and 0 frames for {video_file_path}. Metadata might be incomplete.")
        elif frame_count_cv > 0 and fps_cv <= 0:
            print(f"Warning: OpenCV could not determine valid FPS for {video_file_path} (reported {fps_cv}). Duration might be inaccurate.")
        elif frame_count_cv <= 0 and fps_cv > 0:
            print(f"Warning: OpenCV could not determine valid frame count for {video_file_path} (reported {frame_count_cv}). Duration might be inaccurate.")

        size_bytes: int = os.path.getsize(video_file_path)

        if width <= 0 or height <= 0: # Width/height should be positive
            print(f"Warning: Video resolution for {video_file_path} seems invalid (Width: {width}, Height: {height}).")
            # Depending on strictness, you could return None here if resolution is critical.
            # For now, we'll proceed if other data is available but this indicates a potential issue.

        cap.release()
        cap = None

        return {
            "duration_seconds": round(duration_seconds, 3),
            "fps": round(fps_cv, 3) if fps_cv > 0 else 0.0, # Ensure FPS is not negative
            "resolution_width": width,
            "resolution_height": height,
            "size_bytes": size_bytes,
            "frame_count": frame_count_cv
        }
    
    except Exception as e:
        print(f"Error extracting video metadata using OpenCV for {video_file_path}: {e}")
        return None
    
    finally:
        # Ensure cap is released if an error occurs after it's opened and before explicit release
        if cap is not None and cap.isOpened():
            cap.release()

def sample_frames_from_video(       
    video_path: str, 
    frame_sample_rate: int = DEFAULT_FRAME_SAMPLE_RATE, # Sample 1 frame per second initially
) -> Tuple[List[Image.Image], List[float], float]:
    """Samples frames from a video at a specified rate.
    
    Args:
        video_path (str): Path to the input video file.
        frame_sample_rate (int): Rate at which frames are sampled from the video (frames per second).

    Returns:
        Tuple[List[Image.Image], List[float], float]: 
            - List of PIL Image objects of sampled frames.
            - List of timestamps (in seconds) corresponding to each sampled frame.
            - Detected FPS of the video.
        Returns ([], [], 0.0) if video cannot be opened or no frames are sampled.
    """
    candidate_pil_images = []
    candidate_timestamps = []
    fps = 0.0
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return [], [], fps

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            print(f"Warning: FPS is 0 for video {video_path}. Defaulting to 25 FPS.")
            fps = DEFAULT_FPS # Default FPS if not available or 0

        print(f"Video Info: FPS: {fps:.2f}. Sampling frames at ~{frame_sample_rate} FPS...")
        frame_count = 0
        last_sampled_time = -1.0 # Ensure the first frame (or near it) is sampled

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            current_time_sec = frame_count / fps
            if current_time_sec >= last_sampled_time + (1.0 / frame_sample_rate):
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                candidate_pil_images.append(pil_image)
                candidate_timestamps.append(current_time_sec)
                last_sampled_time = current_time_sec
            frame_count += 1

        cap.release()

        print(f"Initially sampled {len(candidate_pil_images)} candidate frames.")
        return candidate_pil_images, candidate_timestamps, fps
    
    except Exception as e:
        print(f"Error during frame sampling: {e}")
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        return [], [], fps

def generate_clip_embeddings(
    pil_images: List[Image.Image],
    clip_model: CLIPModel,
    clip_processor: CLIPProcessor,
    device: str = get_device(),
    batch_size: int = 32
) -> Optional[np.ndarray]:
    """
    Generates CLIP embeddings for a list of PIL Images using Hugging Face model.

    Args:
        pil_images (List[Image.Image]): List of PIL Image objects.
        clip_model (CLIPModel): The loaded Hugging Face CLIP model.
        clip_processor (CLIPProcessor): The Hugging Face CLIP processor.
        device (str): Device to run CLIP on ('cuda', 'mps', or 'cpu').
        batch_size (int): Batch size for processing.

    Returns:
        Optional[np.ndarray]: A NumPy array of normalized embeddings, or None if error.
    """
    if not pil_images:
        return None
        
    print(f"Generating CLIP embeddings for {len(pil_images)} frames...")
    all_embeddings_list = []
    clip_model.eval() # Ensure model is in evaluation mode

    try:
        # Generate CLIP embeddings for sampled frames in batches.
        for i in range(0, len(pil_images), batch_size):
            batch_pil_images = pil_images[i:i+batch_size]
            inputs = clip_processor(
                images=batch_pil_images,
                return_tensors="pt"
            ).to(device)
            
            with torch.no_grad():
                image_features = clip_model.get_image_features(pixel_values=inputs['pixel_values'])
                all_embeddings_list.append(image_features.cpu().numpy())
        
        if not all_embeddings_list:
            print("Could not generate any embeddings from the provided images.")
            return None
            
        embeddings_np = np.vstack(all_embeddings_list)

        # Normalize embeddings (good practice for cosine similarity based clustering)
        embeddings_np = embeddings_np / np.linalg.norm(embeddings_np, axis=1, keepdims=True)

        print(f"Generated {embeddings_np.shape[0]} embeddings with dimension {embeddings_np.shape[1]}.")
        return embeddings_np
    
    except Exception as e:
        print(f"Error generating CLIP embeddings: {e}")
        return None
    
def get_resnet_feature_extractor(
    model_name: str = DEFAULT_RESNET_MODEL_NAME,
    device: str = get_device()
) -> Optional[Tuple[nn.Module, transforms.Compose]]:
    """
    Loads a pre-trained ResNet model and modifies it to be a feature extractor.
    Also returns the appropriate image transformations.

    Args:
        model_name (str): Name of the ResNet model (e.g., 'resnet18', 'resnet50', 'resnet101').
        device (str): Device to load the model onto ('cuda', 'mps', 'cpu').

    Returns:
        Optional[Tuple[nn.Module, transforms.Compose]]:
            The ResNet feature extractor model, the image transformation pipeline, or None on error.
    """
    try:
        print(f"Loading ResNet model: {model_name} for feature extraction...")
        if model_name == 'resnet18':
            weights = models.ResNet18_Weights.IMAGENET1K_V1
            model = models.resnet18(weights=weights)
            output_dim = 512
        elif model_name == 'resnet34':
            weights = models.ResNet34_Weights.IMAGENET1K_V1
            model = models.resnet34(weights=weights)
            output_dim = 512
        elif model_name == 'resnet50':
            weights = models.ResNet50_Weights.IMAGENET1K_V2 # V2 is often better
            model = models.resnet50(weights=weights)
            output_dim = 2048
        elif model_name == 'resnet101':
            weights = models.ResNet101_Weights.IMAGENET1K_V2
            model = models.resnet101(weights=weights)
            output_dim = 2048
        else:
            print(f"Unsupported ResNet model name: {model_name}")
            return None

        # Modify the model to remove the final classification layer (fc)
        # We want the output of the average pooling layer
        model.fc = nn.Identity() # Replace fc layer with an identity layer

        model = model.to(device)
        model.eval() # Set to evaluation mode

        # Get the appropriate transforms
        preprocess = weights.transforms()
        
        print(f"ResNet model '{model_name}' (output dim: {output_dim}) loaded on {device} as feature extractor.")
        return model, preprocess
    except Exception as e:
        print(f"Error loading ResNet model '{model_name}': {e}")
        return None
    
def generate_resnet_embeddings(
    pil_images: List[Image.Image],
    resnet_model: nn.Module, 
    resnet_transform: transforms.Compose,
    device: str = get_device(),
    batch_size: int = 32,
    normalize_embeddings: bool = True 
) -> Optional[np.ndarray]:
    """
    Generates ResNet embeddings for a list of PIL Images.

    Args:
        pil_images (List[Image.Image]): List of PIL Image objects.
        resnet_model (nn.Module): The pre-loaded and modified ResNet feature extractor.
        resnet_transform (transforms.Compose): The preprocessing transform for the ResNet model.
        device (str): Device the model is on ('cuda', 'mps', 'cpu').
        batch_size (int): Batch size for processing.
        normalize_embeddings (bool): Whether to L2 normalize the resulting embeddings.

    Returns:
        Optional[np.ndarray]: A NumPy array of embeddings, or None if an error occurs.
    """
    if not pil_images:
        print("No PIL images provided to generate_resnet_embeddings.")
        return None
    
    if not resnet_model or not resnet_transform:
        print("ResNet model or transform not provided.")
        return None
        
    print(f"Generating ResNet embeddings for {len(pil_images)} frames...")
    all_embeddings_list = []
    resnet_model.eval() # Ensure model is in evaluation mode

    try:
        for i in range(0, len(pil_images), batch_size):
            batch_pil_images = pil_images[i:i+batch_size]
            
            # Apply transformations and create a batch tensor
            # Ensure images are RGB if ResNet expects that (usually does)
            batch_tensors = torch.stack(
                [resnet_transform(img.convert("RGB")) for img in batch_pil_images]
            ).to(device)
            
            with torch.no_grad():
                features = resnet_model(batch_tensors)
                all_embeddings_list.append(features.cpu().numpy())
        
        if not all_embeddings_list:
            print("Could not generate any ResNet embeddings from the provided images.")
            return None
            
        embeddings_np = np.vstack(all_embeddings_list)

        if normalize_embeddings:
            # L2 normalization
            norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
            # Avoid division by zero for zero vectors
            non_zero_norms = norms.squeeze() != 0
            if embeddings_np.ndim == 1 : # Single embedding case (though vstack makes it 2D)
                 if norms != 0: embeddings_np = embeddings_np / norms
            elif embeddings_np.ndim == 2 :
                 embeddings_np[non_zero_norms] = embeddings_np[non_zero_norms] / norms[non_zero_norms]


        print(f"Generated {embeddings_np.shape[0]} ResNet embeddings with dimension {embeddings_np.shape[1]}.")
        return embeddings_np
    
    except Exception as e:
        print(f"Error generating ResNet embeddings: {e}")
        return None
    
def cluster_and_select_keyframes(
    candidate_pil_images: List[Image.Image],
    candidate_timestamps: List[float],
    embeddings_np: np.ndarray,
    num_keyframes: int
) -> List[Tuple[Image.Image, float]]:
    """
    Performs K-Means clustering on embeddings and selects representative frames.
    The keyframes are chosen as the frames closest to the centroids of the clusters formed by the CLIP embeddings.

    Args:
        candidate_pil_images (List[Image.Image]): List of all sampled PIL images.
        candidate_timestamps (List[float]): Timestamps corresponding to candidate_pil_images.
        embeddings_np (np.ndarray): NumPy array of embeddings for the candidate frames.
        num_keyframes (int): The desired number of keyframes (K).

    Returns:
        List[Tuple[Image.Image, float]]: List of (PIL Image, timestamp) for selected keyframes.
    """
    if embeddings_np is None or len(embeddings_np) == 0:
        print("No embeddings provided for clustering.")
        return []
    
    if len(candidate_pil_images) != len(embeddings_np):
        print("Mismatch between number of images and embeddings. Cannot cluster.")
        return []

    # Ensure num_keyframes isn't more than available samples for clustering
    actual_num_clusters = min(num_keyframes, embeddings_np.shape[0])
    if actual_num_clusters < num_keyframes:
        print(f"Warning: Can only create {actual_num_clusters} clusters as only {embeddings_np.shape[0]} embeddings available.")
    
    if actual_num_clusters == 0:
        print("No clusters to create.")
        return []

    print(f"Clustering {embeddings_np.shape[0]} embeddings into {actual_num_clusters} clusters...")
    try:
        kmeans = KMeans(n_clusters=actual_num_clusters, random_state=0, n_init='auto')
        cluster_labels = kmeans.fit_predict(embeddings_np)
        
        # Keep track of original indices of frames already selected to avoid duplicates
        # if multiple cluster centroids map to the same closest actual frame.
        selected_keyframes_data = []
        selected_original_indices = set()
        print("Selecting representative keyframes from clusters...")

        for i in range(actual_num_clusters):
            # Get indices of all frames belonging to the current cluster
            cluster_member_original_indices = np.where(cluster_labels == i)[0]

            if len(cluster_member_original_indices) == 0: 
                continue
            
            # Get the embeddings of the frames in the current cluster
            cluster_member_embeddings = embeddings_np[cluster_member_original_indices]
            # Get the centroid for the current cluster
            cluster_centroid = kmeans.cluster_centers_[i]
            
            # Find the frame in the cluster that is closest to the centroid
            distances_to_centroid = euclidean_distances(cluster_member_embeddings, cluster_centroid.reshape(1, -1))
            closest_index_within_cluster = np.argmin(distances_to_centroid)

            # Map this back to the original index in the candidate_pil_images list
            original_frame_index = cluster_member_original_indices[closest_index_within_cluster]
            
            if original_frame_index not in selected_original_indices:
                selected_keyframes_data.append(
                    (candidate_pil_images[original_frame_index], candidate_timestamps[original_frame_index])
                )
                selected_original_indices.add(original_frame_index)
        
        selected_keyframes_data.sort(key=lambda x: x[1]) # Sort by timestamp
        print(f"Selected {len(selected_keyframes_data)} keyframes after clustering.")
        return selected_keyframes_data
    
    except Exception as e:
        print(f"Error during clustering and keyframe selection: {e}")
        return []

def extract_keyframes_by_clustering(
    video_path: str,
    num_keyframes: int,
    clip_model: Optional[CLIPModel] = None,
    clip_processor: Optional[CLIPProcessor] = None,
    resnet_model: Optional[nn.Module] = None,
    resnet_transform: Optional[transforms.Compose] = None,
    device: str = get_device(),
    frame_sample_rate: int = 1,
    batch_size: int = 32,
    embedding_method: str = 'resnet'  # 'clip' or 'resnet'
) -> List[Tuple[Image.Image, float]]:
    """
    Extracts keyframes from a video using semantic clustering of CLIP embeddings.
    This function orchestrates frame sampling, embedding, and clustering.

    Args:
        video_path (str): Path to the video file.
        num_keyframes (int): The desired number of keyframes (K).
        clip_model (CLIPModel): The loaded Hugging Face CLIP model.
        clip_processor (CLIPProcessor): The Hugging Face CLIP processor.
        device (str): Device to run CLIP on ('cuda', 'mps', or 'cpu').
        frame_sample_rate (int): Rate at which to initially sample frames (FPS).
        batch_size (int): Batch size for processing frames with CLIP.

    Returns:
        List[Tuple[Image.Image, float]]: List of (PIL Image, timestamp) tuples for keyframes.
    """
    if embedding_method == "clip":
        if clip_model is None or clip_processor is None:
            print("CLIP model or processor not provided. Cannot extract keyframes.")
            return []
    elif embedding_method == "resnet":
        if resnet_model is None or resnet_transform is None:
            print("ResNet model or transform not provided. Cannot extract keyframes.")
            return []
    else:
        print(f"Unsupported embedding method: {embedding_method}. Use 'clip' or 'resnet'.")
        return []

    print(f"\nStarting keyframe extraction for '{video_path}'...")

    # Step 1: Sample frames from the video
    candidate_pil_images, candidate_timestamps, _ = sample_frames_from_video(
        video_path, frame_sample_rate
    )

    if not candidate_pil_images:
        print("Keyframe extraction failed: No frames were sampled.")
        return []

    # Handle case where sampled frames are fewer than desired keyframes
    if len(candidate_pil_images) <= num_keyframes:
        print(f"Number of sampled frames ({len(candidate_pil_images)}) is less than or equal to "
              f"desired keyframes ({num_keyframes}). Returning all sampled frames as keyframes.")
        return sorted(list(zip(candidate_pil_images, candidate_timestamps)), key=lambda x: x[1])

    # Step 2: Generate embeddings for the sampled frames
    if embedding_method.lower() == 'resnet':
        embeddings_np = generate_resnet_embeddings(
            candidate_pil_images, resnet_model, resnet_transform, device, batch_size
        )
    elif embedding_method.lower() == 'clip':
        embeddings_np = generate_clip_embeddings(
            candidate_pil_images, clip_model, clip_processor, device, batch_size
        )

    if embeddings_np is None or embeddings_np.shape[0] == 0:
        print("Keyframe extraction failed: Could not generate embeddings.")
        return []
    
    # Step 3: Cluster embeddings and select representative keyframes
    selected_keyframes = cluster_and_select_keyframes(
        candidate_pil_images, candidate_timestamps, embeddings_np, num_keyframes
    )
    
    print(f"Keyframe extraction process completed. Found {len(selected_keyframes)} keyframes.")
    return selected_keyframes

def plot_keyframes(
    keyframes: List[Tuple[Image.Image, float]], 
    max_cols: int = 5, 
    fig_title: str = "Extracted Keyframes"
):
    """
    Plots the extracted keyframes in a grid layout.

    Args:
        keyframes (List[Tuple[Image.Image, float]]): List of (PIL Image, timestamp) tuples for keyframes.
        max_cols (int): Maximum number of columns in the plot grid.
        fig_title (str): Title for the figure.
    """
    if not keyframes:
        print("No keyframes to plot.")
        return
    num_frames = len(keyframes)
    num_rows = (num_frames - 1) // max_cols + 1
    fig, axes = plt.subplots(num_rows, max_cols, figsize=(max_cols * 3, num_rows * 2.5))
    fig.suptitle(fig_title, fontsize=16)

    if num_frames == 1:
        ax_list = [axes.item() if isinstance(axes, np.ndarray) and axes.size == 1 else axes]
    else:
        ax_list = axes.flatten()

    for i, (frame_img, timestamp) in enumerate(keyframes):
        if i < len(ax_list):
            ax = ax_list[i]
            ax.imshow(frame_img)
            ax.set_title(f"T: {timestamp:.2f}s")
            ax.axis('off')

    for j in range(i + 1, len(ax_list)): # Use i from the loop, not num_frames
        if j < len(ax_list): ax_list[j].axis('off')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    # Example usage 
    sample_video_path = os.path.join("sample_osce_videos", "osce-demo-video-1.mp4")

    device = get_device()

    video_metadata = get_video_metadata(sample_video_path)
    print(video_metadata)

    try:
        clip_processor_instance = CLIPProcessor.from_pretrained(DEFAULT_CLIP_MODEL_NAME) 
        clip_model_instance = CLIPModel.from_pretrained(DEFAULT_CLIP_MODEL_NAME).to(device)

        print(f"Hugging Face CLIP model loaded successfully on {device}.")

        resnet_model, resnet_transform = get_resnet_feature_extractor(
            model_name=DEFAULT_RESNET_MODEL_NAME,
            device=device
        )

        print(f"ResNet model '{DEFAULT_RESNET_MODEL_NAME}' loaded successfully on {device}.")

    except Exception as e:
        print(f"Error loading Hugging Face CLIP model: {e}")
        exit()

    desired_num_keyframes = 20
    print(f"Extracting {desired_num_keyframes} keyframes from video '{sample_video_path}'...")

    if clip_model_instance is None or clip_processor_instance is None:
        print("CLIP model or processor not initialized. Exiting.")
        exit()

    if resnet_model is None or resnet_transform is None:
        print("ResNet model or transform not initialized. Exiting.")
        exit()

    try:
        start = time.time()

        extracted_keyframes_data = extract_keyframes_by_clustering(
            video_path=sample_video_path,
            num_keyframes=desired_num_keyframes,
            resnet_model=resnet_model,
            resnet_transform=resnet_transform,
            device=device,
            frame_sample_rate=1,  # Sample 1 frame per second
            batch_size=16,
            embedding_method="resnet"
        )
        end = time.time()

        if extracted_keyframes_data:
            print(f"\nSuccessfully extracted {len(extracted_keyframes_data)} keyframes in {end - start:.2f} seconds.")

            plot_keyframes(
                extracted_keyframes_data, 
                max_cols=min(desired_num_keyframes, 5), 
                fig_title=f"Top {len(extracted_keyframes_data)} Keyframes."
            )
        else:
            print("No keyframes were extracted from the video.")

    except Exception as e:
        print(f"Error during keyframe extraction: {e}")
        exit()

    finally:
        # Clean up resources
        if clip_model_instance is not None:
            del clip_model_instance

        if clip_processor_instance is not None:
            del clip_processor_instance

        if resnet_model is not None:
            del resnet_model

        if resnet_transform is not None:
            del resnet_transform

        torch.cuda.empty_cache()
        print("Resources cleaned up. Exiting.")






