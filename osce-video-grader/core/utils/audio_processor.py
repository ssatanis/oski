import os 
import tempfile 
import time
import subprocess 
from pathlib import Path 
from pprint import pprint 
from typing import List, Dict, Optional, TypedDict 

import torch 
import librosa 
import numpy as np 
import pandas as pd 
from moviepy import VideoFileClip
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline 
from transformers import pipeline as hf_pipeline

from core.utils.helpers import get_device
from core.config.config import settings

class ProcessedAudioSegment(TypedDict):
    id: int
    start: float
    end: float
    transcript: str
    audio: np.ndarray
    emotion: str
    emotion_confidence_score: float 

DEFAULT_SAMPLING_RATE = 16000

def load_whisper_model(
        model_id: str = "small",
        device: str = "cpu" # No support for MPS
    ):
    if device == "cpu":
        compute_type = "int8"
    else:
        compute_type = "float16"

    model = WhisperModel(model_id, device=device, compute_type=compute_type)

    return model 

def load_diarization_model(
    device: str = get_device(), # No support for MPS
    hf_access_token: str = settings.hf.access_token
):
    return Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", 
        use_auth_token=hf_access_token
    ).to(torch.device(device))

def load_audio_emotion_classification_model(
    device: str = get_device()
):
    return hf_pipeline(
        "audio-classification",
        model="superb/wav2vec2-base-superb-er",
        device=0 if device != "cpu" else -1
    )

def extract_audio(
        video_path: str,
        sampling_rate: int = DEFAULT_SAMPLING_RATE,
        use_ffmpeg: bool = True,
        use_tempfile: bool = True
    ) -> Optional[str]: 
    """
    Extract audio from a video.
    Returns the path to the extracted audio file, or None on failure.
    If use_tempfile is True, the caller is responsible for deleting the temporary file.
    """
    print(f"Extracting audio from '{video_path}'...")
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found at {video_path}")
        return None

    video_file_path_obj = Path(video_path)
    video_path_str = str(video_file_path_obj) 

    if use_tempfile:
        try:
            temp_audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            final_audio_path = temp_audio_file.name
            temp_audio_file.close() 
        except Exception as e:
            print(f"ERROR: Could not create temporary file: {e}")
            return None
    else:
        base_filename = video_file_path_obj.stem
        # Save next to the original video if not using tempfile
        final_audio_path = str(video_file_path_obj.parent / f"{base_filename}.wav")

    extraction_successful = False
    if use_ffmpeg:
        command = [
            "ffmpeg",
            "-i", video_path_str,
            "-vn",
            "-ar", str(sampling_rate),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-loglevel", "error",
            "-y",
            final_audio_path,
        ]
        try:
            # Use Popen for better control over stdout/stderr if needed for debugging
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=60)

            if process.returncode == 0:
                extraction_successful = True
            else:
                print("ERROR: ffmpeg command failed.")
                print(f"  Return code: {process.returncode}")
                # Decode stderr, handling potential encoding issues
                ffmpeg_errors = stderr.decode('utf-8', errors='ignore').strip()
                if ffmpeg_errors:
                    print(f"  FFmpeg STDERR: {ffmpeg_errors}")

        except FileNotFoundError:
            print("ERROR: ffmpeg is not installed or not in your PATH.")

        except subprocess.TimeoutExpired:
            print(f"ERROR: ffmpeg command timed out for {video_path_str}.")

            if process: 
                process.kill() # Ensure process is killed

        except Exception as e: # Catch other potential Popen errors
            print(f"ERROR: Unexpected error during ffmpeg execution: {e}")

    else: # Use moviepy
        try:
            with VideoFileClip(video_path_str) as video_clip:
                if video_clip.audio is None:
                    print(f"ERROR: Video file {video_path_str} has no audio track (MoviePy).")
                else:
                    video_clip.audio.write_audiofile(
                        final_audio_path,
                        codec='pcm_s16le',
                        fps=sampling_rate,
                        logger=None 
                    )
                    extraction_successful = True
        except Exception as e:
            print(f"ERROR: MoviePy failed to extract audio from {video_path_str}: {e}")

    if extraction_successful and os.path.exists(final_audio_path) and os.path.getsize(final_audio_path) > 0:
        print(f"Audio extracted to '{final_audio_path}'.")
        return final_audio_path
    else:
        if extraction_successful: # Means file should exist but is empty or gone
             print(f"ERROR: Audio extraction reported success, but file '{final_audio_path}' is missing or empty.")
        else: # Extraction itself failed
            print(f"ERROR: Audio extraction failed. Output file '{final_audio_path}' may not be valid.")

        # If tempfile was used and extraction failed, attempt to clean up the (possibly empty) temp file.
        if use_tempfile and os.path.exists(final_audio_path):
            try:
                os.unlink(final_audio_path)
                print(f"  Cleaned up failed/empty temp audio file: {final_audio_path}")
            except Exception as e_del:
                print(f"  Could not delete failed/empty temp audio file {final_audio_path}: {e_del}")
        return None

def transcribe_and_diarize(
        audio_path: str,
        whisper_model, 
        diarization_model
    ) -> List[Dict]:
    """
    Manually performs transcription and diarization, then merges the results
    by aligning speakers to individual words. This is the core function.
    """
    print("\n--- Starting Transcription and Diarization ---")
    
    # Step 1: Transcribe with faster-whisper to get word-level timestamps
    print("Step 1: Transcribing with faster-whisper...")
    segments, _ = whisper_model.transcribe(
        audio_path, 
        language="en",
        word_timestamps=True
    )
    
    # Collect all words from all segments into a single list
    all_words = []
    for segment in segments:
        for word in segment.words:
            all_words.append({'start': word.start, 'end': word.end, 'text': word.word})
    print(f"  Transcription complete. Found {len(all_words)} words.")

    # Step 2: Diarize with pyannote.audio to get speaker turns
    print("Step 2: Diarizing with pyannote.audio...")
    diarization = diarization_model(
        audio_path,
        min_speakers=2,
        max_speakers=2
    )
    
    # Create a pandas DataFrame for easy and fast lookup of speaker turns
    speaker_turns = [{
        'start': turn.start,
        'end': turn.end,
        'speaker': speaker
    } for turn, _, speaker in diarization.itertracks(yield_label=True)]
    speaker_df = pd.DataFrame(speaker_turns)
    print(f"  Diarization complete. Found {len(speaker_df)} speaker turns.")

    # Step 3: Manually align words to speakers
    print("Step 3: Manually aligning words to speakers...")
    # For each word, we find which speaker was active during its timestamp.
    # We check the word's midpoint to see which speaker's turn it falls into.
    word_speakers = []
    for word in all_words:
        word_midpoint = word['start'] + (word['end'] - word['start']) / 2
        # Find the speaker turn that contains the word's midpoint
        speaker = speaker_df[(speaker_df['start'] <= word_midpoint) & (speaker_df['end'] >= word_midpoint)]
        
        # Assign the speaker label, defaulting to UNKNOWN if no speaker is found
        assigned_speaker = speaker.iloc[0]['speaker'] if not speaker.empty else "UNKNOWN"
        word_speakers.append(assigned_speaker)

    # Add the determined speaker label to each word dictionary
    for i, word in enumerate(all_words):
        word['speaker'] = word_speakers[i]
        word['text'] += " " # Add space for later joining

    # Step 4: Group consecutive words from the same speaker back into segments
    print("Step 4: Grouping words back into diarized segments...")
    final_segments = []
    if all_words:
        # Start the first segment with the first word
        current_segment = {'start': all_words[0]['start'], 'text': all_words[0]['text'], 'speaker': all_words[0]['speaker']}
        
        for i in range(1, len(all_words)):
            word = all_words[i]
            # If the speaker is the same, append the word's text
            if word['speaker'] == current_segment['speaker']:
                current_segment['text'] += word['text']
            # If the speaker changes, finalize the current segment and start a new one
            else:
                current_segment['end'] = all_words[i-1]['end']
                final_segments.append(current_segment)
                current_segment = {'start': word['start'], 'text': word['text'], 'speaker': word['speaker']}
        
        # Add the very last segment
        current_segment['end'] = all_words[-1]['end']
        final_segments.append(current_segment)
    
    print("  Alignment and segment grouping complete.")
    return final_segments

def group_into_conversational_chunks(
        diarized_segments: List[Dict],
        silence_threshold: float = 1.0
    ) -> List[List[Dict]]:
    """Groups segments into conversational chunks."""
    if not diarized_segments: 
        return []
    
    conversations = []
    current_conversation = [diarized_segments[0]]

    for i in range(1, len(diarized_segments)):
        if (diarized_segments[i]['start'] - diarized_segments[i-1]['end']) > silence_threshold:
            conversations.append(current_conversation)
            current_conversation = [diarized_segments[i]]

        else:
            current_conversation.append(diarized_segments[i])

    conversations.append(current_conversation)
    return conversations

def analyze_audio_segments_emotions(
    diarized_segments: List[Dict], 
    full_audio_waveform: np.ndarray, 
    audio_emotion_classification_model, 
    sampling_rate: int = DEFAULT_SAMPLING_RATE
) -> List[Dict]:
    """Analyzes emotion for each diarized segment."""
    print("\nAnalyzing emotion for each individual speaker turn...")
    segments_with_emotions = []
    for seg in diarized_segments:
        start_time, end_time = seg.get('start', 0.0), seg.get('end', 0.0)
        start_sample = int(start_time * sampling_rate)
        end_sample = int(end_time * sampling_rate)
        
        current_emotion_data = {"label": "unknown", "score": 0.0}

        # Ensure audio chunk is valid and has some duration for emotion analysis
        if end_sample > start_sample and (end_sample - start_sample) > 400:
            segment_audio = full_audio_waveform[start_sample:end_sample]
            emotion_result_list = audio_emotion_classification_model(
                segment_audio, 
                sampling_rate=sampling_rate
            )
            
            if emotion_result_list:
                current_emotion_data = emotion_result_list[0] 

        else:
            current_emotion_data = {
                "label": "too_short",
                "score": 0.0
            }

        segments_with_emotions.append({
            **seg,
            "emotion_label": current_emotion_data.get("label"),
            "emotion_score": current_emotion_data.get("score")
        })
        
    print(f"  Analyzed emotions for {len(segments_with_emotions)} speaker turns.")
    return segments_with_emotions

def infer_chunk_emotion(chunk_segments):
    """Infer emotion from the chunk segments."""
    chunk_emotion_label = "neu" # Default to neutral
    chunk_emotion_confidence = 0.5 # Default confidence for Neutral

    # Priority: Angry ('ang') > Happy ('hap') > Sad ('sad') from student turns
    # Define the exact labels from the model and their desired priority (lower number = higher priority)
    emotion_priority_map = {"ang": 0, "hap": 1, "sad": 2} 
    current_highest_priority = float('inf') # Initialize with a very low priority

    for turn in chunk_segments:
        if turn.get('speaker_role') == 'STUDENT':
            student_turn_emotion = turn.get('emotion_label') # This will be 'hap', 'ang', 'neu', or 'sad'
            student_turn_confidence = turn.get('emotion_score', 0.0)

            if student_turn_emotion in emotion_priority_map:
                # If this emotion has higher priority (lower number) than what we've found so far
                if emotion_priority_map[student_turn_emotion] < current_highest_priority:
                    chunk_emotion_label = student_turn_emotion
                    chunk_emotion_confidence = student_turn_confidence
                    current_highest_priority = emotion_priority_map[student_turn_emotion]
    
    # If no priority emotions were found from student turns, it remains "neu" (or whatever default).
    # If a student turn was 'neu' and no priority emotions were found, we can be more confident in 'neu'.
    if current_highest_priority == float('inf'): # No 'ang', 'hap', or 'sad' student emotion was found
        for turn in chunk_segments:
            if turn.get('speaker_role') == 'STUDENT' and turn.get('emotion_label') == 'neu':
                chunk_emotion_label = "neu" # Confirm neutral if a student was neutral
                chunk_emotion_confidence = turn.get('emotion_score', 0.5) # Use its confidence
                break # Take the first neutral student turn's confidence

    chunk_emotions_labels_map = {
        "ang": "ANGRY",
        "hap": "HAPPY",
        "neu": "NEUTRAL", 
        "sad": "SAD"
    }

    return chunk_emotions_labels_map[chunk_emotion_label], chunk_emotion_confidence

def assign_speaker_roles(diarized_segments: List[Dict]) -> Dict[str, str]:
    """Assigns STUDENT and PATIENT roles based on word count."""
    speaker_word_count = {}

    for seg in diarized_segments:
        speaker = seg.get('speaker', 'UNKNOWN')
        if speaker != 'UNKNOWN':
            count = len(seg['text'].split())
            speaker_word_count[speaker] = speaker_word_count.get(speaker, 0) + count

    if not speaker_word_count:
        return {}

    # Sort speakers by who spoke the most
    sorted_speakers = sorted(speaker_word_count.items(), key=lambda x: x[1], reverse=True)

    # Create the final mapping dictionary
    speaker_map = {speaker[0]: "UNKNOWN" for speaker in sorted_speakers}
    if len(sorted_speakers) > 0:
        speaker_map[sorted_speakers[0][0]] = "STUDENT"
    if len(sorted_speakers) > 1:
        speaker_map[sorted_speakers[1][0]] = "PATIENT"

    return speaker_map

def process_audio_segments(
    audio_path: str, 
    whisper_model: WhisperModel, 
    diarization_model, 
    audio_emotion_classification_model,
    sampling_rate: int = DEFAULT_SAMPLING_RATE,
    silence_threshold: int = 1
):
    """Process audio chunks"""
    # Transcribe and diarize 
    diarized_segments = transcribe_and_diarize(
        audio_path, 
        whisper_model=whisper_model, 
        diarization_model=diarization_model
    )

    full_audio_waveform, _ = librosa.load(
        audio_path, 
        mono=True, 
        sr=sampling_rate
    )

    # Analyze emotions for each diarized segment 
    segments_with_emotions = analyze_audio_segments_emotions(
        diarized_segments, 
        full_audio_waveform, 
        audio_emotion_classification_model
    )

    # Assign speaker roles to each diarized segment
    speaker_map = assign_speaker_roles(diarized_segments)

    for seg in segments_with_emotions:
        seg["speaker_role"] = speaker_map.get(seg["speaker"], "UNKNOWN")

    # Group into conversational chunks 
    conversational_chunks = group_into_conversational_chunks(segments_with_emotions, silence_threshold=silence_threshold)

    processed_segments = []

    for i, chunk_segments in enumerate(conversational_chunks):
        start_time = chunk_segments[0]['start']
        end_time = chunk_segments[-1]['end']

        full_transcript = "\n".join([f"{speaker_map.get(seg['speaker'], 'UNKNOWN')}: {seg['text'].strip()}" for seg in chunk_segments])

        start_sample = int(start_time * DEFAULT_SAMPLING_RATE)
        end_sample = int(end_time * DEFAULT_SAMPLING_RATE)

        # Extract the audio chunk
        chunk_audio = full_audio_waveform[start_sample:end_sample]

        chunk_emotion_label, chunk_emotion_confidence = infer_chunk_emotion(chunk_segments)

        processed_segment = {
            "id": i, 
            "start": start_time, 
            "end": end_time, 
            "transcript": full_transcript, 
            "audio": chunk_audio,
            "emotion": chunk_emotion_label, 
            "emotion_confidence_score": chunk_emotion_confidence
        }

        processed_segments.append(processed_segment)

    return processed_segments

def resample_audio(
    audio_data: np.ndarray, 
    original_sr: int, 
    target_sr: int
) -> np.ndarray:
    """
    Resamples a NumPy audio waveform from an original to a target sampling rate.

    Args:
        audio_data (np.ndarray): The input audio waveform (1D NumPy array).
        original_sr (int): The original sampling rate of the audio_data.
        target_sr (int): The desired target sampling rate.

    Returns:
        np.ndarray: The resampled audio waveform.
    """
    if original_sr == target_sr:
        return audio_data # No resampling needed
    
    # librosa.resample can take a mono or stereo signal. 
    resampled_audio = librosa.resample(
        y=audio_data.astype(np.float32), # librosa expects float32 for resampling
        orig_sr=original_sr,
        target_sr=target_sr
    )
    return resampled_audio

if __name__ == "__main__":
    VIDEO_FILE_PATH = os.path.join("sample_osce_videos", "osce-physical-exam-demo-video-1.mp4")

    # Extract audio 
    audio_path = extract_audio(VIDEO_FILE_PATH)

    start = time.time()

    whisper_model = load_whisper_model()
    diarization_model = load_diarization_model()
    audio_emotion_classification_model = load_audio_emotion_classification_model()

    audio_segments = process_audio_segments(
        audio_path, 
        whisper_model, 
        diarization_model, 
        audio_emotion_classification_model
    )

    end = time.time()

    print(f"Time elapsed: {end - start} seconds.")

    pprint(audio_segments)