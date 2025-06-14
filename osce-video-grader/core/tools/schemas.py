from typing import Optional, List

from pydantic import BaseModel, Field

# Schemas 
class KeyframeDescriptionOutput(BaseModel):
    description: str = Field(..., description="A concise and semantically rich description of the keyframe.")

class DetectedPose(BaseModel):
    person_label: str = Field(
        ...,
        description="Label for the person (e.g., 'student', 'patient')."
    )
    pose: str = Field(
        ...,
        description="The most significant action or posture of the person."
    )
    gaze_direction: Optional[str] = Field(
        None,
        description="Approximate gaze direction, if discernible."
    )

class PoseAnalysisOutput(BaseModel):
    detected_poses: List[DetectedPose] = Field(
        ...,
        description="List of per-person pose analyses."
    )
    summary: str = Field(
        ...,
        description="Brief summary of the collective posture and activity."
    )

class IdentifiedObject(BaseModel):
    name: str = Field(
        ...,
        description="Specific name of the identified clinical object e.g. stethoscope, thermometer, otoscope, etc."
    )
    context_or_location: str = Field(
        ...,
        description="Immediate usage context or location of the object."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score for the identification of the clinical object, between 0 and 1."
    )

class ObjectDetectionOutput(BaseModel):
    identified_objects: List[IdentifiedObject] = Field(
        ...,
        description="List of detected objects with context."
    )
    summary: str = Field(
        ...,
        description="Concise summary of the key objects present or absent."
    )

class ObjectInteraction(BaseModel):
    subject_label: str = Field(
        ...,
        description="Label of the entity performing the action."
    )
    action_predicate: str = Field(
        ...,
        description="The verb or relationship describing the interaction."
    )
    object_target_label: str = Field(
        ...,
        description="Label of the object or entity being acted upon."
    )
    target_detail: Optional[str] = Field(
        None,
        description="Additional detail about the target (e.g., 'to patient's left arm')."
    )

class SceneInteractionOutput(BaseModel):
    object_interactions: List[ObjectInteraction] = Field(
        ...,
        description="List of interaction triples describing the scene."
    )
    summary: str = Field(
        ...,
        description="Summary of the primary interaction in the scene."
    )