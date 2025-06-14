import re 
import os 
import json 
import uuid 
from typing import Type, Any, Dict, List, get_args, get_origin  

import cv2 
import torch 
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo 

def get_device() -> str:
    """Returns the device to be used for PyTorch operations.
    
    Returns:
        str: "cuda" if a CUDA-capable GPU is available, "mps" if using Apple Silicon, otherwise "cpu".
    """
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    return device 

def get_video_details(
    video_file_path: str 
):
    """Returns the FPS, total frames, and duration of a video."""
    cap = cv2.VideoCapture(video_file_path)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_file_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()

    if fps <= 0 or total_frames <= 0:
        raise RuntimeError("Unable to determine video length (FPS or frame count is invalid).")

    video_duration = total_frames / fps

    return (fps, int(total_frames), video_duration)

def extract_and_validate_json_from_llm_response(
    raw_text: str,
    model_cls: Type[BaseModel]
) -> Dict[str, Any]:
    """
    Finds the first {...} or [...] in `raw_text`, loads it, and validates against `model_cls`.
    Returns the validated model instance or raises a ValueError.
    """
    # Remove any preamble before the first JSON bracket
    m = re.search(r'([\[{].*[\]}])', raw_text, re.DOTALL)
    if not m:
        raise ValueError("No JSON object or array found in response.")
    json_str = m.group(1).strip()

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e.msg}") from e

    # Validate with Pydantic v2
    try:
        validated =  model_cls.model_validate(data)
        return validated.model_dump()
    except ValidationError as e:
        raise ValueError(f"JSON did not conform to schema: {e}") from e


def pydantic_schema_to_json_string(
    model_cls: Type[BaseModel],
    indent: int = 2
) -> str:
    """
    Generates a “template” JSON string describing the shape of `model_cls`,
    including field descriptions.
    """
    def resolve_field(fld: FieldInfo, level: int, name: str) -> str:
        ann = fld.annotation
        origin = get_origin(ann)
        args = get_args(ann)

        # Case A: List of nested BaseModel
        if origin in (list, List) and len(args) == 1 and isinstance(args[0], type) and issubclass(args[0], BaseModel):
            # recurse into the element model
            nested = walk(args[0], level + 2)
            return (
                f'{" " * level}"{name}": [\n'
                f'{nested}\n'
                f'{" " * level}],  # {fld.description or ""}'
            )

        # Case B: Nested BaseModel directly
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            nested = walk(ann, level + 2)
            return f'{" " * level}"{name}": {nested},  # {fld.description or ""}'

        # Fallback: scalar or unknown container
        # get a short name for the type
        type_name = getattr(ann, "__name__", str(ann))
        return f'{" " * level}"{name}": <{type_name}>,  # {fld.description or ""}'

    def walk(cls: Type[BaseModel], level: int) -> str:
        lines = [f'{" " * (level - 2)}{{']
        for fname, fld in cls.model_fields.items():
            lines.append(resolve_field(fld, level, fname))
        lines.append(f'{" " * (level - 2)}}}')
        return "\n".join(lines)

    return walk(model_cls, indent)

def sanitize_filename_for_minio(filename: str) -> str:
    """
    Sanitizes a filename to be safe for MinIO object names.
    - Replaces spaces with underscores.
    - Removes characters not in a safe set (alphanumeric, '.', '-', '_').
    - Ensures it's not empty and doesn't start/end with problematic chars (less critical for MinIO but good practice).
    """
    if not filename:
        return f"unnamed_file_{uuid.uuid4()}"

    # Split filename and extension
    base, ext = os.path.splitext(filename)

    # Replace spaces with underscores
    base = base.replace(" ", "_")

    # Keep only safe characters for the base name
    # Allow alphanumeric, underscore, hyphen. Dots are usually only for extension.
    safe_chars = r"[^a-zA-Z0-9_-]"
    base = re.sub(safe_chars, "", base)

    # Ensure base is not empty after sanitization
    if not base:
        base = f"file_{uuid.uuid4()}" # Fallback if base becomes empty

    # Extension sanitization (less critical, usually simple like .mp4, .jpeg)
    # Keep alphanumeric, remove leading dots if multiple, then add one back.
    ext = ext.lstrip('.')
    safe_ext_chars = r"[^a-zA-Z0-9]"
    ext = re.sub(safe_ext_chars, "", ext)
    if ext:
        ext = "." + ext
    else: # If no valid extension found, maybe default or leave empty
        ext = ".dat" # Or handle as error, or try to infer from content type

    return base + ext

def cleanup_local_file(filepath: str):
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Cleaned up local file: {filepath}")
        except Exception as e:
            print(f"Error cleaning up local file {filepath}: {e}")

if __name__ == "__main__":
    # device = get_device()
    # print(f"Using device: {device}")
    # # Example usage
    # tensor = torch.tensor([1.0, 2.0, 3.0]).to(device)
    # print(f"Tensor on {device}: {tensor}")

    print(sanitize_filename_for_minio("testvideo.mp4"))
    print(sanitize_filename_for_minio("osce_keyframe_audio.mp3"))
    print(sanitize_filename_for_minio("test.mp3"))
    print(sanitize_filename_for_minio("-test*.jpeg"))

    pass 