import io 
import os 
import re 
import json 
import time 
import logging 
import random 
from typing import Optional, List, Dict, Literal, Type, Union, Any, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np 
from PIL import Image 
from google import genai 
from google.genai import types
from pydantic import BaseModel
from tenacity import (
    retry, 
    stop_after_attempt,
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from ratelimit import limits, sleep_and_retry

from core.config.config import settings 
from core.utils.helpers import extract_and_validate_json_from_llm_response, pydantic_schema_to_json_string
from core.prompts.gemini import (
    OSCE_KEYFRAME_CAPTIONER_PROMPT
)
from core.tools.schemas import KeyframeDescriptionOutput

logger = logging.getLogger(__name__)    
logging.basicConfig(level=logging.INFO)

for lib in ("google_genai.models", "httpx", "urllib3"):
    logging.getLogger(lib).setLevel(logging.ERROR)


DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.0-flash-exp"
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.0-flash"

# Exceptions 
class GeminiRateLimit(Exception):
    """Raised when Gemini returns a 429 with retryInfo."""


def load_gemini_client(
    api_key: str = settings.gemini.api_key
) -> Optional[genai.Client]:
    """Loads and returns the Gemini client."""
    if not api_key:
        print(f"Error: Gemini API key is required.")
        return None

    try:
        client = genai.Client(api_key=api_key)
        return client
    
    except Exception as e:
        print("Error initializing Gemini client or model: {e}")
        return None
    
def generate_text_content_with_gemini(
    client: genai.Client, 
    prompt_text: str, 
    model_id: str = DEFAULT_GEMINI_TEXT_MODEL, 
    max_output_tokens: Optional[int] = None,
    temperature: float = 0,
    top_p: float = 1.0,
    top_k: float = 35
):
    """Generate content from Gemini using a text-only prompt."""
    if not client:
         print("Gemini client is required.")
         return None
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=[
                prompt_text
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
        )

        return response.text

    except Exception as e:
        print(f"An error occurred while generating response: {e}")
        
        return None 


def generate_text_content_gemini_with_retry(
    client: genai.Client, 
    prompt_text: str, 
    model_id: str = DEFAULT_GEMINI_TEXT_MODEL, 
    max_output_tokens: Optional[int] = None,
    temperature: float = 0,
    top_p: float = 1.0,
    top_k: float = 35,
    max_retries: int = 10,
    min_delay: float = 25.0, 
    max_delay: float = 30.0,
):
    """Generate content from Gemini using a text-only prompt (with a retry mechanism)."""
    try:    
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )

    except Exception as e:
        print(f"An error occurred while generating response: {e}")
        
        return None 
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    prompt_text
                ],
                config=generation_config
            )

            return response.text 
        
        except Exception as e:
            try:
                if attempt + 1 == max_retries: 
                    print(f"Max retries reached. Failing permanently.")
                    break 

                delay = random.uniform(min_delay, max_delay)

                print(f"Waiting for {delay:.2f} seconds before retrying...")
                time.sleep(delay)
            
            except Exception as e:
                print(f"A non-retryable error occurred. Stopping immediately. Error: {e}")
                return None 
            
    return None
    
def generate_image_content_with_gemini(
    client: genai.Client,
    pil_image: Image.Image,
    prompt_text: str,
    model_id: str = DEFAULT_GEMINI_IMAGE_MODEL,
    max_output_tokens: Optional[int] = None,
    temperature: float = 0,
    top_p: float = 1.0,
    top_k: float = 35
):
    """Generate content from Gemini using an image and text prompt."""
    if not client:
         print("Gemini client is required.")
         return None
    
    try:
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format="JPEG")
        image_bytes = img_byte_arr.getvalue()

        response = client.models.generate_content(
            model=model_id,
            contents=[
                prompt_text,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                )
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
        )

        return response.text

    except Exception as e:
        print(f"An error occurred while generating response: {e}")
        
        return None 
    
def generate_image_content_gemini_with_retry(
    client: genai.Client, 
    pil_image: Image.Image, 
    prompt_text: str, 
    model_id: str = DEFAULT_GEMINI_IMAGE_MODEL,
    max_retries: int = 10, 
    min_delay: float = 25.0, 
    max_delay: float = 30.0,
    max_output_tokens: Optional[int] = None,
    temperature: float = 0,
    top_p: float = 1.0,
    top_k: float = 35
):
    """Generate content from Gemini using an image and text prompt, with a self-contained exponential backoff retry mechanism."""
    try:
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format="JPEG")
        image_bytes = img_byte_arr.getvalue()

        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )

    except Exception as e:
        print(f"An error occurred while generating response: {e}")
        
        return None 
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    prompt_text,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                ],
                config=generation_config 
            )

            return response.text 
        
        except Exception as e:
            try:
                if attempt + 1 == max_retries: 
                    print(f"Max retries reached. Failing permanently.")
                    break 

                delay = random.uniform(min_delay, max_delay)

                print(f"Waiting for {delay:.2f} seconds before retrying...")
                time.sleep(delay)
            
            except Exception as e:
                print(f"A non-retryable error occurred. Stopping immediately. Error: {e}")
                return None 
            
    return None

def generate_image_description_using_gemini(
    client: genai.Client, 
    pil_image: Image.Image,
    output_schema: BaseModel,
    prompt: str = OSCE_KEYFRAME_CAPTIONER_PROMPT,
    response_format: Literal["raw", "json"] = "json"
):
    json_format_str = pydantic_schema_to_json_string(output_schema)
    json_format_str = json_format_str.replace("{", "{{").replace("}", "}}")

    prompt = prompt.format(
        json_format_str=json_format_str
    )

    try:
        raw_response = generate_image_content_with_gemini(
            client=client, 
            pil_image=pil_image, 
            prompt_text=prompt 
        )

        if response_format == "json":
            json_response = extract_and_validate_json_from_llm_response(
                raw_response, 
                output_schema
            )
            return json_response 
        else:
            return raw_response 
    
    except Exception as e:
        print(f"An unknown error occurred: {e}.")
        return None 

class GeminiImageBatchProcessor:
    def __init__(
        self,
        client: genai.Client,
        prompt_template: str,
        output_schema: Type[BaseModel],
        rate_limit_calls: int = 10,
        rate_limit_period: int = 60,
        max_retries: int = 5,
        max_backoff: int = 120,
        max_workers: int = 4,
    ):
        """
        A robust, concurrent batch-processor for generating descriptions of images via Gemini API.

        Args:
          - client (genai.Client): Google Gemini API Client.
          - prompt_template (str): Prompt for generating the image description.
          - output_schema (BaseModel): Pydantic schema class to validate the structured JSON output.
          - rate_limit_calls (int): Max calls per rate_limit_period (default 10)
          - rate_limit_period (int): Seconds in which rate_limit_calls applies (default 60)
          - max_retries (int): Retry attempts on failure (default 5)
          - max_backoff (int): Maximum backoff time in seconds (default 120)
          - max_workers (int): Size of the thread pool for concurrent image processing (default 4).
        """
        self.client = client
        self.prompt_template = prompt_template
        self.output_schema = output_schema
        self.max_workers = max_workers

        raw_schema = pydantic_schema_to_json_string(output_schema)
        escaped = raw_schema.replace("{", "{{").replace("}", "}}")
        self.prompt = prompt_template.format(json_format_str=escaped)

        # rate‐limit decorator parameters
        self._rate_limit_calls = rate_limit_calls
        self._rate_limit_period = rate_limit_period

        # retry decorator parameters
        self._max_retries = max_retries
        self._max_backoff = max_backoff

        # bind decorated methods
        self._throttled_call = self._make_throttled(self._make_retry(self._call_once))
        self._process_image = self._make_process(self._throttled_call)

    def _parse_retry_delay(self, payload: dict) -> float:
        """Extract '42s' → 42.0 from RetryInfo in error payload."""
        for d in payload.get("details", []):
            if d.get("@type", "").endswith("RetryInfo"):
                delay = d.get("retryDelay", "")
                if delay.endswith("s"):
                    try:
                        return float(delay[:-1])
                    except ValueError:
                        pass
        return None

    def _make_retry(self, fn):
        """Wrap `fn(client, img, prompt)` with tenacity retry logic."""
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, max=self._max_backoff),
            retry=retry_if_exception_type((GeminiRateLimit, Exception)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def wrapped(img: Image.Image) -> str:
            raw = fn(img)

            if raw is None:
                raise Exception("Empty response from Gemini")
            
            # if the wrapper surfaces a 429 as an Exception with `.payload` dict:
            if isinstance(raw, Exception) and hasattr(raw, "payload"):
                err = raw.payload.get("error", {})
                if err.get("code") == 429:
                    rd = self._parse_retry_delay(err)
                    if rd:
                        logger.warning("429 → sleeping %ss", rd)
                        time.sleep(rd)
                    raise GeminiRateLimit("Gemini rate-limit hit")
            return raw
        return wrapped

    def _make_throttled(self, fn):
        """Wrap `fn(img)` to rate-limit calls per config."""
        @sleep_and_retry
        @limits(
            calls=self._rate_limit_calls,
            period=self._rate_limit_period
        )
        def wrapped(img: Image.Image) -> str:
            return fn(img)
        return wrapped

    def _call_once(self, img: Image.Image) -> str:
        """Single Gemini API call."""
        return generate_image_content_with_gemini(
            client=self.client,
            pil_image=img,
            prompt_text=self.prompt,
        )

    def _make_process(self, fn):
        """Wrap `fn(img)` to optionally validate JSON."""
        def wrapped(img: Image.Image, response_format: str = "json") -> Union[str, Dict[str, Any]]:
            raw = fn(img)

            if response_format == "raw":
                return raw
            
            return extract_and_validate_json_from_llm_response(
                raw, 
                self.output_schema
            )
        
        return wrapped

    def process_batch(
        self,
        pil_images: Sequence[Image.Image],
        response_format: str = "json",
    ) -> List[Union[str, Dict[str, Any]]]:
        """
        Process a list of images in parallel, preserving order.
        Returns either raw strings or validated dicts.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(
                lambda img: self._process_image(img, response_format),
                pil_images
            ))

if __name__ == "__main__":
    gemini_client = load_gemini_client()
    
    # sample_image_path = os.path.join("sample_images/osce", "osce-image-5.jpeg")
    # sample_pil_image = Image.open(sample_image_path)
    
    # keyframe_description_response = generate_image_description_using_gemini(
    #     client=gemini_client,
    #     pil_image=sample_pil_image,
    #     prompt=OSCE_KEYFRAME_DESCRIPTION_PROMPT,
    #     output_schema=KeyframeDescriptionOutput
    # )

    # print(keyframe_description_response)

    # pose_grounding_output_response = generate_image_description_using_gemini(
    #     client=gemini_client,
    #     pil_image=sample_pil_image,
    #     prompt=OSCE_KEYFRAME_POSE_EXTRACTION_PROMPT,
    #     output_schema=PoseGroundingOutput
    # )

    # print(pose_grounding_output_response)

    # object_detection_grounding_output_response = generate_image_description_using_gemini(
    #     client=gemini_client,
    #     pil_image=sample_pil_image,
    #     prompt=OSCE_KEYFRAME_OBJECT_DETECTION_PROMPT,
    #     output_schema=ObjectDetectionOutput
    # )

    # print(object_detection_grounding_output_response)

    # scene_interaction_grounding_output_response = generate_image_description_using_gemini(
    #     client=gemini_client,
    #     pil_image=sample_pil_image,
    #     prompt=OSCE_KEYFRAME_SCENE_INTERACTION_GRAPH_GROUNDING_PROMPT,
    #     output_schema=SceneInteractionGraphOutput
    # )

    # print(scene_interaction_grounding_output_response)

    # Batched generation example 
    imgs = [Image.open(os.path.join("sample_images/osce", f"osce-image-{(i % 10) + 1}.jpeg")) for i in range(0, 20)]

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

    results = gemini_image_processor.process_batch(
        imgs, 
        response_format="json"
    )

    for idx, result in enumerate(results, 1):
        print(f"Image {idx} -> {result}")





    

