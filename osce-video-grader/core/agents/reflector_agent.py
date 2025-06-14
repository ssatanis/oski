import json 
import traceback 
from typing import List, Optional, Dict, Any  

from google import genai 
from pydantic import BaseModel, Field

from core.tools.base import Tool, ToolCategory
from core.utils.gemini_utils import generate_text_content_with_gemini
from core.agents.scorer_agent import Scorer 

class ReflectorOutput(BaseModel):
    flagged: bool
    reasons: List[str] = Field(default_factory=list)
    needs_more_evidence: bool
            
class Reflector:
    # Scorer's SCORING_CRITERIA can be useful for the Reflector's LLM too
    SCORING_CRITERIA_FOR_CONTEXT = Scorer.SCORING_CRITERIA

    def __init__(
            self,
            gemini_client: genai.Client,
            scorer_formatter_func: callable
        ):
        self.gemini_client = gemini_client 
        # Pass the Scorer's evidence formatter to reuse the same evidence representation
        self.format_evidence_for_prompt = scorer_formatter_func 

    def _construct_prompt(
        self,
        rubric_question: str,
        formatted_evidence: str,
        scorer_grade: int,
        scorer_rationale: str
    ) -> str:
        prompt = f"""
        You are an AI assistant acting as the 'Reflector' in a Planner-Executor-Scorer-Reflector multi-agent system for automated OSCE video assessment.
        Your role is to critically review the 'Scorer's' assessment of a student's performance. The Scorer was given a rubric question and evidence from automated tools.

        Your Task:
        1.  Review the `Rubric Question`.
        2.  Review the `Evidence from Automated Analysis Tools` that the Scorer used.
        3.  Review the `Scorer's Grade` and `Scorer's Rationale`.
        4.  Critically evaluate if the Scorer's grade and rationale are well-supported by the provided evidence and align with the `Scoring Criteria Context`.
        5.  Determine if the assessment should be flagged for human review.

        Chain of Thought for Reflection:
        1.  **Understand Scorer's Conclusion:** What grade did the Scorer assign and what were their main justifications (rationale)?
        2.  **Cross-Reference with Evidence:**
            *   Does the Scorer's rationale accurately cite the evidence? (e.g., if rationale mentions an audio transcript at 10s, is there such a transcript in the evidence?)
            *   Are there any contradictions between the rationale and the evidence? (e.g., rationale says "no object used" but evidence shows object detection).
            *   Did the Scorer ignore any significant pieces of evidence that might change the grade?
        3.  **Assess Justification Strength:**
            *   Is the assigned grade adequately justified by the cited evidence in the rationale?
            *   Does the rationale logically lead to the grade based on the scoring criteria?
            *   Is the evidence strong enough for the assigned grade? (e.g., a high grade of 5 should be backed by very strong, multifaceted evidence).
        4.  **Consider Evidence Sufficiency:**
            *   Was the overall evidence (from all tools) sufficient for a confident assessment of the rubric question?
            *   If the evidence was sparse, or key tools failed or found nothing, did the Scorer appropriately acknowledge this and assign a cautious grade?
        5.  **Decision - Flagging:**
            *   If there are significant inconsistencies, unsupported claims in the rationale, a grade that seems too high/low for the evidence, or very weak evidence for a definitive score, then set `flagged` to `true`.
            *   Otherwise, set `flagged` to `false`.
        6.  **Decision - Reasons (if flagged):**
            *   If `flagged` is `true`, provide up to three concise bullet-point reasons. Reasons should be specific, e.g.:
                *   "Scorer's rationale claims student explained X, but no such explanation is found in the audio transcripts around the specified timestamps."
                *   "A grade of 4 ('Very Good') was given, but the evidence only shows a single, brief audio segment and no visual confirmation of the primary action."
                *   "Object detector evidence showing 'stethoscope in use' contradicts the Scorer's statement that the tool was not used."
        7.  **Decision - Needs More Evidence:**
            *   Set `needs_more_evidence` to `true` if you believe the original set of evidence provided to the Scorer was fundamentally insufficient to answer the rubric question robustly, regardless of how well the Scorer interpreted it. This implies the Planner/Executor might need to gather more or different types of evidence in a future iteration or for human review.
            *   Set `needs_more_evidence` to `false` if the evidence seemed adequate, even if the Scorer's interpretation was flawed.

        Rubric Question:
        "{rubric_question}"

        Evidence from Automated Analysis Tools (same as Scorer saw):
        --- BEGIN EVIDENCE ---
        {formatted_evidence}
        --- END EVIDENCE ---

        Scorer's Assessment:
        Grade: {scorer_grade}
        Rationale: "{scorer_rationale}"

        Scoring Criteria Context (for your reference):
        {self.SCORING_CRITERIA_FOR_CONTEXT}

        Output Format Instructions:
        You MUST return your response as a single, valid JSON object.
        The JSON object must have the following keys:
        1.  `flagged`: boolean (true if the Scorer's assessment should be flagged for human review, false otherwise).
        2.  `reasons`: A list of strings. If `flagged` is true, provide 1 to 3 bullet-point style reasons. If `flagged` is false, this should be an empty list.
        3.  `needs_more_evidence`: boolean (true if the original evidence itself was insufficient for a robust assessment, false otherwise).

        Example of a valid JSON output if flagged:
        {{
            "flagged": true,
            "reasons": [
                "The Scorer assigned a grade of 5 (Outstanding) but the rationale primarily relies on a single keyframe caption, which is insufficient for such a high grade.",
                "Audio transcript evidence mentioned in the rationale (around 45s) does not appear in the provided evidence logs.",
                "The rationale overlooks contradictory evidence from the pose_analyzer suggesting the student was not facing the patient during a critical communication phase."
            ],
            "needs_more_evidence": true
        }}

        Example of a valid JSON output if not flagged:
        {{
            "flagged": false,
            "reasons": [],
            "needs_more_evidence": false
        }}

        You MUST return only the JSON object. Do not return any additional explanation or text other than the JSON output.
        """
        
        return prompt

    def run(
        self,
        rubric_question: str,
        evidence_from_executor: Dict[str, List[Dict[str, Any]]], # Using the new structure
        scorer_output: Dict[str, str]
    ) -> Optional[ReflectorOutput]:

        formatted_evidence = self.format_evidence_for_prompt(evidence_from_executor)
        
        prompt = self._construct_prompt(
            rubric_question=rubric_question,
            formatted_evidence=formatted_evidence,
            scorer_grade=scorer_output["grade"],
            scorer_rationale=scorer_output["rationale"]
        )

        try:
            response_str = generate_text_content_with_gemini(
                client=self.gemini_client, 
                prompt_text=prompt 
            )

            if response_str.strip().startswith("```json"):
                response_str = response_str.strip()[7:-3].strip()
            elif response_str.strip().startswith("```"):
                 response_str = response_str.strip()[3:-3].strip()
            
            response_json = json.loads(response_str)
            
            # Ensure 'reasons' is a list even if LLM omits it when flagged=false
            if 'reasons' not in response_json:
                response_json['reasons'] = []
            if not isinstance(response_json.get('reasons'), list):
                 response_json['reasons'] = [str(response_json.get('reasons'))] # Coerce if not list

            reflector_output_obj = ReflectorOutput(**response_json)
            reflector_output_dict = reflector_output_obj.model_dump()

            return reflector_output_dict

        except json.JSONDecodeError:
            print(f"Error: Reflector LLM did not return valid JSON. Response: >>>{response_str}<<<")
            return None
        
        except Exception as e: # Catches Pydantic validation errors and other issues
            print(f"An error occurred during Reflector LLM call or parsing/validation: {e}")
            import traceback
            traceback.print_exc()
            return None