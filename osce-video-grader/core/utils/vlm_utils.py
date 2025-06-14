import os 
from functools import lru_cache
from typing import Union, Optional, List, Tuple 

import torch 
import numpy as np
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer

from core.utils.helpers import get_device

DEFAULT_MOONDREAM_MODEL_ID = "vikhyatk/moondream2"
DEFAULT_MOONDREAM_REVISION = "2025-04-14"  # Check Hugging Face Hub for latest stable revision
DEFAULT_OSCE_IMAGE_DESCRIPTION_PROMPT = """
Describe this frame from a medical OSCE video and provide a detailed description of the clinical scenario depicted.

Provide a concise, factual description of the key elements in the image: including the medical context, any visible medical equipment, 
the patient and clinician's actions, and any other relevant details that would help in understanding the clinical situation."""


@lru_cache(maxsize=2)
def load_moondream_model(
    model_id: str = DEFAULT_MOONDREAM_MODEL_ID,
    revision: str = DEFAULT_MOONDREAM_REVISION,
    device: str = get_device()
) -> Optional[Tuple[
    AutoModelForCausalLM, 
    AutoTokenizer]]:
    """
    Loads and caches a Moondream model and its tokenizer.

    Args:
        model_id (str): The Hugging Face model ID for Moondream.
        revision (str): The specific model revision (commit hash or tag).
        device_preference (Optional[str]): Preferred device. If None, auto-detects.

    Returns:
        Optional[Tuple[AutoModelForCausalLM, AutoTokenizer, str]]:
            Loaded model, tokenizer, and the device it was loaded onto, or None if error.
    """
    
    print(f"Attempting to load Moondream model: {model_id} (revision: {revision}) onto device: {device}...")
    try:
        dtype = torch.float16 if device != 'cpu' else torch.float32

        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            trust_remote_code=True, 
            revision=revision, 
            torch_dtype=dtype
        ).to(device)

        model.eval()

        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        print(f"✓ Moondream model '{model_id}' loaded successfully on {device}.")
        
        return model, tokenizer
    
    except Exception as e:
        print(f"✗ Error loading Moondream model '{model_id}': {e}")
        return None
    
    
def describe_keyframe_with_moondream_model(
    pil_image: Image.Image,
    model: AutoModelForCausalLM,
    prompt: str = DEFAULT_OSCE_IMAGE_DESCRIPTION_PROMPT,
) -> Optional[str]:
    """
    Generates a description for a PIL Image using pre-loaded Moondream model and tokenizer.

    Args:
        pil_image (Image.Image): The keyframe image.
        moondream_model (AutoModelForCausalLM): The pre-loaded Moondream model.
        moondream_tokenizer (AutoTokenizer): The pre-loaded Moondream tokenizer.
        device (str): The device the model is currently on.
        prompt (str): The prompt to guide description.
        max_new_tokens (int): Max new tokens for the description.

    Returns:
        Optional[str]: The generated description or None if error.
    """
    try:
        if model is None:
            print("Moondream model not loaded.")
            return None
        
        # Generate the answer
        answer = model.query(
            pil_image, 
            prompt,
        )["answer"]

        return answer
        
    except Exception as e:
        print(f"✗ Error generating Moondream description: {e}")
        import traceback
        traceback.print_exc()
        return None
    
if __name__ == "__main__":
    # Example usage
    test_image_path = os.path.join("data", "test-image-1.jpg")
    osce_image_path = os.path.join("data", "osce-image-1.jpeg")

    model, tokenizer = load_moondream_model()

    if model:
        example_image = Image.open(osce_image_path)

        description = describe_keyframe_with_moondream_model(
            example_image, 
            model, 
            prompt=DEFAULT_OSCE_IMAGE_DESCRIPTION_PROMPT
        )

        print("Generated Description:", description)

        # TODO: Batch processing example 
    else:
        print("Failed to load Moondream model or tokenizer.")