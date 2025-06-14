from typing import List

from google import genai 

from core.tools.base import Tool
from core.utils.gemini_utils import generate_text_content_with_gemini

class Planner:
    def __init__(
        self, 
        gemini_client: genai.Client, 
        tool_repository: List[Tool]
    ):
        self.gemini_client = gemini_client 
        self.tool_repository = tool_repository
        self.tool_map = {tool.TOOL_NAME: tool for tool in tool_repository} 

    def _format_tools_for_prompt(self) -> str:
        """
        Formats the tool repository into a string suitable for the LLM prompt.
        """
        formatted_tools = []
        for i, tool in enumerate(self.tool_repository):
            formatted_tools.append(
                f"{i+1}. Tool Name: {tool.name}\n"
                f"   Category: {tool.category.value}\n"
                f"   Description: {tool.description}"
            )
        return "\n\n".join(formatted_tools)
    
    def _format_tools_for_prompt(self) -> str:
        """
        Formats the tool repository into a string suitable for the LLM prompt.
        """
        formatted_tools = []
        for i, tool in enumerate(self.tool_repository):
            formatted_tools.append(
                f"{i+1}. Tool Name: {tool.TOOL_NAME}\n"
                f"   Category: {tool.TOOL_CATEGORY.value}\n"
                f"   Description: {tool.TOOL_DESCRIPTION}"
            )
        return "\n\n".join(formatted_tools)

    def _construct_prompt(self, rubric_question: str, formatted_tools: str) -> str:
        """Constructs the full prompt for the LLM."""
        prompt = f"""You are an expert AI assistant acting as the 'Planner' component in a multi-agent system for automated OSCE video assessment.
        This system follows a Planner-Executor-Scorer-Reflector pipeline. 
        Your specific role as the Planner is to analyze a given rubric question and select the most appropriate tools from a provided list. 
        The selected tools will then be used by the 'Executor' to gather evidence, which the 'Scorer' will use for grading, and the 'Reflector' will review.
        Your accurate tool selection is crucial for the downstream success of the entire assessment pipeline.
        
        Available Tools:
        {formatted_tools}

        Rubric Question: "{rubric_question}"

        Based on the rubric question, identify the tools that would be most effective for gathering relevant evidence for assessing the rubric question.
        Consider what type of information is needed to answer the rubric question and which tools provide that information.
        
        To help you, here are some guidelines and examples for tool selection:

        1.  **Communication Skills (Verbal):**
            - If the rubric question assesses what was said, the content of dialogue, specific phrases used, or general verbal communication between student and patient (e.g., "Did the student introduce themselves?", "Did the student explain the procedure clearly?", "Assess the student's empathy based on their words."), use the **audio_transcript_extractor**.

        2.  **Object Identification and Usage:**
            - If the rubric question is about identifying specific clinical tools or objects (e.g., "Did the student use a stethoscope?", "Was a pen torch present on the tray?"), use the **object_detector**.
            - If the question is about *how* the student interacted with an object or the patient (e.g., "Did the student correctly place the stethoscope on the patient's chest?", "Evaluate the student's handling of the otoscope."), use the **scene_interaction_analyzer**. You might also consider **object_detector** if simple presence is also key.

        3.  **Procedural Steps and Actions Over Time:**
            - If the rubric question assesses the sequence of actions, completion of procedural steps, or timing (e.g., "Did the student wash their hands before examining the patient?", "Assess the order of examination steps.", "How long did the student take for the cardiovascular exam?"), use the **temporal_action_segmenter**.
            - The **keyframe_captioner** can provide supplementary visual context for actions if a general description of key moments related to a procedure is needed.

        4.  **General Scene Understanding & Visual Context:**
            - If the rubric question requires a general understanding of what is visually happening in a scene without focusing on specific objects or interactions (e.g., "Describe the examination room setup.", "What was the general environment like?"), use the **keyframe_captioner**.

        5.  **Poses, Gaze, and Non-Verbal Communication:**
            - If the rubric question relates to the student's or patient's body language, posture, positioning, or eye contact (e.g., "Was the student positioned appropriately relative to the patient?", "Did the student maintain eye contact?", "Assess the student's professional demeanor based on posture."), use the **pose_analyzer**.

        6.  **Combined Evidence:**
            - Some rubric questions may benefit from multiple tools. For instance, assessing "effective communication during a physical examination step" might require **audio_transcript_extractor** (for verbal content) and **pose_analyzer** (for non-verbal cues) and potentially **scene_interaction_analyzer** (if the communication is about an interaction with an object/patient).
            - For a question like "Did the student demonstrate correct use of the reflex hammer and explain the action?", you might need **object_detector** (to confirm reflex hammer), **scene_interaction_analyzer** (for how it was used), and **audio_transcript_extractor** (for the explanation).

        The audio_transcript_extractor tool should be used when the rubric question requires understanding what was said, the content of dialogue, specific phrases used, or general verbal communication between student and patient.  
        The keyframe_captioner tool should be used when the rubric question requires a general understanding of what is visually happening in the keyframes. This tool should be returned if the rubric question requires visual context unless it is absolutely clear that it is not needed.

        Your goal is to select the best set of tools that can provide MAXIMUM relevant evidence for the given rubric question.

        Return your answer as a comma-separated list of tool names. For example: "tool_name_1", "tool_name_2".
        Do not include any additional text or explanations in your response.

        If you are unsure about which tools to select, consider the following:
        - What specific information is needed to answer the rubric question?
        - Which tools provide that information?
        - Are there any tools that can provide multiple types of information?
        - Are there any tools that can complement each other in providing a comprehensive answer?
        - Are there any tools that are redundant or unnecessary for this specific question?
        - Are there any tools that are not relevant to the rubric question?
        - Are there any tools that are essential for answering the rubric question?
        - Are there any tools that can provide a more complete or nuanced answer to the rubric question?

        Return at least one tool name, but do not return more than three tools unless absolutely necessary. 
        If you think multiple tools are necessary, include all of them in the list.
        Selected tool names MUST be from the 'Tool Name' list provided above. Do not invent new tool names."""

        return prompt 
    
    def run(self, rubric_question: str) -> List[Tool]:
        try: 
            if not self.tool_repository:
                raise ValueError("Tool repository is empty. Please provide at least one tool.")

            formatted_tools_string = self._format_tools_for_prompt()
            prompt = self._construct_prompt(
                rubric_question=rubric_question, 
                formatted_tools=formatted_tools_string
            )    

            response = generate_text_content_with_gemini(
                client=self.gemini_client, 
                prompt_text=prompt
            )

            if not response:
                raise ValueError("No response received from the LLM. Please check the prompt and try again.")
            
            tool_names = response.strip().split(",")
            selected_tools = []
            for tool_name in tool_names:
                tool_name = tool_name.strip().strip('"').strip("'")  # Clean up the tool name
                if tool_name in self.tool_map:
                    selected_tools.append(self.tool_map[tool_name])
                else:
                    print(f"Warning: Tool '{tool_name}' not found in the tool repository. Skipping.")

            if not selected_tools:
                raise ValueError("No valid tools selected. Please check the rubric question and the tool repository.")
            
            return selected_tools 

        except Exception as e: 
            print(f"An error occurred while running the Planner: {e}")
            return None 
        