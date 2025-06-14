import uuid 
import numpy as np 
from typing import List, Dict, Any, Optional, TypeVar, Tuple
from pydantic import BaseModel, Field 

from qdrant_client.http import models 
from qdrant_client.http.models import PointStruct

from core.config.config import settings 
from core.vector_store.schemas import SearchResult
from core.vector_store.qdrant_client import QdrantClient

AUDIO_SEGMENT_EMBEDDING_VECTOR_NAME = "audio_segment_clap_embedding" # using CLAP
AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE = 512 # using CLAP
AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_NAME = "audio_segment_transcript_embedding"
AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE = 384 # since we are using sentence transformers

class AudioSegmentMetadata(BaseModel):
    """Metadata for audio segments."""
    id: str = Field(description="Unique identifier for the audio segment, typically matching the Qdrant point ID and part of the MinIO object name.")
    minio_path: str = Field(description="Full path to the audio segment in MinIO.")
    video_id: Optional[str] = Field(default=None, description="Unique ID for the video.")

    start_time: float = Field(description="Start time of the segment within the original audio file (in seconds).")
    end_time: float = Field(description="End time of the segment within the original audio file (in seconds).")
    duration: float = Field(description="Duration of the audio segment (in seconds).")
    sample_rate: int = Field(description="Sample rate of the audio data (e.g., 16000, 44100).")

    transcript: Optional[str] = Field(default=None, description="Full transcript of the audio segment, if available.")
    emotion: str = Field(..., description="Emotion label associated with the audio segment.")
    emotion_confidence_score: Optional[float] = Field(..., description="Confidence score for the predicted emotion label.")

class AudioSegmentRetriever:
    """Handles indexing and retrieval of audio segments."""
    def __init__(
            self,
            client: QdrantClient,
            audio_segment_embedding_vector_size: int = AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE, 
            audio_segment_transcript_embedding_vector_size: int = AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE
        ):
        self.client = client
        self.collection_name = settings.qdrant.audio_segments_collection_name
        
        vectors_config_payload = {
            AUDIO_SEGMENT_EMBEDDING_VECTOR_NAME: models.VectorParams(
                size=audio_segment_embedding_vector_size, 
                distance=models.Distance.COSINE
            ),
            AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_NAME: models.VectorParams(
                size=audio_segment_transcript_embedding_vector_size,
                distance=models.Distance.COSINE
            )
        }

        self.client.create_collection_if_not_exists(
            self.collection_name,
            vectors_config=vectors_config_payload
        )
        
    def index_segment(
            self,
            segment_id: str,
            audio_segment_embedding: np.ndarray, 
            audio_segment_transcript_embedding: np.ndarray, 
            metadata: AudioSegmentMetadata
        ) -> bool:
        point = PointStruct(
            id=segment_id,
            vector={
                AUDIO_SEGMENT_EMBEDDING_VECTOR_NAME: audio_segment_embedding.tolist(), 
                AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_NAME: audio_segment_transcript_embedding.tolist()
            },
            payload=metadata.model_dump()
        )

        success = self.client.upsert_points(
            self.collection_name,
            [point]
        )

        if success:
            print(f"✓ Indexed audio segment '{segment_id}' with audio and transcript embeddings.")

        return success

    def update_segment_metadata(
            self,
            segment_id: str,
            metadata: AudioSegmentMetadata
        ) -> bool:
        # TODO: re-calculate and upsert the transcript embedding if metadata.transcript is updated
        return self.client.update_payload(
            self.collection_name,
            segment_id,
            metadata.model_dump()
        )

    def get_segment_by_id(
            self,
            segment_id: str
        ) -> Optional[SearchResult[AudioSegmentMetadata]]:
        raw_points = self.client.retrieve_points(
            self.collection_name,
            [segment_id]
        )

        if not raw_points:
            return None
        
        p = raw_points[0]

        return SearchResult[AudioSegmentMetadata](
            id=p.id,
            score=-1.0, 
            metadata=AudioSegmentMetadata(**p.payload)
        )
    
    def search_audio_segments_by_transcript(
        self, 
        query_sentence_embedding: np.ndarray, 
        limit: int = 5, 
        search_filter: Optional[models.Filter] = None 
    ) -> List[SearchResult[AudioSegmentMetadata]]:
        """Searches for audio segments based on similarity between 
        query text sentence embedding and audio transcripts sentence embeddings.
        """
        print(f"Searching for audio segments by transcript (Query text sentence embedding vs. Audio transcripts embeddings)....")
        search_query = models.NamedVector(
            name=AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_NAME, 
            vector=query_sentence_embedding.tolist()
        )

        raw_results = self.client.search(
            collection_name=self.collection_name, 
            query_input=search_query,
            limit=limit, 
            search_filter=search_filter
        )

        return [
            SearchResult[AudioSegmentMetadata](
                id=p.id, score=p.score, version=p.version,
                metadata=AudioSegmentMetadata(**p.payload)
            ) for p in raw_results
        ]

    def search_audio_segments_clap(
        self, 
        query_clap_embedding: np.ndarray, 
        limit: int = 5, 
        search_filter: Optional[models.Filter] = None 
    ) -> List[SearchResult[AudioSegmentMetadata]]:
        """Searches for audio segments based on similarity between 
        query text CLAP embedding and audio segment CLAP embeddings.
        """
        print(f"Searching for audio segments based on audio similarity (Query CLAP embedding vs. Audio CLAP embeddings)....")
        search_query = models.NamedVector(
            name=AUDIO_SEGMENT_EMBEDDING_VECTOR_NAME, 
            vector=query_clap_embedding.tolist()
        )

        raw_results = self.client.search(
            collection_name=self.collection_name, 
            query_input=search_query, 
            limit=limit, 
            search_filter=search_filter
        )

        return [
            SearchResult[AudioSegmentMetadata](
                id=p.id, score=p.score, version=p.version,
                metadata=AudioSegmentMetadata(**p.payload)
            ) for p in raw_results
        ]

    def search_audio_segments_hybrid(
        self, 
        query_text: str, 
        query_clap_embedding: np.ndarray, 
        query_sentence_embedding: np.ndarray, 
        limit: int = 10, 
        clap_weight: float = 0.4, 
        transcript_weight: float = 0.6,
        initial_fetch_multiplier: int = 3, 
        search_filter: Optional[models.Filter] = None
    ) -> List[SearchResult[AudioSegmentMetadata]]:
        """
        Performs a HYBRID search using both audio segment CLAP embeddings and audio segment transcript sentence embeddings,
        then re-ranks the results using a weighted sum.
        """
        print(f"Performing hybrid search for query: '{query_text}'")

        # 1. Audio segments CLAP embeddings-based search      
        # We need the raw ScoredPoint from the generic client search for scores
        clap_search_query = models.NamedVector(
            name=AUDIO_SEGMENT_EMBEDDING_VECTOR_NAME, 
            vector=query_clap_embedding.tolist()
        )
        clap_search_results_raw = self.client.search(
            self.collection_name,
            clap_search_query,
            limit * initial_fetch_multiplier,
            search_filter
        )
        print(f"  Found {len(clap_search_results_raw)} audio segment candidates after CLAP-based search (pre-re-ranking).")


        # 2. Audio segment transcript sentence embeddings-based search
        textual_query = models.NamedVector(
            name=AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_NAME,
            vector=query_sentence_embedding.tolist()
        )
        textual_results_raw = self.client.search(
            self.collection_name,
            textual_query,
            limit * initial_fetch_multiplier, 
            search_filter
        )
        print(f"  Found {len(textual_results_raw)} audio segment candidates after sentence embeddings-based search (pre-re-ranking).")

        # 3. Combine and Re-rank Results
        combined_scores: Dict[str | uuid.UUID, Dict[str, Any]] = {} # Store by point ID

        for point in clap_search_results_raw:
            point_id_key = str(point.id) # Use string representation for dict keys

            if point_id_key not in combined_scores:
                combined_scores[point_id_key] = {
                    "payload": point.payload,
                    "clap_search_score": 0.0,
                    "transcript_search_score": 0.0,
                    "version": point.version
                }

            combined_scores[point_id_key]["clap_search_score"] = point.score

        for point in textual_results_raw:
            point_id_key = str(point.id)

            if point_id_key not in combined_scores:
                combined_scores[point_id_key] = {
                    "payload": point.payload,
                    "clap_search_score": 0.0,
                    "transcript_search_score": 0.0,
                    "version": point.version
                }

            combined_scores[point_id_key]["transcript_search_score"] = point.score
            
            if not combined_scores[point_id_key].get("payload"): # Ensure payload is present
                 combined_scores[point_id_key]["payload"] = point.payload

            if combined_scores[point_id_key].get("version") is None: # Ensure version is present
                 combined_scores[point_id_key]["version"] = point.version


        final_results_with_combined_scores: List[Tuple[float, SearchResult[AudioSegmentMetadata]]] = []

        for point_id_str_key, scores_data in combined_scores.items():
            clap_search_score = scores_data.get("clap_search_score", 0.0)
            transcript_search_score = scores_data.get("transcript_search_score", 0.0)
            final_score = (clap_search_score * clap_weight) + (transcript_search_score * transcript_weight)
            
            if scores_data["payload"] is None:
                print(f"Warning: Payload for point ID {point_id_str_key} is None during re-ranking. Skipping.")
                continue

            try:
                final_results_with_combined_scores.append(
                    (final_score, 
                     SearchResult[AudioSegmentMetadata](
                        id=point_id_str_key, 
                        score=final_score,
                        version=scores_data["version"],
                        metadata=AudioSegmentMetadata(**scores_data["payload"])
                     )
                    )
                )

            except Exception as e:
                print(f"Error creating SearchResult for point ID {point_id_str_key} with payload {scores_data['payload']}: {e}")

        final_results_with_combined_scores.sort(key=lambda x: x[0], reverse=True)
        final_ranked_results = [result_obj for _, result_obj in final_results_with_combined_scores][:limit]
        
        print(f"  Re-ranked results. Returning top {len(final_ranked_results)} of {len(combined_scores)} combined unique results.")
        return final_ranked_results

# ------ TESTING ------ 
TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE = AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE 
TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE = AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE 

def generate_mock_embedding(size: int) -> np.ndarray:
    """Generates a random normalized embedding vector."""
    emb = np.random.rand(size).astype(np.float32)
    return emb / np.linalg.norm(emb)
    

def test_audio_segment_retriever():
    """An end-to-end test for the audio segment retriever."""
    print("=== Audio Segment Retriever Test Suite ===\n")

    qdrant_client: QdrantClient | None = None 
    audio_segment_retriever: AudioSegmentRetriever | None = None 

    # Keep track of IDs for cleanup 
    indexed_ids: List[str] = []

    # Mock data for the audio segments 
    seg_id_1 = str(uuid.uuid4())
    seg_id_2 = str(uuid.uuid4())
    seg_id_3 = str(uuid.uuid4())

    video_id = str(uuid.uuid4())

    try: 
        print("--- 1. Initialization ---")
        qdrant_client = QdrantClient(
            host=settings.qdrant.host, 
            port=settings.qdrant.port, 
            api_key=settings.qdrant.api_key, 
            use_https=getattr(settings.qdrant, "https", False)
        )

        assert qdrant_client.check_connection(), "Qdrant connection failed during initialization."

        audio_segment_retriever = AudioSegmentRetriever(
            client=qdrant_client
        )
        print("✓ Clients and AudioSegmentRetriever initialized successfully.")
        print(f"  Using Qdrant collection: {audio_segment_retriever.collection_name}")
        print("-" * 40)

        # --- 2. Indexing Audio Segments ---
        print("\n--- 2. Indexing Audio Segments ---")
        
        # Audio segment 1
        seg1_clap_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE)
        seg1_transcript = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam viverra."
        seg1_transcript_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE) # Mock this for now
        seg1_meta = AudioSegmentMetadata(
            id=seg_id_1, 
            minio_path=f"audio_segments_bucket/{seg_id_1}.wav", 
            video_id=video_id,
            start_time=2.5, 
            end_time=5,
            duration=2.5, 
            sample_rate=16000, 
            transcript=seg1_transcript, 
            emotion="Happy",
            emotion_confidence_score=0.8
        )
        assert audio_segment_retriever.index_segment(seg_id_1, seg1_clap_emb, seg1_transcript_emb, seg1_meta), f"Failed to index audio segment {seg_id_1}"
        indexed_ids.append(seg_id_1)
        print(f" ✓ Indexed audio segment 1: {seg_id_1}")

        # Audio segment 2
        seg2_clap_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE) 
        seg2_transcript = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam viverra."
        seg2_transcript_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE) 
        seg2_meta = AudioSegmentMetadata(
            id=seg_id_2, 
            minio_path=f"audio_segments_bucket/{seg_id_2}.wav", 
            video_id=video_id,
            start_time=5, 
            end_time=7.5,
            duration=2.5, 
            sample_rate=16000, 
            transcript=seg2_transcript, 
            emotion="Sad",
            emotion_confidence_score=0.8
        )
        assert audio_segment_retriever.index_segment(seg_id_2, seg2_clap_emb, seg2_transcript_emb, seg2_meta), f"Failed to index audio segment {seg_id_2}"
        indexed_ids.append(seg_id_2)
        print(f" ✓ Indexed audio segment 2: {seg_id_2}")

        # Audio segment 3
        seg3_clap_emb = seg1_clap_emb + np.random.normal(0, 0.01, TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE)
        seg3_clap_emb = seg3_clap_emb / np.linalg.norm(seg3_clap_emb)
        seg3_transcript = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam viverra."
        seg3_transcript_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE)
        seg3_meta = AudioSegmentMetadata(
            id=seg_id_3, 
            minio_path=f"audio_segments_bucket/{seg_id_3}.wav", 
            video_id=video_id,
            start_time=7.5, 
            end_time=10,
            duration=2.5, 
            sample_rate=16000, 
            transcript=seg3_transcript, 
            emotion="Neutral",
            emotion_confidence_score=0.8
        )
        assert audio_segment_retriever.index_segment(seg_id_3, seg3_clap_emb, seg3_transcript_emb, seg3_meta), f"Failed to index audio segment {seg_id_3}"
        indexed_ids.append(seg_id_3)
        print(f" ✓ Indexed audio segment 3: {seg_id_3}")
        print("-" * 40)

        # --- 3. Get Audio Segment by ID ---
        print("\n--- 3. Get Keyframe by ID ---")
        retrieved_seg1 = audio_segment_retriever.get_segment_by_id(seg_id_1)
        assert retrieved_seg1, f"Failed to retrieve audio segment by ID."
        assert retrieved_seg1.id == seg_id_1, "Retrieved audio segment ID mismatch."
        assert retrieved_seg1.metadata.transcript == seg1_transcript, "Retrieved audio segment transcript mismatch."
        print(f"✓ Successfully retrieved audio segment: ID {retrieved_seg1.id}, Desc: '{retrieved_seg1.metadata.transcript[:30]}...'")
        print("-" * 40)

        # --- 4. Update Audio Segment Metadata ---
        print("\n--- 4. Update Audio Segment Metadata ---")
        updated_transcript = "Updated audio segment transcript."
        updated_seg1_meta_payload = seg1_meta.model_copy(update={
            "transcript": updated_transcript
        })

        assert audio_segment_retriever.update_segment_metadata(seg_id_1, updated_seg1_meta_payload), f"Failed to update metadata for audio segment."
        
        retrieved_after_update_seg1 = audio_segment_retriever.get_segment_by_id(seg_id_1)
        assert retrieved_after_update_seg1 and retrieved_after_update_seg1.metadata.transcript == updated_transcript, "audio segment metadata description not updated."
        print(f"✓ Successfully updated and verified metadata for audio segment. New transcript: '{retrieved_after_update_seg1.metadata.transcript}'")
        print("-" * 40)

        # --- 5. Search Tests ---
        print("\n--- 5. Search Tests ---")
        query1_text = "doctor examining patient"
        query1_clap_emb = seg1_clap_emb + np.random.normal(0, 0.02, TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE)
        query1_clap_emb = query1_clap_emb / np.linalg.norm(query1_clap_emb)
        query1_sentence_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE)

        query2_text = "student washing hands"
        query2_clap_emb = generate_mock_embedding(TEST_AUDIO_SEGMENT_EMBEDDING_VECTOR_SIZE)
        query2_sentence_emb = seg3_transcript_emb + np.random.normal(0, 0.02, TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE)
        query2_sentence_emb = query2_sentence_emb / np.linalg.norm(query2_sentence_emb)

        # Test 5A: Search by CLAP embeddings
        print("\n  --- 5A. CLAP embeddings search ---")
        clap_search_results = audio_segment_retriever.search_audio_segments_clap(
            query_clap_embedding=query1_clap_emb, 
            limit=3 
        )
        assert len(clap_search_results) > 0, "CLAP search returned no results."
        clap_search_results_ids = {str(r.id) for r in clap_search_results}
        assert seg_id_1 in clap_search_results_ids, f"Audio segment 1 not found in CLAP search results for '{query1_text}'"
        assert seg_id_3 in clap_search_results_ids, f"Audio segment 2 not found in CLAP search results for '{query1_text}'"
        print(f"  ✓ CLAP search found relevant items. Top result ID: {clap_search_results[0].id}, Score: {clap_search_results[0].score:.4f}")

        print("-" * 40)

        # Test 5B: Search by Transcript sentence embeddings
        print("\n  --- 5B. Transcript sentence embeddings search ---")
        transcript_search_results = audio_segment_retriever.search_audio_segments_by_transcript(
            query_sentence_embedding=query2_sentence_emb,
            limit=3 
        )
        assert len(transcript_search_results) > 0, "Transcript returned no results."
        transcript_search_results_ids = {str(r.id) for r in clap_search_results}
        assert seg_id_3 in transcript_search_results_ids, f"Audio segment 3 not found in transcript search results for '{query2_text}'"
        print(f"  ✓ Transcript search found relevant items. Top result ID: {transcript_search_results[0].id}, Score: {transcript_search_results[0].score:.4f}")

        # Test 5C: Hybrid Search
        print("\n  --- 5C. Hybrid Search ---")
        query1_transcript_emb_for_hybrid = seg1_transcript_emb + np.random.normal(0, 0.01, TEST_AUDIO_SEGMENT_TRANSCRIPT_EMBEDDING_VECTOR_SIZE)
        query1_trascript_emb_for_hybrid = query1_transcript_emb_for_hybrid / np.linalg.norm(query1_transcript_emb_for_hybrid)

        hybrid_results = audio_segment_retriever.search_audio_segments_hybrid(
            query_text=query1_text,
            query_clap_embedding=query1_clap_emb, # Visually like KF1/KF3
            query_sentence_embedding=query1_transcript_emb_for_hybrid, # Textually like KF1
            limit=3,
            clap_weight=0.4, 
            transcript_weight=0.6
        )
        assert len(hybrid_results) > 0, "Hybrid search returned no results."

        # Audio segment 1 should be ranked higher than audio segment 3 due to matching both modalities for query1
        # Audio segment 3 matches query1 based on CLAP embeddings, but its transcript does not match

        hybrid_result_ids = [str(r.id) for r in hybrid_results]
        assert hybrid_result_ids[0] == seg_id_1, f"Hybrid search did not rank KF1 first for '{query1_text}'. Top was {hybrid_result_ids[0]}"
        print(f"  ✓ Hybrid search successful. Top result ID: {hybrid_results[0].id}, Hybrid Score: {hybrid_results[0].score:.4f}")
        print(f"    Audio segment 1 CLAP search score component (approx): {hybrid_results[0].score / (0.6 + 0.4 * (np.dot(query1_transcript_emb_for_hybrid, seg1_transcript_emb) if hybrid_results[0].id == seg_id_1 else 0)):.4f}") # Rough estimate
        print(f"    Audio segment 1 transcript search score component (approx): {hybrid_results[0].score / (0.4 + 0.6 * (np.dot(query1_clap_emb, seg1_clap_emb) if hybrid_results[0].id == seg_id_1 else 0)):.4f}") # Rough estimate

        print("-" * 40)

    except AssertionError as e:
        print(f"\n!!!!!! TEST FAILED (AssertionError) !!!!!!")
        print(f"✗ ASSERTION FAILED: {e}")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n!!!!!! An unexpected error occurred during the test suite !!!!!!")
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally: 
        # -- 6. Cleanup --- 
        print("\n--- 6. Cleanup ---")
        if qdrant_client and audio_segment_retriever and indexed_ids:
            print(f"Attempting to delete {len(indexed_ids)} test points from collection '{audio_segment_retriever.collection_name}'...")
            success_delete = qdrant_client.delete_points(audio_segment_retriever.collection_name, indexed_ids)
            if success_delete:
                print(f"✓ Successfully deleted test points from Qdrant.")
            else:
                print(f"✗ Failed to delete all test points from Qdrant. Manual cleanup may be needed.")
        elif qdrant_client and audio_segment_retriever:
             print("No points were successfully indexed to clean up from Qdrant.")
        else:
            print("Qdrant client or retriever not initialized, skipping Qdrant cleanup.")

            
    print("\n=== Audio Segment Retriever Test Suite Completed ===")

if __name__ == "__main__":
    try:
        test_audio_segment_retriever()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")