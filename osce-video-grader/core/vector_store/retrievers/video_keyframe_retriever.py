import uuid 
import numpy as np 
from typing import List, Dict, Any, Optional, Tuple 
from pydantic import BaseModel, Field 

from qdrant_client.http import models 
from qdrant_client.http.models import PointStruct

from core.config.config import settings 
from core.vector_store.schemas import SearchResult
from core.vector_store.qdrant_client import QdrantClient

KEYFRAME_IMAGE_EMBEDDING_VECTOR_NAME = "keyframe_embedding"
KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE = 512 
KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_NAME = "keyframe_description_embedding" 
KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE = 384 # since we are using sentence transformers 

class VideoKeyframeMetadata(BaseModel):
    """
    Metadata for a video keyframe.
    """
    id: str = Field(description="Unique identifier for the audio segment.")
    minio_path: str = Field(description="Full path to the video keyframe in MinIO.")
    video_id: Optional[str] = Field(default=None, description="Unique ID for the video.")

    frame_number: Optional[int] = Field(default=None, description="The frame number of the keyframe within the original video file.")
    timestamp: float = Field(description="Precise timestamp of the keyframe within the original video file (in seconds).")
    description: Optional[str] = Field(default=None, description="Description of the keyframe, if available.")
    objects: Optional[List[str]] = Field(default=[], description="List of objects detected in the keyframe, if available.")

class VideoKeyframeRetriever:
    """Handles the business logic for indexing and retrieving video keyframes."""
    def __init__(
            self,
            client: QdrantClient,
            keyframe_image_embedding_vector_size: int = KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE,
            keyframe_description_embedding_vector_size: int = KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE
        ):
        self.client = client
        self.collection_name = settings.qdrant.video_keyframes_collection_name

        vectors_config_payload = {
            KEYFRAME_IMAGE_EMBEDDING_VECTOR_NAME: models.VectorParams(
                size=keyframe_image_embedding_vector_size, 
                distance=models.Distance.COSINE
            ),
            KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_NAME: models.VectorParams(
                size=keyframe_description_embedding_vector_size, 
                distance=models.Distance.COSINE
            )
        }

        self.client.create_collection_if_not_exists(
            self.collection_name, 
            vectors_config=vectors_config_payload 
        )

    def index_keyframe(
            self, 
            keyframe_id: str,
            keyframe_image_embedding: np.ndarray, 
            keyframe_description_embedding: np.ndarray,
            metadata: VideoKeyframeMetadata
        ) -> bool:
        """
        Indexes a video keyframe with its CLIP image embedding and description embedding.
        """
        if not metadata.description:
            print(f"Warning: Indexing keyframe {keyframe_id} without a description in metadata. Text-to-image search might be ineffective.")
            
        point = PointStruct(
            id=keyframe_id, 
            vector={
                KEYFRAME_IMAGE_EMBEDDING_VECTOR_NAME: keyframe_image_embedding.tolist(),
                KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_NAME: keyframe_description_embedding.tolist()
            },
            payload=metadata.model_dump()
        )

        success = self.client.upsert_points(self.collection_name, [point])

        if success:
            print(f"✓ Indexed video keyframe '{keyframe_id}' with image and description embeddings.")

        return success

    def update_keyframe_metadata(
            self,
            keyframe_id: str, 
            metadata: VideoKeyframeMetadata
        ) -> bool:
        # TODO: re-calculate and upsert the description embedding if metadata.description is updated
        return self.client.update_payload(
            self.collection_name,
            keyframe_id,
            metadata.model_dump()
        )

    def get_keyframe_by_id(
            self, 
            keyframe_id: str
        ) -> Optional[SearchResult[VideoKeyframeMetadata]]:
        raw_points = self.client.retrieve_points(
            self.collection_name,
            [keyframe_id]
        )

        if not raw_points: 
            return None
        
        p = raw_points[0]

        return SearchResult[VideoKeyframeMetadata](
            id=p.id,
            score=-1.0,
            metadata=VideoKeyframeMetadata(**p.payload)
        )

    def search_keyframes_clip(
        self,
        query_clip_embedding: np.ndarray, # CLIP embedding of the text query
        limit: int = 5,
        search_filter: Optional[models.Filter] = None
    ) -> List[SearchResult[VideoKeyframeMetadata]]:
        """
        Searches for keyframes based purely on VISUAL similarity
        (CLIP text query embedding vs. stored CLIP image keyframe embeddings).
        """
        print(f"Performing visual-only search i.e. Query CLIP embedding vs. Keyframe CLIP image embeddings...")
        search_query = models.NamedVector(
            name=KEYFRAME_IMAGE_EMBEDDING_VECTOR_NAME, 
            vector=query_clip_embedding.tolist()
        )
        
        raw_results = self.client.search(
            collection_name=self.collection_name,
            query_input=search_query,
            limit=limit,
            search_filter=search_filter
        )
        
        return [
            SearchResult[VideoKeyframeMetadata](
                id=p.id, score=p.score, version=p.version,
                metadata=VideoKeyframeMetadata(**p.payload)
            ) for p in raw_results
        ]
    
    def search_keyframes_by_description(
        self,
        query_sentence_embedding: np.ndarray, # SentenceTransformer embedding of the query text
        limit: int = 5,
        search_filter: Optional[models.Filter] = None
    ) -> List[SearchResult[VideoKeyframeMetadata]]:
        """
        Searches for keyframes based purely on TEXTUAL similarity between query embedding and description embeddings.
        """
        print(f"Performing textual-only search (Query text embedding vs. Keyframe description embedding)...")
        search_query = models.NamedVector(
            name=KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_NAME, 
            vector=query_sentence_embedding.tolist()
        )
        
        raw_results = self.client.search(
            collection_name=self.collection_name,
            query_input=search_query,
            limit=limit,
            search_filter=search_filter
        )
        
        return [
            SearchResult[VideoKeyframeMetadata](
                id=p.id, score=p.score, version=p.version,
                metadata=VideoKeyframeMetadata(**p.payload)
            ) for p in raw_results
        ]

    def search_keyframes_hybrid(
        self,
        query_text: str,
        query_clip_embedding: np.ndarray,
        query_sentence_embedding: np.ndarray,
        limit: int = 10,
        clip_weight: float = 0.6,
        description_weight: float = 0.4,
        initial_fetch_multiplier: int = 3,
        search_filter: Optional[models.Filter] = None # Filter applied to both searches
    ) -> List[SearchResult[VideoKeyframeMetadata]]:
        """
        Performs a HYBRID search using both video keyframe CLIP embeddings and video keyframe description sentence embeddings,
        then re-ranks the results using a weighted sum.
        """
        print(f"Performing hybrid search for query: '{query_text}'")

        # 1. Video keyframes CLIP embeddings-based Search        
        # We need the raw ScoredPoint from the generic client search for scores
        visual_query = models.NamedVector(
            name=KEYFRAME_IMAGE_EMBEDDING_VECTOR_NAME, 
            vector=query_clip_embedding.tolist()
        )
        visual_results_raw = self.client.search(
            self.collection_name,
            visual_query,
            limit * initial_fetch_multiplier,
            search_filter
        )
        print(f"  Found {len(visual_results_raw)} visual matches (pre-re-ranking).")


        # 2. Video keyframes descriptions sentence embeddings-based search
        textual_query = models.NamedVector(
            name=KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_NAME,
            vector=query_sentence_embedding.tolist()
        )
        textual_results_raw = self.client.search(
            self.collection_name,
            textual_query,
            limit * initial_fetch_multiplier, 
            search_filter
        )
        print(f"  Found {len(textual_results_raw)} textual matches (pre-re-ranking).")

        # 3. Combine and Re-rank Results
        combined_scores: Dict[str | uuid.UUID, Dict[str, Any]] = {} # Store by point ID

        for point in visual_results_raw:
            point_id_key = str(point.id) # Use string representation for dict keys

            if point_id_key not in combined_scores:
                combined_scores[point_id_key] = {
                    "payload": point.payload,
                    "clip_search_score": 0.0,
                    "description_search_score": 0.0,
                    "version": point.version
                }

            combined_scores[point_id_key]["clip_search_score"] = point.score

        for point in textual_results_raw:
            point_id_key = str(point.id)

            if point_id_key not in combined_scores:
                combined_scores[point_id_key] = {
                    "payload": point.payload,
                    "clip_search_score": 0.0,
                    "description_search_score": 0.0,
                    "version": point.version
                }

            combined_scores[point_id_key]["description_search_score"] = point.score
            
            if not combined_scores[point_id_key].get("payload"): # Ensure payload is present
                 combined_scores[point_id_key]["payload"] = point.payload

            if combined_scores[point_id_key].get("version") is None: # Ensure version is present
                 combined_scores[point_id_key]["version"] = point.version


        final_results_with_combined_scores: List[Tuple[float, SearchResult[VideoKeyframeMetadata]]] = []

        for point_id_str_key, scores_data in combined_scores.items():
            clip_search_score = scores_data.get("clip_search_score", 0.0)
            description_search_score = scores_data.get("description_search_score", 0.0)
            final_score = (clip_search_score * clip_weight) + (description_search_score * description_weight)
            
            if scores_data["payload"] is None:
                print(f"Warning: Payload for point ID {point_id_str_key} is None during re-ranking. Skipping.")
                continue

            try:
                final_results_with_combined_scores.append(
                    (final_score, 
                     SearchResult[VideoKeyframeMetadata](
                        id=point_id_str_key, 
                        score=final_score,
                        version=scores_data["version"],
                        metadata=VideoKeyframeMetadata(**scores_data["payload"])
                     )
                    )
                )

            except Exception as e:
                print(f"Error creating SearchResult for point ID {point_id_str_key} with payload {scores_data['payload']}: {e}")

        final_results_with_combined_scores.sort(key=lambda x: x[0], reverse=True)
        final_ranked_results = [result_obj for _, result_obj in final_results_with_combined_scores][:limit]
        
        print(f"  Re-ranked results. Returning top {len(final_ranked_results)} of {len(combined_scores)} combined unique results.")
        return final_ranked_results
    

# ------- TESTING --------
# These test cases were generated by Gemini pro with minimal edits
TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE = KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE
TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE = KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE

def generate_mock_embedding(size: int) -> np.ndarray:
    """Generates a random normalized embedding vector."""
    emb = np.random.rand(size).astype(np.float32)
    return emb / np.linalg.norm(emb)
    
def test_video_keyframe_retriever():
    """
    A comprehensive standalone test script for the VideoKeyframeRetriever class,
    covering indexing, getting, updating, and all three search methods.
    """
    print("=== VideoKeyframeRetriever Comprehensive Test Suite ===\n")
    
    qdrant_client: QdrantClient | None = None
    video_keyframe_retriever: VideoKeyframeRetriever | None = None
    
    # Keep track of IDs for cleanup
    indexed_ids: List[str] = []

    # Mock data for keyframes
    kf_id_1 = str(uuid.uuid4())
    kf_id_2 = str(uuid.uuid4())
    kf_id_3 = str(uuid.uuid4()) # Will have a description very different from its visual

    video_id = str(uuid.uuid4())

    try:
        # --- 1. Initialization ---
        print("--- 1. Initialization ---")
        qdrant_client = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key,
            use_https=getattr(settings.qdrant, 'https', False)
        )
        assert qdrant_client.check_connection(), "Qdrant connection failed during initialization."
        
        video_keyframe_retriever = VideoKeyframeRetriever(
            client=qdrant_client
        )
        print("✓ Clients and VideoKeyframeRetriever initialized successfully.")
        print(f"  Using Qdrant collection: {video_keyframe_retriever.collection_name}")
        print("-" * 40)

        # --- 2. Indexing Keyframes ---
        print("\n--- 2. Indexing Keyframes ---")
        
        # Keyframe 1: Visually about "a doctor examining a patient"
        # Description also matches this.
        kf1_clip_emb = generate_mock_embedding(TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE)
        kf1_desc = "A doctor is carefully examining a patient in a clinic room."
        kf1_desc_emb = generate_mock_embedding(TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE) # Mock this for now
        kf1_meta = VideoKeyframeMetadata(
            id=kf_id_1, minio_path=f"vid_bucket/{kf_id_1}.jpg", timestamp=10.5, frame_number=105,
            video_id=video_id, description=kf1_desc
        )
        assert video_keyframe_retriever.index_keyframe(kf_id_1, kf1_clip_emb, kf1_desc_emb, kf1_meta), f"Failed to index KF1 {kf_id_1}"
        indexed_ids.append(kf_id_1)
        print(f" ✓ Indexed Keyframe 1 (Visual: doctor, Text: doctor): {kf_id_1}")

        # Keyframe 2: Visually about "a medical chart"
        # Description also matches this.
        kf2_clip_emb = generate_mock_embedding(TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE) # Different visual
        kf2_desc = "Close-up of a medical chart with patient data."
        kf2_desc_emb = generate_mock_embedding(TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE) # Different text
        kf2_meta = VideoKeyframeMetadata(
            id=kf_id_2, minio_path=f"vid_bucket/{kf_id_2}.jpg", timestamp=20.2, frame_number=202,
            video_id=video_id, description=kf2_desc
        )
        assert video_keyframe_retriever.index_keyframe(kf_id_2, kf2_clip_emb, kf2_desc_emb, kf2_meta), f"Failed to index KF2 {kf_id_2}"
        indexed_ids.append(kf_id_2)
        print(f" ✓ Indexed Keyframe 2 (Visual: chart, Text: chart): {kf_id_2}")

        # Keyframe 3: Visually about "a doctor examining a patient" (similar to KF1 visually)
        # BUT its description is about "student washing hands" (very different textually)
        kf3_clip_emb = kf1_clip_emb + np.random.normal(0, 0.01, TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE) # Visually similar to KF1
        kf3_clip_emb = kf3_clip_emb / np.linalg.norm(kf3_clip_emb)
        kf3_desc = "Student is thoroughly washing their hands at a sink."
        kf3_desc_emb = generate_mock_embedding(TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE) # Very different text embedding
        kf3_meta = VideoKeyframeMetadata(
            id=kf_id_3, minio_path=f"vid_bucket/{kf_id_3}.jpg", timestamp=30.8, frame_number=308,
            video_id=video_id, description=kf3_desc
        )
        assert video_keyframe_retriever.index_keyframe(kf_id_3, kf3_clip_emb, kf3_desc_emb, kf3_meta), f"Failed to index KF3 {kf_id_3}"
        indexed_ids.append(kf_id_3)
        print(f" ✓ Indexed Keyframe 3 (Visual: doctor, Text: washing hands): {kf_id_3}")
        print("-" * 40)

        # --- 3. Get Keyframe by ID ---
        print("\n--- 3. Get Keyframe by ID ---")
        retrieved_kf1 = video_keyframe_retriever.get_keyframe_by_id(kf_id_1)
        assert retrieved_kf1, f"Failed to retrieve KF1 by ID."
        assert retrieved_kf1.id == kf_id_1, "Retrieved KF1 ID mismatch."
        assert retrieved_kf1.metadata.description == kf1_desc, "Retrieved KF1 description mismatch."
        print(f"✓ Successfully retrieved KF1: ID {retrieved_kf1.id}, Desc: '{retrieved_kf1.metadata.description[:30]}...'")
        print("-" * 40)

        # --- 4. Update Keyframe Metadata ---
        print("\n--- 4. Update Keyframe Metadata ---")
        updated_kf1_meta_payload = kf1_meta.model_copy(update={"description": "Doctor examining patient, updated."})
        # Note: If description changes, the description_embedding is NOT automatically updated by this method.
        # A full re-index or a dedicated update_vector method would be needed for that.
        assert video_keyframe_retriever.update_keyframe_metadata(kf_id_1, updated_kf1_meta_payload), f"Failed to update metadata for KF1."
        
        retrieved_after_update_kf1 = video_keyframe_retriever.get_keyframe_by_id(kf_id_1)
        assert retrieved_after_update_kf1 and retrieved_after_update_kf1.metadata.description == "Doctor examining patient, updated.", "KF1 metadata description not updated."
        print(f"✓ Successfully updated and verified metadata for KF1. New desc: '{retrieved_after_update_kf1.metadata.description[:30]}...'")
        print("-" * 40)

        # --- 5. Search Tests ---
        print("\n--- 5. Search Tests ---")
        # Mock query embeddings. In a real scenario, these would come from your CLIP and SentenceTransformer models.
        # Query 1: "doctor examining patient" (should match KF1 and KF3 visually, KF1 textually)
        query1_text = "doctor examining patient"
        query1_clip_emb = kf1_clip_emb + np.random.normal(0, 0.02, TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE) # Similar to KF1's visual
        query1_clip_emb = query1_clip_emb / np.linalg.norm(query1_clip_emb)
        query1_desc_emb = generate_mock_embedding(TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE) # Assume this matches kf1_desc_emb closely

        # Query 2: "student washing hands" (should match KF3 textually, not visually for KF1/KF2)
        query2_text = "student washing hands"
        query2_clip_emb = generate_mock_embedding(TEST_KEYFRAME_IMAGE_EMBEDDING_VECTOR_SIZE) # Generic visual query
        query2_desc_emb = kf3_desc_emb + np.random.normal(0, 0.02, TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE) # Similar to KF3's description
        query2_desc_emb = query2_desc_emb / np.linalg.norm(query2_desc_emb)

        # Test 5A: Visual Search
        print("\n  --- 5A. Visual Search (Query: 'doctor examining patient') ---")
        visual_results = video_keyframe_retriever.search_keyframes_clip(query_clip_embedding=query1_clip_emb, limit=3)
        assert len(visual_results) > 0, "Visual search returned no results."
        visual_result_ids = {str(r.id) for r in visual_results}
        assert kf_id_1 in visual_result_ids, f"KF1 (visual 'doctor') not found in visual search for '{query1_text}'"
        assert kf_id_3 in visual_result_ids, f"KF3 (visual 'doctor') not found in visual search for '{query1_text}'"
        print(f"  ✓ Visual search found relevant items. Top result ID: {visual_results[0].id}, Score: {visual_results[0].score:.4f}")

        # Test 5B: Textual Search
        print("\n  --- 5B. Textual Search (Query: 'student washing hands') ---")
        textual_results = video_keyframe_retriever.search_keyframes_by_description(query_sentence_embedding=query2_desc_emb, limit=3)
        assert len(textual_results) > 0, "Textual search returned no results."
        textual_result_ids = {str(r.id) for r in textual_results}
        assert kf_id_3 in textual_result_ids, f"KF3 (text 'washing hands') not found in textual search for '{query2_text}'"
        print(f"  ✓ Textual search found relevant items. Top result ID: {textual_results[0].id}, Score: {textual_results[0].score:.4f}")

        # Test 5C: Hybrid Search
        print("\n  --- 5C. Hybrid Search (Query: 'doctor examining patient') ---")
        query1_desc_emb_for_hybrid = kf1_desc_emb + np.random.normal(0, 0.01, TEST_KEYFRAME_DESCRIPTION_EMBEDDING_VECTOR_SIZE)
        query1_desc_emb_for_hybrid = query1_desc_emb_for_hybrid / np.linalg.norm(query1_desc_emb_for_hybrid)

        hybrid_results = video_keyframe_retriever.search_keyframes_hybrid(
            query_text=query1_text,
            query_clip_embedding=query1_clip_emb, # Visually like KF1/KF3
            query_sentence_embedding=query1_desc_emb_for_hybrid, # Textually like KF1
            limit=3,
            clip_weight=0.6,
            description_weight=0.4
        )
        assert len(hybrid_results) > 0, "Hybrid search returned no results."
        # KF1 should be ranked higher than KF3 due to matching both modalities for query1
        # KF3 matches query1 visually, but its description ("washing hands") doesn't match query1_desc_emb_for_hybrid
        hybrid_result_ids = [str(r.id) for r in hybrid_results]
        assert hybrid_result_ids[0] == kf_id_1, f"Hybrid search did not rank KF1 first for '{query1_text}'. Top was {hybrid_result_ids[0]}"
        print(f"  ✓ Hybrid search successful. Top result ID: {hybrid_results[0].id}, Hybrid Score: {hybrid_results[0].score:.4f}")
        print(f"    KF1 visual score component (approx): {hybrid_results[0].score / (0.6 + 0.4 * (np.dot(query1_desc_emb_for_hybrid, kf1_desc_emb) if hybrid_results[0].id == kf_id_1 else 0)):.4f}") # Rough estimate
        print(f"    KF1 textual score component (approx): {hybrid_results[0].score / (0.4 + 0.6 * (np.dot(query1_clip_emb, kf1_clip_emb) if hybrid_results[0].id == kf_id_1 else 0)):.4f}") # Rough estimate

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
        # --- 6. Cleanup ---
        print("\n--- 6. Cleanup ---")
        if qdrant_client and video_keyframe_retriever and indexed_ids:
            print(f"Attempting to delete {len(indexed_ids)} test points from collection '{video_keyframe_retriever.collection_name}'...")
            success_delete = qdrant_client.delete_points(video_keyframe_retriever.collection_name, indexed_ids)
            if success_delete:
                print(f"✓ Successfully deleted test points from Qdrant.")
            else:
                print(f"✗ Failed to delete all test points from Qdrant. Manual cleanup may be needed.")
        elif qdrant_client and video_keyframe_retriever:
             print("No po   ints were successfully indexed to clean up from Qdrant.")
        else:
            print("Qdrant client or retriever not initialized, skipping Qdrant cleanup.")
            
    print("\n=== Video Keyframe Retriever Test Suite Completed ===")


if __name__ == "__main__":
    try:
        test_video_keyframe_retriever()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")