from enum import Enum 
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional 

class ToolCategory(Enum):
    VISUAL = "visual"
    AUDIO = "audio"
    TEMPORAL = "temporal"

class Tool(ABC):
    """
    Abstract base class for tools.
    All tools should inherit from this class and implement the `run` method.
    """
    TOOL_NAME: str 
    TOOL_CATEGORY: ToolCategory
    TOOL_DESCRIPTION: str

    def __init__(
        self, 
        name: str, 
        category: str,
        description: Optional[str] = None  
    ):
        self.name = name 
        self.category = category 
        self.description = description 

    @abstractmethod 
    def run(self, *args, **kwargs) -> Any: 
        pass 

    def metadata(self) -> Dict[str, str]:
        """
        Returns metadata about the tool.
        This can include name, category, description, etc.
        """
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description or ""
        }
        