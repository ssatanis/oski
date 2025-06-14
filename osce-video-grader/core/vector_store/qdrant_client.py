import uuid 
from typing import List, Dict, Any, Optional, Union 

import numpy as np
from qdrant_client import QdrantClient as OfficialQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    PointStruct, UpdateStatus, ScoredPoint, 
    Filter, FieldCondition, MatchValue, 
    Record, QueryResponse, VectorParams, 
    NamedVector, Distance 
)

from core.config.config import settings 

class QdrantClient:
    """
    A generic client wrapper for interacting with a Qdrant vector database.
    This class provides a low-level interface for core Qdrant operations.
    """
    def __init__(
        self, 
        host: str = settings.qdrant.host, 
        port: int = settings.qdrant.port, 
        api_key: Optional[str] = settings.qdrant.api_key,
        use_https: bool = getattr(settings.qdrant, 'use_https', False)
    ):
        """Initializes the Qdrant client."""
        self.client = OfficialQdrantClient(
            host=host,
            port=port,
            api_key=api_key,
            https=use_https
        )
        print(f"Qdrant client initialized, connected to {host}:{port}")

    def create_collection_if_not_exists(
            self,
            collection_name: str,
            vectors_config: Union[VectorParams, Dict[str, VectorParams]]
        ):
        """Creates a collection if it doesn't already exist."""
        try:
            _ = self.client.get_collection(collection_name=collection_name)
            
            print(f"Collection '{collection_name}' already exists.")
        
        except Exception:
            print(f"Collection '{collection_name}' not found. Creating it...")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=vectors_config
            )

            print(f"Collection '{collection_name}' created.")

    def upsert_points(
            self, 
            collection_name: str, 
            points: List[PointStruct]
        ) -> bool:
        """
        Upserts (inserts or updates) points into a specified collection.

        Args:
            collection_name: The name of the collection.
            points: A list of PointStruct objects to be upserted.

        Returns:
            True if the operation was successful, False otherwise.
        """
        try:
            operation_info = self.client.upsert(
                collection_name=collection_name,
                wait=True,
                points=points
            )

            return operation_info.status == UpdateStatus.COMPLETED
        
        except Exception as e:
            print(f"Error upserting points to '{collection_name}': {e}")
            return False
        
    def update_payload(
            self,
            collection_name: str,
            point_id: str,
            payload: Dict[str, Any]
        ) -> bool:
        """
        Updates the payload for a specific point in a collection.

        Args:
            collection_name: The name of the collection.
            point_id: The ID of the point to update.
            payload: The new payload dictionary to set.

        Returns:
            True if the operation was successful, False otherwise.
        """
        try:
            operation_info = self.client.set_payload(
                collection_name=collection_name,
                payload=payload,
                points=[point_id],
                wait=True
            )

            return operation_info.status == UpdateStatus.COMPLETED
        
        except Exception as e:
            print(f"Error updating payload for point '{point_id}' in '{collection_name}': {e}")
            return False
        
    def retrieve_points(
        self,
        collection_name: str, 
        point_ids: List[str],
        with_vectors: Union[bool, List[str]] = False
    ) -> List[Record]:
        """
        Retrieves points from a specified collection by their IDs.
        Can optionally retrieve specified named vectors or all vectors (if `with_vectors=True`)

        Args:
            collection_name: The name of the collection to retrieve from.
            point_ids: A list of point IDs to retrieve.

        Returns:
            A list of Record objects containing the retrieved points."""
        try:
            return self.client.retrieve(
                collection_name=collection_name,
                ids=point_ids,
                with_payload=True,
                with_vectors=with_vectors
            )
        
        except Exception as e:
            print(f"Error retrieving points from collection '{collection_name}': {e}")
            return []
        
    def search(
        self,
        collection_name: str,
        query_input: Union[List[float], NamedVector],
        limit: int = 10,
        search_filter: Optional[models.Filter] = None,
        with_vectors: Union[bool, List[str]] = False 
    ) -> List[ScoredPoint]:
        """
        Performs a vector search in a collection.
        If query_vector is a list, searches the default vector (if any).
        If query_vector is a NamedVector, searches the specified named vector.

        Args:
            collection_name: The name of the collection to search in.
            query_vector: The vector to search with.
            limit: The maximum number of results to return.
            search_filter: An optional filter to apply to the search.

        Returns:
            A list of ScoredPoint objects.
        """
        actual_query_vector: List[float]
        vector_name_to_use: Optional[str] = None

        if isinstance(query_input, NamedVector):
            actual_query_vector = query_input.vector
            vector_name_to_use = query_input.name
        elif isinstance(query_input, list):
            actual_query_vector = query_input
        else:
            raise ValueError(f"Unsupported query_vector type: {type(query_input)}")


        try:
            response: QueryResponse = self.client.query_points(
                collection_name=collection_name,
                query=actual_query_vector,
                using=vector_name_to_use,
                limit=limit,
                query_filter=search_filter,
                with_payload=True, # Always retrieve payload with search results,
                with_vectors=with_vectors
            )

            return response.points
        
        except Exception as e:
            print(f"Error searching in collection '{collection_name}': {e}")
            return []
        
    def delete_points(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        """
        Deletes points from a specified collection by their IDs.

        Args:
            collection_name: The name of the collection.
            point_ids: A list of point IDs to delete.

        Returns:
            True if the operation was successful, False otherwise.
        """
        try:
            operation_info = self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
                wait=True
            )

            return operation_info.status == UpdateStatus.COMPLETED
        
        except Exception as e:
            print(f"Error deleting points from '{collection_name}': {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """Deletes an entire collection."""
        try:
            result = self.client.delete_collection(collection_name=collection_name)
            print(f"Collection '{collection_name}' deletion initiated. Result: {result}")
            return result
        
        except Exception as e:
            print(f"Error deleting collection '{collection_name}': {e}")
            return False
        
    def check_connection(self) -> bool:
        """Checks if the connection to the Qdrant server is alive."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            print(f"✗ Qdrant connection failed: {e}")
            return False
        
def test_qdrant_client():
    """A standalone test script for the QdrantClient class."""
    print("=== Qdrant Client Test Suite ===\n")
    
    client: QdrantClient | None = None
    default_collection_name = f"test-default-vec-coll-{uuid.uuid4()}"
    named_collection_name = f"test-named-vec-coll-{uuid.uuid4()}"
    vector_size = 4 
    
    image_vec_name = "image_vector"
    text_vec_name = "text_vector"
    image_vec_size = 4
    text_vec_size = 3

    point_id_default_1 = str(uuid.uuid4())
    point_id_default_2 = str(uuid.uuid4())
    point_id_named_1 = str(uuid.uuid4())
    
    try:
        # --- Initialization & Connection ---
        print("--- 1. Initialization & Connection ---")
        client = QdrantClient()
        if not client.check_connection():
            raise ConnectionError("Initial connection check to Qdrant failed.")
        print("✓ Qdrant client initialized and connection successful.")
        print("-" * 40)

        # 2A: Default vector collection creation 
        print(f"\n--- 2A. Default Vector Collection Creation ('{default_collection_name}') ---")
        default_vectors_config = VectorParams(size=vector_size, distance=Distance.COSINE)
        client.create_collection_if_not_exists(default_collection_name, vectors_config=default_vectors_config)
        client.create_collection_if_not_exists(default_collection_name, vectors_config=default_vectors_config) # Idempotency
        
        collection_info_default = client.client.get_collection(collection_name=default_collection_name)
        # Check for default vector configuration
        actual_vectors_config = collection_info_default.config.params.vectors
        if isinstance(actual_vectors_config, VectorParams): # Single, unnamed vector
            assert actual_vectors_config.size == vector_size
            assert actual_vectors_config.distance == Distance.COSINE
        elif isinstance(actual_vectors_config, dict) and "" in actual_vectors_config: # Default vector named ""
            assert actual_vectors_config[""].size == vector_size
            assert actual_vectors_config[""].distance == Distance.COSINE
        else:
            raise AssertionError(f"Default vector config not found or in unexpected format: {actual_vectors_config}")
        print("✓ Default vector collection created successfully.")
        print("-" * 40)

        # 2B: Named vector collection creation 
        print(f"\n--- 2B. Named Vector Collection Creation ('{named_collection_name}') ---")
        named_vectors_config = {
            image_vec_name: VectorParams(size=image_vec_size, distance=Distance.DOT),
            text_vec_name: VectorParams(size=text_vec_size, distance=Distance.EUCLID)
        }
        client.create_collection_if_not_exists(named_collection_name, vectors_config=named_vectors_config)
        collection_info_named = client.client.get_collection(collection_name=named_collection_name)
        assert image_vec_name in collection_info_named.config.params.vectors
        assert collection_info_named.config.params.vectors[image_vec_name].size == image_vec_size
        assert collection_info_named.config.params.vectors[text_vec_name].size == text_vec_size
        print("✓ Named vector collection created successfully.")
        print("-" * 40)

        # Upsert points to collections
        # To default vector collection
        print(f"\n--- 3A. Point Upsert (to '{default_collection_name}') ---")
        vector_for_point_default_2 = np.random.rand(vector_size).tolist()
        points_default = [
            PointStruct(id=point_id_default_1, vector=np.random.rand(vector_size).tolist(), payload={"type": "default", "val": 1}),
            PointStruct(id=point_id_default_2, vector=vector_for_point_default_2, payload={"type": "default", "val": 2}),
        ]
        assert client.upsert_points(default_collection_name, points_default), "Upsert to default collection failed."
        print(f"✓ Points upserted to '{default_collection_name}'.")

        # To named vector collection
        print(f"\n--- 3B. Point Upsert (to '{named_collection_name}') ---")
        image_vector_data = np.random.rand(image_vec_size).tolist()
        text_vector_data = np.random.rand(text_vec_size).tolist()
        points_named = [
            PointStruct(id=point_id_named_1, vector={image_vec_name: image_vector_data, text_vec_name: text_vector_data}, payload={"type": "hybrid", "desc": "test item"})
        ]
        assert client.upsert_points(named_collection_name, points_named), "Upsert to named collection failed."
        print(f"✓ Points upserted to '{named_collection_name}'.")
        print("-" * 40)

        # Retrieve specific points 
        print(f"\n--- 4. Retrieve Specific Points ---")
        retrieved_default = client.retrieve_points(default_collection_name, [point_id_default_1])
        assert len(retrieved_default) == 1 and retrieved_default[0].id == point_id_default_1 and retrieved_default[0].payload.get("val") == 1, \
            f"Retrieval from default collection failed. Got: {retrieved_default}"
        print(f"✓ Point retrieved from '{default_collection_name}'.")
        
        retrieved_named = client.retrieve_points(named_collection_name, [point_id_named_1], with_vectors=[image_vec_name]) # Test retrieving a named vector
        assert len(retrieved_named) == 1 and retrieved_named[0].id == point_id_named_1 and retrieved_named[0].payload.get("type") == "hybrid", \
            f"Retrieval from named collection failed. Got: {retrieved_named}"
        assert retrieved_named[0].vector is not None and image_vec_name in retrieved_named[0].vector, f"Named vector '{image_vec_name}' not retrieved."
        print(f"✓ Point with named vector retrieved from '{named_collection_name}'.")
        print("-" * 40)

        # Update pauload 
        print(f"\n--- 5. Payload Update (in '{default_collection_name}') ---")
        new_payload = {"type": "default_updated", "val": 1, "status": "changed"}
        assert client.update_payload(default_collection_name, point_id_default_1, new_payload), "Update payload failed."
        retrieved_updated = client.retrieve_points(default_collection_name, [point_id_default_1])[0]
        assert retrieved_updated.payload == new_payload, "Payload content mismatch after update."
        print("✓ Payload update verified.")
        print("-" * 40)

        # Vector search 
        print(f"\n--- 6. Vector Search ---")
        # Simple search in default collection
        results_default_search = client.search(default_collection_name, vector_for_point_default_2, limit=1)
        assert len(results_default_search) == 1 and results_default_search[0].id == point_id_default_2 and results_default_search[0].score > 0.99, \
            f"Simple search failed. Got: {results_default_search}"
        print(f"✓ Simple search in '{default_collection_name}' successful.")

        # Search against named "image" vector in named collection
        query_named_image_vector = NamedVector(name=image_vec_name, vector=image_vector_data)
        results_named_search = client.search(named_collection_name, query_named_image_vector, limit=1)
        assert len(results_named_search) == 1 and results_named_search[0].id == point_id_named_1 and results_named_search[0].score > 0.99, \
             f"Search against named '{image_vec_name}' failed. Got: {results_named_search}" # DOT product score for identical vector
        print(f"✓ Search against named '{image_vec_name}' vector in '{named_collection_name}' successful.")
        print("-" * 40)

        # Delete points 
        print(f"\n--- 7. Delete Points (from '{default_collection_name}') ---")
        assert client.delete_points(default_collection_name, [point_id_default_1]), f"Delete operation for {point_id_default_1} failed."
        assert len(client.retrieve_points(default_collection_name, [point_id_default_1])) == 0, f"Point {point_id_default_1} not deleted."
        print(f"✓ Point {point_id_default_1} deleted and verified.")
        assert len(client.retrieve_points(default_collection_name, [point_id_default_2])) == 1, f"Point {point_id_default_2} was wrongly deleted."
        print(f"✓ Point {point_id_default_2} confirmed to exist.")
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
        # --- Cleanup: Delete All Test Collections ---
        print("\n--- 8. Cleanup: Delete Collections ---")
        if client: # Ensure client was initialized
            for coll_name in [default_collection_name, named_collection_name]:
                try:
                    if coll_name: # Ensure collection_name is not empty if a test failed early
                        print(f"Attempting to delete collection: '{coll_name}'...")
                        if client.delete_collection(coll_name):
                            print(f"✓ Collection '{coll_name}' successfully deleted.")
                        else:
                             # delete_collection in client now returns True/False based on Qdrant's response
                             print(f"✗ Deletion of collection '{coll_name}' reported False (may have already been deleted or failed).")
                except Exception as e:
                    print(f"✗ Exception during cleanup of collection '{coll_name}': {e}")
                
    print("\n=== Generic QdrantClient Test Suite Completed ===")

if __name__ == "__main__":
    try:
        test_qdrant_client()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


    
        
