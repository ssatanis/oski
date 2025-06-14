import uuid 
from typing import Optional, Dict, Any, Generic

import numpy as np 
from typing import List, Dict, Any, Optional, TypeVar 
from pydantic import BaseModel, Field 
from dataclasses import dataclass 

MetadataType = TypeVar("MetadataType")

class SearchResult(BaseModel, Generic[MetadataType]):
    """A generic schema representing a single search result from Qdrant."""
    id: uuid.UUID | str = Field(description="The unique ID of the point.")
    score: float = Field(description="The similarity score or -1.0 for retrieved points.")
    version: Optional[int] = Field(default=None, description="The version of the point.")
    metadata: MetadataType = Field(description="The validated metadata payload.")