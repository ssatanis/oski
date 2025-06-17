from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class RubricItem(BaseModel):
    """Individual assessment item within a rubric section"""
    item_id: str = Field(..., description="Unique identifier for the assessment item")
    description: str = Field(..., description="Description of what is being assessed")
    points: float = Field(..., ge=0, description="Point value for this item")
    criteria: Optional[str] = Field(None, description="Detailed criteria for assessment")
    
    @validator('item_id')
    def validate_item_id(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('item_id must be a non-empty string')
        # Ensure snake_case format
        if not v.replace('_', '').isalnum():
            raise ValueError('item_id should only contain alphanumeric characters and underscores')
        return v.lower()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('description must be at least 3 characters long')
        return v.strip()

class RubricSection(BaseModel):
    """A section or category within a rubric"""
    section_name: str = Field(..., description="Name of the rubric section")
    section_id: str = Field(..., description="Unique identifier for the section")
    description: Optional[str] = Field(None, description="Description of the section")
    items: List[RubricItem] = Field(..., min_items=1, description="List of assessment items in this section")
    
    @validator('section_id')
    def validate_section_id(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('section_id must be a non-empty string')
        # Ensure snake_case format
        if not v.replace('_', '').isalnum():
            raise ValueError('section_id should only contain alphanumeric characters and underscores')
        return v.lower()
    
    @validator('section_name')
    def validate_section_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('section_name must be at least 3 characters long')
        return v.strip()
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Each section must have at least one item')
        
        # Check for duplicate item_ids within the section
        item_ids = [item.item_id for item in v]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError('item_ids must be unique within a section')
        
        return v
    
    @property
    def total_points(self) -> float:
        """Calculate total points for this section"""
        return sum(item.points for item in self.items)

class RubricInfo(BaseModel):
    """General information about the rubric"""
    title: str = Field(..., description="Title of the rubric")
    total_points: Optional[float] = Field(None, ge=0, description="Total points for the entire rubric")
    description: Optional[str] = Field(None, description="Description of what the rubric assesses")
    subject: Optional[str] = Field(None, description="Subject or course this rubric is for")
    level: Optional[str] = Field(None, description="Academic level (e.g., undergraduate, graduate)")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('title must be at least 3 characters long')
        return v.strip()

class RubricPrompt(BaseModel):
    """Complete rubric prompt structure"""
    rubric_info: RubricInfo = Field(..., description="General rubric information")
    sections: List[RubricSection] = Field(..., min_items=1, description="List of rubric sections")
    
    @validator('sections')
    def validate_sections(cls, v):
        if not v:
            raise ValueError('Rubric must have at least one section')
        
        # Check for duplicate section_ids
        section_ids = [section.section_id for section in v]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError('section_ids must be unique across all sections')
        
        # Check for duplicate item_ids across all sections
        all_item_ids = []
        for section in v:
            all_item_ids.extend([item.item_id for item in section.items])
        
        if len(all_item_ids) != len(set(all_item_ids)):
            raise ValueError('item_ids must be unique across the entire rubric')
        
        return v
    
    @validator('rubric_info')
    def validate_total_points(cls, v, values):
        """Validate that total_points matches the sum of all item points"""
        if 'sections' in values and v.total_points is not None:
            calculated_total = sum(
                section.total_points for section in values['sections']
            )
            if abs(v.total_points - calculated_total) > 0.01:  # Allow for small floating point differences
                raise ValueError(f'total_points ({v.total_points}) does not match calculated total ({calculated_total})')
        return v
    
    @property
    def calculated_total_points(self) -> float:
        """Calculate total points from all sections"""
        return sum(section.total_points for section in self.sections)
    
    @property
    def total_items(self) -> int:
        """Count total number of assessment items"""
        return sum(len(section.items) for section in self.sections)
    
    def get_section_by_id(self, section_id: str) -> Optional[RubricSection]:
        """Get a section by its ID"""
        for section in self.sections:
            if section.section_id == section_id:
                return section
        return None
    
    def get_item_by_id(self, item_id: str) -> Optional[RubricItem]:
        """Get an item by its ID (searches all sections)"""
        for section in self.sections:
            for item in section.items:
                if item.item_id == item_id:
                    return item
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format suitable for YAML export"""
        return {
            "rubric_info": self.rubric_info.dict(exclude_none=True),
            "sections": [
                {
                    "section_name": section.section_name,
                    "section_id": section.section_id,
                    "description": section.description,
                    "items": [
                        {
                            "item_id": item.item_id,
                            "description": item.description,
                            "points": item.points,
                            "criteria": item.criteria
                        }
                        for item in section.items
                    ]
                }
                for section in self.sections
            ]
        }

# Additional models for API responses
class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    value: Any

class ValidationResult(BaseModel):
    """Result of YAML validation"""
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []
    parsed_rubric: Optional[RubricPrompt] = None

class ProcessingStep(BaseModel):
    """Individual step in the processing workflow"""
    step_name: str
    status: str  # pending, processing, completed, error
    message: str
    progress_percent: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_details: Optional[str] = None 