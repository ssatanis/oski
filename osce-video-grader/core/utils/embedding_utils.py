from functools import lru_cache
from typing import Union, Optional, List, Tuple

import torch 
import numpy as np
from PIL import Image 
from transformers import CLIPModel, CLIPProcessor, ClapModel, AutoProcessor  
from sentence_transformers import SentenceTransformer 

from core.utils.helpers import get_device
from core.utils.audio_processor import DEFAULT_SAMPLING_RATE, resample_audio

DEFAULT_CLIP_MODEL_NAME = "openai/clip-vit-base-patch16"
DEFAULT_CLAP_MODEL_NAME = "laion/clap-htsat-fused"
DEFAULT_SENTENCE_TRANSFORMER_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_CLIP_EMBEDDING_DIM = 512
DEFAULT_CLAP_EMBEDDING_DIM = 512 
DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_DIM = 384

CLAP_SAMPLING_RATE = 48000

def load_clip_model_and_processor(
    model_name: str = DEFAULT_CLIP_MODEL_NAME,
    device: str = get_device()
) -> Tuple[CLIPModel, CLIPProcessor]:
    """
    Loads a CLIP model and its processor.

    Args:
        model_name (str): The Hugging Face model identifier for CLIP.
        device (str): The device to load the model onto (e.g., 'cpu', 'cuda').

    Returns:
        Tuple[CLIPModel, CLIPProcessor]: The loaded CLIP model and processor.
    """
    print(f"Loading CLIP model '{model_name}' on device '{device}'...")
    
    try:
        model = CLIPModel.from_pretrained(model_name).to(device)
        processor = CLIPProcessor.from_pretrained(model_name)
        
        print(f"CLIP model '{model_name}' loaded successfully on {device}.")
        return model, processor
    
    except Exception as e:
        print(f"Error loading CLIP model '{model_name}': {e}")
        raise

@torch.no_grad()
def generate_clip_image_embedding(
    pil_image: Image.Image,
    model: CLIPModel, 
    processor: CLIPProcessor, 
    device: str = get_device()
) -> np.ndarray:
    inputs = processor(
        images=pil_image,
        return_tensors="pt"
    ).to(device)

    image_features = model.get_image_features(**inputs)
    emb = image_features.cpu().numpy().flatten()
    return emb / np.linalg.norm(emb)

@torch.no_grad()
def generate_clip_image_embeddings_batch(
    pil_images: List[Image.Image],
    model: CLIPModel,
    processor: CLIPProcessor,
    device: str = get_device(),
    batch_size: int = 32
) -> Optional[np.ndarray]:
    if not pil_images:
        return None
    
    all_embeddings_list = []
    model.eval()

    try:
        for i in range(0, len(pil_images), batch_size):
            batch_pil_images = pil_images[i:i+batch_size]
            inputs = processor(images=batch_pil_images, return_tensors="pt").to(device)
            image_features = model.get_image_features(pixel_values=inputs['pixel_values'])
            all_embeddings_list.append(image_features.cpu().numpy())

        if not all_embeddings_list: 
            return None
        
        embeddings_np = np.vstack(all_embeddings_list)
        return embeddings_np / np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    
    except Exception as e:
        print(f"Error generating batch CLIP image embeddings: {e}"); return None

@torch.no_grad()
def generate_clip_text_embedding(
    text: str,
    model: CLIPModel, 
    processor: CLIPProcessor,
    device: str = get_device()
) -> np.ndarray:
    inputs = processor(
        text=[text], 
        return_tensors="pt", 
        padding=True, 
        truncation=True
    ).to(device)

    text_features = model.get_text_features(**inputs)
    emb = text_features.cpu().numpy().flatten()
    return emb / np.linalg.norm(emb)

@torch.no_grad
def generate_clip_text_embeddings_batch(
    texts: List[str],
    model: CLIPModel,
    processor: CLIPProcessor,
    device: str = get_device(),
    batch_size: int = 32
) -> Optional[np.ndarray]:
    """
    Generates CLIP text embeddings for a list of texts in batches.

    Args:
        texts (List[str]): The list of input text strings.
        model (CLIPModel): A pre-loaded CLIP text model.
        processor (CLIPProcessor): The corresponding CLIP processor.
        device (str): Torch device string (e.g., "cuda" or "cpu").
        batch_size (int): Number of texts to process per batch.

    Returns:
        Optional[np.ndarray]: A 2D array of shape (len(texts), D), where D is
        the CLIP text embedding dimension; or None on error.
    """
    if model is None or processor is None:
        print("CLIP model or processor not provided.")
        return None

    model = model.to(device)
    all_embeddings: List[np.ndarray] = []

    try:
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]

            # Tokenize/process the batch of texts
            inputs = processor(
                text=batch,
                return_tensors="pt",
                padding=True,
                truncation=True
            ).to(device)

            text_features = model.get_text_features(**inputs)

            emb_batch = text_features.cpu().numpy()

            # Normalize each embedding vector
            norms = np.linalg.norm(emb_batch, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb_batch = emb_batch / norms

            all_embeddings.append(emb_batch)

        # Concatenate all batch embeddings into one array
        return np.vstack(all_embeddings)

    except Exception as e:
        print(f"Error generating CLIP text embeddings batch: {e}")
        return None

@lru_cache(maxsize=4)
def load_sentence_transformer_model(model_name: str = DEFAULT_SENTENCE_TRANSFORMER_MODEL) -> SentenceTransformer:
    """
    Loads and caches a SentenceTransformer model.

    Args:
        model_name (str): The SentenceTransformer model identifier.

    Returns:
        SentenceTransformer: The loaded model instance.
    """
    print(f"Loading SentenceTransformer model: {model_name}...")
    try:
        model = SentenceTransformer(model_name)
        print(f"SentenceTransformer model '{model_name}' loaded successfully.")
        return model
    
    except Exception as e:
        print(f"Error loading SentenceTransformer model '{model_name}': {e}")
        raise

def generate_sentence_embedding(
    text_input: Union[str, List[str]],
    model: SentenceTransformer,
    normalize_embeddings: bool = True
) -> Optional[np.ndarray]:
    """
    Generates a sentence embedding for the given text(s) using a pre-loaded
    SentenceTransformer model instance.

    Args:
        text_input (Union[str, List[str]]): The text or list of texts to embed.
        model (SentenceTransformer): The pre-loaded SentenceTransformer model.
        normalize_embeddings (bool): Whether to normalize embeddings.

    Returns:
        Optional[np.ndarray]: Embedding(s) or None if an error occurs.
    """
    if model is None:
        print("SentenceTransformer model instance not provided.")
        return None
    
    try:
        embeddings = model.encode(
            text_input,
            convert_to_numpy=True
        )
        
        if normalize_embeddings:
            # Ensure normalization is robust for single or multiple embeddings
            if embeddings.ndim == 1: # Single embedding
                norm = np.linalg.norm(embeddings)
                if norm == 0: return embeddings # Avoid division by zero
                embeddings = embeddings / norm

            elif embeddings.ndim == 2: # Batch of embeddings
                norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
                # Avoid division by zero for zero vectors in the batch
                non_zero_rows = norm.squeeze() != 0
                embeddings[non_zero_rows] = embeddings[non_zero_rows] / norm[non_zero_rows]

        return embeddings
    
    except Exception as e:
        print(f"Error generating sentence embedding: {e}")
        return None
    
def generate_sentence_embeddings_batch(
    texts: List[str],
    model: SentenceTransformer,
    batch_size: int = 32,
    normalize_embeddings: bool = True
) -> Optional[np.ndarray]:
    """
    Generates sentence embeddings for a list of texts in batches.

    Args:
        texts (List[str]): The list of input sentences/documents.
        model_instance (SentenceTransformer): The pre-loaded model.
        batch_size (int): How many texts to encode at once.
        normalize_embeddings (bool): Whether to apply L2-normalization.

    Returns:
        Optional[np.ndarray]: A 2D array of shape (len(texts), dim), or
        None if an error occurs.
    """
    if model is None:
        print("SentenceTransformer model instance not provided.")
        return None

    all_embeddings: List[np.ndarray] = []
    try:
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]

            emb = model.encode(
                batch,
                convert_to_numpy=True
            )
            if normalize_embeddings:
                # normalize each row
                if emb.ndim == 1:
                    norm = np.linalg.norm(emb)
                    if norm != 0:
                        emb = emb / norm
                else:
                    norms = np.linalg.norm(emb, axis=1, keepdims=True)
                    non_zero = norms.squeeze() != 0
                    emb[non_zero] /= norms[non_zero]
            all_embeddings.append(emb)

        return np.vstack(all_embeddings)

    except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        return None
    
def load_clap_model_and_processor(
    model_name: str = DEFAULT_CLAP_MODEL_NAME,
    device: str = get_device()
) -> Tuple[ClapModel, AutoProcessor]:
    """
    Loads a CLAP model and its processor.

    Args:
        model_name (str): The Hugging Face model identifier for CLIP.
        device (str): The device to load the model onto (e.g., 'cpu', 'cuda').

    Returns:
        Tuple[CLAPModel, AutoProcessor]: The loaded CLAP model and processor.
    """
    print(f"Loading CLAP model '{model_name}' on device '{device}'...")
    
    try:
        model = ClapModel.from_pretrained(model_name).to(device)
        processor = AutoProcessor.from_pretrained(model_name)
        
        print(f"CLAP model '{model_name}' loaded successfully on {device}.")
        return model, processor
    
    except Exception as e:
        print(f"Error loading CLAP model '{model_name}': {e}")
        raise

@torch.no_grad()
def generate_clap_audio_embedding(
    audio_data: np.ndarray,       # Single audio waveform as a NumPy array
    model: ClapModel,
    processor: AutoProcessor,
    device: str = get_device(),
    original_sampling_rate: int = DEFAULT_SAMPLING_RATE, 
    target_sampling_rate: int = CLAP_SAMPLING_RATE
) -> np.ndarray:
    """
    Generates CLAP audio embedding for a single audio waveform.

    Args:
        audio_data (np.ndarray): The input audio waveform.
        sampling_rate (int): The sampling rate of the audio_data.
        model (ClapModel): A pre-loaded CLAP model.
        processor (AutoProcessor): The corresponding CLAP processor.
        device (str): Torch device string.

    Returns:
        np.ndarray: A 1D array representing the normalized CLAP audio embedding.
    """
    if model is None or processor is None:
        raise ValueError("CLAP model or processor not provided.")
    
    model = model.to(device)
    model.eval()

    # Resample
    if original_sampling_rate != target_sampling_rate:
        audio_data_resampled = resample_audio(
            audio_data,
            original_sampling_rate, 
            target_sampling_rate
        )
    else:
        audio_data_resampled = audio_data

    inputs = processor(
        audios=[audio_data_resampled], # Processor expects a list of audios
        sampling_rate=target_sampling_rate,
        return_tensors="pt",
        padding=True # Padding helps, even for a single item if model expects fixed input
    ).to(device)

    audio_features = model.get_audio_features(**inputs)
    emb = audio_features.cpu().numpy().flatten()
    
    # Normalize the embedding
    norm = np.linalg.norm(emb)
    if norm == 0: # Avoid division by zero
        return emb 
    return emb / norm

@torch.no_grad()
def generate_clap_audio_embeddings_batch(
    audio_data_list: List[np.ndarray], # List of audio waveforms
    model: ClapModel,
    processor: AutoProcessor,
    device: str = get_device(),
    batch_size: int = 32,
    original_sampling_rate: int = DEFAULT_SAMPLING_RATE, 
    target_sampling_rate: int = CLAP_SAMPLING_RATE
) -> Optional[np.ndarray]:
    """
    Generates CLAP audio embeddings for a list of audio waveforms in batches.

    Args:
        audio_data_list (List[np.ndarray]): List of input audio waveforms.
        sampling_rate (int): The sampling rate of the audio_data.
        model (ClapModel): A pre-loaded CLAP model.
        processor (AutoProcessor): The corresponding CLAP processor.
        device (str): Torch device string.
        batch_size (int): Number of audio samples to process per batch.

    Returns:
        Optional[np.ndarray]: A 2D array of shape (len(audio_data_list), D),
        where D is the CLAP audio embedding dimension; or None on error or empty input.
    """
    if not audio_data_list:
        return None
    if model is None or processor is None:
        print("CLAP model or processor not provided.")
        return None
    
    all_embeddings_list = []
    model = model.to(device)
    model.eval()

    try:
        for i in range(0, len(audio_data_list), batch_size):
            batch_audio_data_raw = audio_data_list[i:i+batch_size]
            
            # Resample audio in the batch if necessary
            batch_audio_data_resampled = []
            for audio_data in batch_audio_data_raw:
                if original_sampling_rate != target_sampling_rate:
                    resampled_ad = resample_audio(
                        audio_data,
                        original_sampling_rate,
                        target_sampling_rate
                    )
                    batch_audio_data_resampled.append(resampled_ad)
                else:
                    batch_audio_data_resampled.append(audio_data)

            inputs = processor(
                audios=batch_audio_data_resampled,
                sampling_rate=target_sampling_rate,
                return_tensors="pt",
                padding=True 
            ).to(device)
            
            audio_features = model.get_audio_features(**inputs) # Use **inputs for multimodal models
            emb_batch = audio_features.cpu().numpy()
            all_embeddings_list.append(emb_batch)

        if not all_embeddings_list: 
            return None
        
        embeddings_np = np.vstack(all_embeddings_list)
        
        # Normalize each embedding vector in the batch
        norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
        norms[norms == 0] = 1.0 # Avoid division by zero
        return embeddings_np / norms
    
    except Exception as e:
        print(f"Error generating batch CLAP audio embeddings: {e}")
        return None

@torch.no_grad()
def generate_clap_text_embedding(
    text: str,
    model: ClapModel, 
    processor: AutoProcessor,
    device: str = get_device()
) -> np.ndarray:
    """
    Generates CLAP text embedding for a single text string.

    Args:
        text (str): The input text string.
        model (ClapModel): A pre-loaded CLAP model.
        processor (AutoProcessor): The corresponding CLAP processor.
        device (str): Torch device string.

    Returns:
        np.ndarray: A 1D array representing the normalized CLAP text embedding.
    """
    if model is None or processor is None:
        raise ValueError("CLAP model or processor not provided.")

    model = model.to(device)
    model.eval()

    inputs = processor(
        text=[text], # Processor expects a list of texts
        return_tensors="pt", 
        padding=True, 
        truncation=True
    ).to(device)

    text_features = model.get_text_features(**inputs)
    emb = text_features.cpu().numpy().flatten()
    
    # Normalize the embedding
    norm = np.linalg.norm(emb)
    if norm == 0:
        return emb
    return emb / norm

@torch.no_grad()
def generate_clap_text_embeddings_batch(
    texts: List[str],
    model: ClapModel,
    processor: AutoProcessor,
    device: str = get_device(),
    batch_size: int = 32
) -> Optional[np.ndarray]:
    """
    Generates CLAP text embeddings for a list of texts in batches.

    Args:
        texts (List[str]): The list of input text strings.
        model (ClapModel): A pre-loaded CLAP model.
        processor (AutoProcessor): The corresponding CLAP processor.
        device (str): Torch device string.
        batch_size (int): Number of texts to process per batch.

    Returns:
        Optional[np.ndarray]: A 2D array of shape (len(texts), D), 
        where D is the CLAP text embedding dimension; or None on error or empty input.
    """
    if not texts:
        return None
    if model is None or processor is None:
        print("CLAP model or processor not provided.")
        return None

    model = model.to(device)
    model.eval()
    all_embeddings_list: List[np.ndarray] = []

    try:
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            inputs = processor(
                text=batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True
            ).to(device)

            text_features = model.get_text_features(**inputs)
            emb_batch = text_features.cpu().numpy()
            all_embeddings_list.append(emb_batch)

        if not all_embeddings_list:
            return None

        embeddings_np = np.vstack(all_embeddings_list)

        # Normalize each embedding vector in the batch
        norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return embeddings_np / norms

    except Exception as e:
        print(f"Error generating CLAP text embeddings batch: {e}")
        return None
    
if __name__ == "__main__":
    # Testing sentence embedding generation 
    sent_model = load_sentence_transformer_model() 

    sent_emb1 = generate_sentence_embedding(
        text_input="This is a test sentence.",
        model=sent_model,
        normalize_embeddings=True
    )

    print(sent_emb1.shape)

    sent_embs = generate_sentence_embedding(
        text_input=["This is a test sentence 1.", "This is a test sentence 2."],
        model=sent_model,
        normalize_embeddings=True
    )

    print(sent_embs.shape)

    sent_embs = generate_sentence_embeddings_batch(
        texts=[f"This is a test sentence {i}." for i in range(1, 21)],
        model=sent_model, 
        batch_size=10
    )

    print(sent_embs.shape)

    # Testing CLIP model loading and embedding generation 
    clip_model, clip_processor = load_clip_model_and_processor(
        model_name=DEFAULT_CLIP_MODEL_NAME,
        device=get_device()
    )
    test_image = Image.open("sample_images/test-image-1.jpg")
    clip_image_emb = generate_clip_image_embedding(
        pil_image=test_image,
        model=clip_model,
        processor=clip_processor,
        device=get_device()
    )
    print(f"CLIP Image Embedding Shape: {clip_image_emb.shape}")
    clip_text_emb = generate_clip_text_embedding(
        text="This is a test text for CLIP.",
        model=clip_model,
        processor=clip_processor,
        device=get_device()
    )
    print(f"CLIP Text Embedding Shape: {clip_text_emb.shape}")

    clip_image_embs = generate_clip_image_embeddings_batch(
        pil_images=[test_image] * 10,  # Example batch of 10 identical images
        model=clip_model,
        processor=clip_processor,
        batch_size=5
    )
    print(f"CLIP Batch Image Embeddings Shape: {clip_image_embs.shape if clip_image_embs is not None else 'None'}")

    clip_text_embs = generate_clip_text_embeddings_batch(
        texts=[f"This is a test sentence {i}." for i in range(1, 21)],
        model=clip_model, 
        processor=clip_processor
    )

    print(f"CLIP Batch Text Embeddings Shape: {clip_text_embs.shape}")

    # Testing CLAP 
    clap_model, clap_processor = load_clap_model_and_processor(
        model_name=DEFAULT_CLAP_MODEL_NAME,
        device=get_device()
    )

    duration_seconds = 2
    
    # Generate a few sample audio waveforms
    audio_noise_1 = np.random.uniform(-0.5, 0.5, DEFAULT_SAMPLING_RATE * duration_seconds).astype(np.float32)
    audio_noise_2 = np.random.uniform(-0.4, 0.4, DEFAULT_SAMPLING_RATE * duration_seconds).astype(np.float32) # Slightly different noise
    audio_sine_wave = np.sin(np.linspace(0, 440 * 2 * np.pi * duration_seconds, DEFAULT_SAMPLING_RATE * duration_seconds)).astype(np.float32)

    sample_audios_batch = [audio_noise_1, audio_sine_wave, audio_noise_1[:DEFAULT_SAMPLING_RATE//2]] # Include a short one

    audio_noise_1_emb = generate_clap_audio_embedding(
        audio_noise_1, 
        model=clap_model, 
        processor=clap_processor, 
        original_sampling_rate=DEFAULT_SAMPLING_RATE
    )

    audio_noise_2_emb = generate_clap_audio_embedding(
        audio_noise_2, 
        model=clap_model, 
        processor=clap_processor, 
        original_sampling_rate=DEFAULT_SAMPLING_RATE
    )

    audio_sine_wave_emb = generate_clap_audio_embedding(
        audio_sine_wave, 
        model=clap_model, 
        processor=clap_processor, 
        original_sampling_rate=DEFAULT_SAMPLING_RATE
    )

    print(f"CLAP audio embeddings: {audio_noise_1_emb.shape, audio_noise_2_emb.shape, audio_sine_wave_emb.shape}")

    audio_embs = generate_clap_audio_embeddings_batch(
        sample_audios_batch, 
        model=clap_model, 
        processor=clap_processor, 
        original_sampling_rate=DEFAULT_SAMPLING_RATE
    )

    print(f"CLAP batch audio embeddings: {audio_embs.shape}")

    sim_noise1_noise2 = np.dot(audio_noise_1_emb, audio_noise_2_emb)
    sim_noise1_sine = np.dot(audio_noise_1_emb, audio_sine_wave_emb)
    sim_noise2_sine = np.dot(audio_noise_2_emb, audio_sine_wave_emb)

    print(f"  Similarity(Noise1, Noise2): {sim_noise1_noise2:.4f}")
    print(f"  Similarity(Noise1, SineWave): {sim_noise1_sine:.4f}")
    print(f"  Similarity(Noise2, SineWave): {sim_noise2_sine:.4f}")

    assert sim_noise1_noise2 > sim_noise1_sine, "Sim(N1,N2) should be > Sim(N1,Sine)"
    assert sim_noise1_noise2 > sim_noise2_sine, "Sim(N1,N2) should be > Sim(N2,Sine)"


