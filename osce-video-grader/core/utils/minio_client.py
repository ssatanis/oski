import os 
import io 
import uuid 
import json 
import traceback
from typing import Optional, Dict, Any, List, Tuple 
from datetime import datetime, timedelta 
from pathlib import Path 
from enum import Enum 

import numpy as np 
from PIL import Image 
import soundfile as sf 
from minio import Minio 
from minio.error import S3Error 
import urllib3 

from core.config.config import settings 
from core.utils.audio_processor import extract_audio
from core.utils.helpers import sanitize_filename_for_minio, cleanup_local_file

class MediaType(Enum):
    AUDIO = "audio"
    VIDEO_KEYFRAME = "video_keyframe"

class MinIOClient:
    """
    MinIO client for storing and retrieving files (audio segments and video keyframes).
    """

    def __init__(
        self, 
        endpoint: str = settings.minio.endpoint,
        access_key: str = settings.minio.access_key,
        secret_key: str = settings.minio.secret_key,
        secure: bool = False 
    ):
        """
        Initialize  MinIO client.

        Args:
            endpoint (str): MinIO server endpoint.
            access_key (str): Access key for MinIO.
            secret_key (str): Secret key for MinIO.
            secure (bool): Whether to use HTTPS.
        """
        # Disable SSL warnings for local development 
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # Bucket names for different media types
        self.audio_segments_bucket = settings.minio.audio_segments_bucket_name
        self.video_keyframes_bucket = settings.minio.video_keyframes_bucket_name
        self.original_videos_bucket = settings.minio.original_videos_bucket_name
        self.extracted_audios_bucket = settings.minio.extracted_audios_bucket_name 
        self.metadata_bucket = settings.minio.metadata_bucket_name
        
        # Initialize buckets
        self._setup_buckets()

    def _setup_buckets(self):
        """Create required buckets if they don't exist"""
        buckets = [
            self.audio_segments_bucket,
            self.video_keyframes_bucket,
            self.original_videos_bucket,
            self.extracted_audios_bucket,
            self.metadata_bucket
        ]
        
        for bucket_name in buckets:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    print(f"Created bucket: {bucket_name}")
                else:
                    print(f"Bucket already exists: {bucket_name}")
            except S3Error as e:
                print(f"Error creating bucket {bucket_name}: {e}")

    def check_connection(self) -> bool:
        """Checks if the connection to the MinIO server is alive."""
        try:
            self.client.list_buckets()
            return True
        
        except Exception as e:
            print(f"MinIO connection failed: {e}")
            return False
    
    def store_original_video(
        self,
        video_data_stream: io.BytesIO,
        video_data_length: int,
        # video_id: str, # No longer directly used for object_name, but good for logging/metadata
        original_filename: str # This will be sanitized for the object name
    ) -> Optional[str]:
        """
        Stores the original uploaded video file using a sanitized version of its original name.
        Args:
            video_data_stream: Stream of video data.
            video_data_length: Length of the video data.
            original_filename: The original filename of the video.
        Returns:
            MinIO object path (bucket/sanitized_object_name) or None on failure.
        """
        if not original_filename:
            print("Error: Original filename is required to store the video.")
            # Or generate a UUID-based name as a fallback:
            # original_filename = f"{uuid.uuid4()}.mp4" # Or try to infer extension
            return None

        sanitized_object_name = sanitize_filename_for_minio(original_filename)

        try:
            # Infer content type from sanitized name's extension
            _, extension = os.path.splitext(sanitized_object_name)
            content_type = f"video/{extension.lstrip('.').lower()}" if extension else "application/octet-stream"

            self.client.put_object(
                bucket_name=self.original_videos_bucket,
                object_name=sanitized_object_name, # Use sanitized name
                data=video_data_stream,
                length=video_data_length,
                content_type=content_type
            )
            minio_path = f"{self.original_videos_bucket}/{sanitized_object_name}"

            print(f"Stored original video as: {minio_path}")
            return minio_path
        
        except S3Error as e:
            print(f"MinIO S3Error storing original video as {sanitized_object_name}: {e}")
        
        except Exception as e:
            print(f"Unexpected error storing original video as {sanitized_object_name}: {e}")
        
        return None
    
    def store_extracted_audio(
        self,
        audio_data_stream: io.BytesIO,
        audio_data_length: int,
        video_id: str, # Still useful for naming the extracted audio consistently
        original_video_filename: str, # Can be used to derive a base name for the audio
        audio_format: str = "wav"
    ) -> Optional[str]:
        """
        Stores the full extracted audio track from a video.
        """
        if not original_video_filename:
            base_name_for_audio = video_id # Fallback to video_id if no original name
        else:
            base_name_for_audio, _ = os.path.splitext(sanitize_filename_for_minio(original_video_filename))

        object_name = f"{base_name_for_audio}.{audio_format.lower()}"
        content_type = f"audio/{audio_format.lower()}"

        try:
            self.client.put_object(
                bucket_name=self.extracted_audios_bucket,
                object_name=object_name,
                data=audio_data_stream,
                length=audio_data_length,
                content_type=content_type
            )
            minio_path = f"{self.extracted_audios_bucket}/{object_name}"
            print(f"Stored extracted full audio (from video_id: {video_id}): {minio_path}")
            return minio_path
        
        except S3Error as e:
            print(f"MinIO S3Error storing extracted audio for video {video_id}: {e}")

        except Exception as e:
            print(f"Unexpected error storing extracted audio for video {video_id}: {e}")

        return None

    def store_audio_segment(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int, 
        segment_id: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Store audio segment in MinIO
        
        Args:
            audio_data (np.ndarray): Audio data as numpy array
            sample_rate (int): Sample rate of audio
            segment_id (str): Unique identifier for the segment
            metadata (dict): Additional metadata to store
            
        Returns:
            MinIO object path
        """
        try:
            # Convert numpy array to WAV bytes
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
            audio_buffer.seek(0)
            
            # Generate object name
            object_name = f"{segment_id}.wav"
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.audio_segments_bucket,
                object_name=object_name,
                data=audio_buffer,
                length=audio_buffer.getbuffer().nbytes,
                content_type="audio/wav"
            )
            
            # Store metadata separately if provided
            if metadata:
                self._store_metadata(segment_id, metadata, MediaType.AUDIO)
            
            minio_path = f"{self.audio_segments_bucket}/{object_name}"
            print(f"Stored audio segment: {minio_path}")
            return minio_path
            
        except S3Error as e:
            print(f"MinIO S3Error storing audio segment {segment_id}: {e}")

        except Exception as e:
            print(f"Unexpected error storing audio segment {segment_id}: {e}")

        return None

    def store_video_keyframe(
        self, 
        image_data: bytes, 
        keyframe_id: str,
        image_format: str = "JPEG",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store video keyframe in MinIO
        
        Args:
            image_data (bytes): Image data as bytes
            keyframe_id (str): Unique identifier for the keyframe
            image_format (str): Image format (JPEG, PNG, etc.)
            metadata (dict): Additional metadata to store
            
        Returns:
            MinIO object path
        """
        try:
            # Generate object name
            extension = image_format.lower()
            object_name = f"{keyframe_id}.{extension}"
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.video_keyframes_bucket,
                object_name=object_name,
                data=io.BytesIO(image_data),
                length=len(image_data),
                content_type=f"image/{extension}"
            )
            
            # Store metadata separately if provided
            if metadata:
                self._store_metadata(keyframe_id, metadata, MediaType.VIDEO_KEYFRAME)
            
            minio_path = f"{self.video_keyframes_bucket}/{object_name}"
            print(f"Stored video keyframe: {minio_path}")
            return minio_path
            
        except S3Error as e:
            print(f"MinIO S3Error storing video keyframe {keyframe_id}: {e}")

        except Exception as e:
            print(f"Unexpected error storing video keyframe {keyframe_id}: {e}")

        return None

    def _store_metadata(
            self,
            item_id: str,
            metadata: Dict[str, Any],
            media_type: MediaType
        ):
        """Store metadata as JSON file"""
        try:
            metadata_json = json.dumps(metadata, indent=2, default=str)
            object_name = f"{media_type.value}/{item_id}_metadata.json"

            # Ensure all datetime objects are converted to ISO format strings
            def json_serializer(obj):
                if isinstance(obj, (datetime, Path)):
                    return obj.isoformat() if isinstance(obj, datetime) else str(obj)
                
                raise TypeError(f"Type {type(obj)} not serializable")
            
            metadata_json = json.dumps(
                metadata,
                indent=2,
                default=json_serializer
            ) # Use custom serializer
            metadata_bytes = metadata_json.encode('utf-8')
            
            self.client.put_object(
                bucket_name=self.metadata_bucket,
                object_name=object_name,
                data=io.BytesIO(metadata_bytes),
                length=len(metadata_bytes),
                content_type="application/json"
            )
        
        except TypeError as e:
            print(f"Metadata serialization error for {item_id} ({media_type.name}): {e}. Metadata: {metadata}")

        except S3Error as e:
            print(f"MinIO S3Error storing metadata for {item_id} ({media_type.name}): {e}")

        except Exception as e:
            print(f"Unexpected error storing metadata for {item_id} ({media_type.name}): {e}")

    def get_presigned_url(
            self,
            minio_path: str,
            expires_in_hours: int = 5*24 # 5 days
        ) -> Optional[str]:
        """
        Generate a presigned URL for an object.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object.
            expires_in_hours (int): URL expiration time in hours.

        Returns:
            Presigned URL string or None if an error occurs.
        """
        try:
            bucket_name, object_name = minio_path.split("/", 1)

            if not self.client.bucket_exists(bucket_name):
                print(f"Error: Bucket '{bucket_name}' does not exist.")
                return None
            
            # Check if object exists (optional, but good for presigned URLs)
            # self.client.stat_object(bucket_name, object_name) # This will raise S3Error if not found

            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_in_hours)
            )
            return url
        
        except S3Error as e:
            if e.code == "NoSuchKey":
                print(f"Error generating presigned URL: Object '{object_name}' not found in bucket '{bucket_name}'.")
            elif e.code == "NoSuchBucket": # Should be caught by bucket_exists, but good to have
                 print(f"Error generating presigned URL: Bucket '{bucket_name}' does not exist.")
            else:
                print(f"MinIO S3Error generating presigned URL for {bucket_name}/{object_name}: {e}")

        except Exception as e:
            print(f"Unexpected error generating presigned URL for {bucket_name}/{object_name}: {e}")

        return None

    def retrieve_object_data(
            self,
            bucket_name: str,
            object_name: str
        ) -> Optional[bytes]:
        """Generic helper to retrieve raw object data from MinIO."""
        response = None

        try:
            response = self.client.get_object(bucket_name, object_name)
            return response.read()
        except S3Error as e:
            if e.code != "NoSuchKey": # Don't spam console for expected misses
                print(f"S3Error retrieving {bucket_name}/{object_name}: {e}")
        finally:
            if response:
                response.close()
                response.release_conn()

        return None
    
    def retrieve_audio_segment(self, minio_path: str) -> Optional[Tuple[np.ndarray, int]]:
        """Retrieves audio segment from MinIO given a full path."""
        try:
            bucket_name, object_name = minio_path.split('/', 1)
            audio_bytes = self.retrieve_object_data(bucket_name, object_name)

            if audio_bytes:
                audio_buffer = io.BytesIO(audio_bytes)
                data, sample_rate = sf.read(audio_buffer)
                return data, sample_rate
        
            return None
        
        except (ValueError, S3Error, Exception) as e:
            print(f"Error retrieving audio segment from {minio_path}: {e}")
            return None
        
    def retrieve_video_keyframe(self, minio_path: str) -> Optional[Image.Image]:
        """Retrieves video keyframe from MinIO given a full path."""
        try:
            bucket_name, object_name = minio_path.split('/', 1)
            image_bytes = self.retrieve_object_data(bucket_name, object_name)

            if image_bytes:
                return Image.open(io.BytesIO(image_bytes))
            
            return None
        
        except (ValueError, S3Error, Exception) as e:
            print(f"Error retrieving video keyframe from {minio_path}: {e}")
            return None
        
    def retrieve_metadata(
            self,
            item_id: str,
            media_type: MediaType
        ) -> Optional[Dict[str, Any]]:
        """Retrieves and parses the metadata JSON file for a given item."""
        try:
            object_name = f"{media_type.value}/{item_id}_metadata.json"
            metadata_bytes = self.retrieve_object_data(self.metadata_bucket, object_name)

            if metadata_bytes:
                return json.loads(metadata_bytes.decode('utf-8'))
            
        except Exception as e:
            print(f"Error retrieving metadata for {item_id} ({media_type.name}): {e}")

        return None
    
    def list_objects(
            self,
            bucket_name: str,
            prefix: str = ""
        ) -> List[str]:
        """Lists objects in a bucket, optionally filtered by a prefix."""
        try:
            return [obj.object_name for obj in self.client.list_objects(bucket_name, prefix=prefix, recursive=True)]
        
        except (S3Error, Exception) as e:
            print(f"Error listing objects in {bucket_name}: {e}")
            return []
        
    def delete_object(self, minio_path: str) -> bool:
        """Deletes a single object from MinIO given its full path."""
        try:
            bucket_name, object_name = minio_path.split('/', 1)
            self.client.remove_object(bucket_name, object_name)
            return True
        
        except (ValueError, S3Error, Exception) as e:
            if isinstance(e, S3Error) and e.code == "NoSuchKey":
                return True
            
            print(f"Error deleting object {minio_path}: {e}")
            return False

        
    def delete_media_asset(self, item_id: str, media_type: MediaType, file_extension: str) -> bool:
        """
        Deletes a media asset and its associated metadata. 
        The metadata is also deleted to prevent orphaned metadata files.
        """
        success = True

        # Determine media object path
        if media_type == MediaType.AUDIO:
            media_path = f"{self.audio_segments_bucket}/{item_id}.{file_extension}"
        elif media_type == MediaType.VIDEO_KEYFRAME:
            media_path = f"{self.video_keyframes_bucket}/{item_id}.{file_extension}"
        else:
            return False
        
        # Delete media object
        if not self.delete_object(media_path):
            success = False
            
        # Delete metadata object
        metadata_object_name = f"{media_type.value}/{item_id}_metadata.json"
        metadata_path = f"{self.metadata_bucket}/{metadata_object_name}"
        if not self.delete_object(metadata_path):
            success = False
            
        if success:
            print(f"Successfully deleted asset and metadata for {item_id}")

        return success
        
    
# Test function 
def test_minio_client():
    """Test script for MinIO client functionality."""
    print("=== MinIO Client Test Suite ===\n")

    # Initialize MinIO client
    try:
        minio_client = MinIOClient()
        print("✓ MinIO client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize MinIO client: {e}")
        return

    # Test connection
    if not minio_client.check_connection():
        print("✗ MinIO connection test failed. Make sure MinIO server is running and accessible.")
        return
    print("✓ MinIO connection successful.")
    print("-" * 30)

    # --- Test 2: Store and retrieve video keyframe ---
    print("\n=== Test 2: Video Keyframe Storage & Retrieval ===")
    keyframe_id, keyframe_minio_path = None, None
    try:
        image = Image.new('RGB', (100, 80), color=(0, 128, 255))
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        image_data = img_buffer.getvalue()
        keyframe_id = f"test-video-{uuid.uuid4()}"
        metadata = {"width": 100, "height": 80, "format": "PNG", "created_at": datetime.now(), "test_data": True}
        
        keyframe_minio_path = minio_client.store_video_keyframe(image_data, keyframe_id, "PNG", metadata)
        assert keyframe_minio_path is not None, "Storing keyframe returned None"
        print(f"✓ Stored keyframe at: {keyframe_minio_path}")

        retrieved_image = minio_client.retrieve_video_keyframe(keyframe_minio_path)
        assert retrieved_image is not None, "Retrieving keyframe returned None"
        print(f"✓ Retrieved image: size={retrieved_image.size}, mode={retrieved_image.mode}")
        retrieved_image.save("test_retrieved_keyframe.png")
        print("  Saved retrieved image as test_retrieved_keyframe.png")

        retrieved_metadata = minio_client.retrieve_metadata(keyframe_id, MediaType.VIDEO_KEYFRAME)
        assert retrieved_metadata is not None, "Retrieving video metadata returned None"
        print(f"✓ Retrieved metadata keys: {list(retrieved_metadata.keys())}")
    except Exception as e:
        print(f"✗ Video test failed: {e}")
    print("-" * 30)

    # --- Test 1: Store and retrieve audio segment ---
    print("\n=== Test 1: Audio Segment Storage & Retrieval ===")
    audio_segment_id, audio_minio_path = None, None
    try:
        sample_rate = 22050
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio_segment_id = f"test-audio-{uuid.uuid4()}"
        metadata = {"duration": duration, "frequency": 440, "created_at": datetime.now(), "test_data": True}
        
        audio_minio_path = minio_client.store_audio_segment(audio_data, sample_rate, audio_segment_id, metadata)
        assert audio_minio_path is not None, "Storing audio returned None"
        print(f"✓ Stored audio segment at: {audio_minio_path}")

        retrieved_audio, retrieved_sr = minio_client.retrieve_audio_segment(audio_minio_path)
        assert retrieved_audio is not None, "Retrieving audio returned None"
        print(f"✓ Retrieved audio: shape={retrieved_audio.shape}, sr={retrieved_sr}")
        
        retrieved_metadata = minio_client.retrieve_metadata(audio_segment_id, MediaType.AUDIO)
        assert retrieved_metadata is not None, "Retrieving audio metadata returned None"
        print(f"✓ Retrieved metadata keys: {list(retrieved_metadata.keys())}")
    except Exception as e:
        print(f"✗ Audio test failed: {e}")
    print("-" * 30)

    # --- Test 3: List objects and Presigned URLs ---
    print("\n=== Test 3: Listing & URL Generation ===")
    try:
        audio_objects = minio_client.list_objects(minio_client.audio_segments_bucket, prefix="test-audio")
        print(f"✓ Found {len(audio_objects)} audio objects with 'test-audio' prefix.")
        if audio_objects:
            test_path = f"{minio_client.audio_segments_bucket}/{audio_objects[0]}"
            presigned_url = minio_client.get_presigned_url(test_path)
            assert presigned_url is not None, "Generating presigned URL returned None"
            print(f"✓ Generated presigned URL (preview): {presigned_url[:100]}...")
    except Exception as e:
        print(f"✗ List/URL test failed: {e}")
    print("-" * 30)

    # --- Test 4: Cleanup via Deletion ---
    print("\n=== Test 4: Asset Deletion (Cleanup) ===")
    try:
        if audio_segment_id:
            print(f"Attempting to delete audio asset: {audio_segment_id}")
            success = minio_client.delete_media_asset(audio_segment_id, MediaType.AUDIO, "wav")
            assert success, "Audio asset deletion failed"
            print("✓ Audio asset and metadata deleted.")
        if keyframe_id:
            print(f"Attempting to delete video asset: {keyframe_id}")
            success = minio_client.delete_media_asset(keyframe_id, MediaType.VIDEO_KEYFRAME, "png")
            assert success, "Video asset deletion failed"
            print("✓ Video asset and metadata deleted.")
    except Exception as e:
        print(f"✗ Cleanup test failed: {e}")
    print("-" * 30)

    # Video and audio storage 
    video_id = str(uuid.uuid4())
    VIDEO_FILE_PATH = os.path.join("sample_osce_videos", "testvideo.mp4")
    original_video_filename_for_minio = os.path.basename(VIDEO_FILE_PATH)

    try: 
        print("Testing original video file storage")
        with open(VIDEO_FILE_PATH, "rb") as f_vid:
            video_stream = io.BytesIO(f_vid.read())
            video_length = video_stream.getbuffer().nbytes 

        minio_stored_video_path = minio_client.store_original_video(
            video_data_stream=video_stream, 
            video_data_length=video_length, 
            original_filename=original_video_filename_for_minio 
        )

        if minio_stored_video_path: 
            print(f"SUCCESS: Original video stored at MinIO path: {minio_stored_video_path}")
            video_presigned_url = minio_client.get_presigned_url(minio_stored_video_path)

            if video_presigned_url:
                print(f"Presigned URL for original video: {video_presigned_url}")
            else:
                print(f"Error: Could not get presigned URL for stored video.")

        else:
            print(f"Error: Failed to store original video '{original_video_filename_for_minio}'")

        print("Testing extracted audio storage")

        extracted_audio_path = extract_audio(
            video_path=VIDEO_FILE_PATH, 
            use_ffmpeg=True 
        )

        if extracted_audio_path and os.path.exists(extracted_audio_path):
            print(f"Audio extracted locally to temporary file: {extracted_audio_path}")
            with open(extracted_audio_path, "rb") as f_audio:
                audio_stream = io.BytesIO(f_audio.read())
                audio_length = audio_stream.getbuffer().nbytes

            # Assuming .wav from the suffix in extract_audio's NamedTemporaryFile
            extracted_audio_format = "wav"

            minio_stored_audio_path = minio_client.store_extracted_audio(
                audio_data_stream=audio_stream,
                audio_data_length=audio_length,
                video_id=video_id,
                original_video_filename=original_video_filename_for_minio,
                audio_format=extracted_audio_format
            )

            if minio_stored_audio_path:
                print(f"SUCCESS: Extracted audio stored at MinIO path: {minio_stored_audio_path}")
                audio_presigned_url = minio_client.get_presigned_url(minio_stored_audio_path)

                if audio_presigned_url:
                    print(f"  Presigned URL for extracted audio: {audio_presigned_url}")
                else: 
                    print("  ERROR: Could not get presigned URL for stored audio.")
            else: print(f"ERROR: Failed to store extracted audio for video ID '{video_id}'.")

        else:
            print(f"ERROR: Audio extraction failed or temp audio file not found. Skipping audio storage test.")

    except Exception as e:
        print(f"\nAn error occurred during the test: {e}")
        traceback.print_exc()

    finally:
        if minio_stored_video_path:
            print(f"Attempting to delete from MinIO: {minio_stored_video_path}")

            if minio_client.delete_object(minio_stored_video_path):
                print(f"Successfully deleted {minio_stored_video_path} from MinIO.")

            else:
                print(f"Failed to delete {minio_stored_video_path} from MinIO.")


        if minio_stored_audio_path:
            print(f"Attempting to delete from MinIO: {minio_stored_audio_path}")

            if minio_client.delete_object(minio_stored_audio_path):
                print(f"Successfully deleted {minio_stored_audio_path} from MinIO.")

            else:
                print(f"Failed to delete {minio_stored_audio_path} from MinIO.")

        cleanup_local_file(extracted_audio_path)

    print("\n=== MinIO Test Suite Completed ===\n")
    print("Next steps:")
    print("1. Check MinIO console at http://localhost:9001 to verify test buckets and objects.")
    print("2. If any test objects remain, the cleanup step may have failed.")

if __name__ == "__main__":
    try:
        test_minio_client()

    except Exception as e:
        print(f"An unexpected error occurred during the test suite: {e}")