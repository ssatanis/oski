OSCE_KEYFRAME_CAPTIONER_PROMPT = """
This image is a keyframe from a video of a clinical skills assessment (OSCE).
Your goal is to generate a CONCISE yet SEMANTICALLY RICH description of this specific moment.
This description will be embedded and used to retrieve relevant keyframes based on textual rubric questions.
Focus on the primary action, the main individuals involved (e.g., student, patient), and any critical objects or their interactions directly relevant to a clinical assessment.
Avoid unnecessary details or speculation. The description should capture the core event.

**YOUR TASK**:
1. Identify the primary subject(s) and their roles if clear (e.g., "student," "patient"). The only possible roles are "student" or "patient".
2. Identify the most significant action or interaction taking place.
3. Note any critical medical objects directly involved in that action.
4. If the image shows a clinical object or tool being used, state its name and how it is being used (e.g., "holding a stethoscope to the patient's chest," "writing on a patient chart").
5. Note any other commonly present objects in OSCE examination settings (e.g., hand wash station, gloves box, waste bin) **if they are clearly visible** and their usage context, even if they are not directly involved in the clinical action.
6. If the image shows a patient, describe their position or condition relevant to the action (e.g., "patient lying on an examination bed," "patient sitting in a chair").
7. If the image shows a student, describe their position or action relevant to the interaction (e.g., "student standing beside the patient," "student leaning over the patient").
8. If a specific clinical procedure or interaction is evident, include that in the description.
9. Ensure the description is concise, focusing on the core event without extraneous details.
10. Formulate a single, concise sentence or two sentences summarizing this core event. 

**OUTPUT FORMAT:**:

Strictly output your final answer as a single JSON object with one key: 'description'.

Format:
{json_format_str}

Example:
{{
  "description": "A student is applying a blood pressure cuff to a patient lying on an examination bed, while holding a stethoscope in their right hand and looking at the patient's face. The patient appears calm and is looking at the student."
}}
"""

OSCE_KEYFRAME_POSE_ANALYZER_PROMPT = """
This image is a keyframe from a video recording of a clinical skills assessment (OSCE).
Your goal is to meticulously analyze and describe the body positions and significant actions of all primary individuals visible.
This information will be used as direct, structured evidence for assessing a student's clinical performance against a rubric. 
Focus on details that indicate clinical actions, patient interaction, and professional conduct.

**YOUR TASK:**
1.  For each clearly identifiable primary person in the image:
    a.  Assign a 'person_label' (e.g., "student", "patient", or "unknown" if role is ambiguous).
    b.  Describe their 'key_action_or_posture' in detail. This should include their overall body position 
        (e.g., "standing straight," "leaning forward over the bed," "sitting on a chair," "lying flat on their back," "lying on their side"), 
        specific limb positions if they are critical to an action (e.g., "right arm stretched out towards the patient's stomach," "both hands working with an object"), 
        and any tool interaction related to their pose (e.g., "holding a pen and writing," "placing an instrument near the patient's ear").
    c.  If discernible and clinically relevant, note their 'gaze_direction' (e.g., "looking at the patient's face," "focused on a medical chart," "looking at a piece of equipment").

2.  After analyzing all individuals, provide an 'summary'. This summary should concisely describe the main activity or interaction suggested by the observed body positions and actions from a clinical assessment viewpoint.

**OUTPUT FORMAT:**:
Strictly output your final answer as a single JSON object. Do not include any explanations or conversational text outside of this JSON structure.

Format:
{json_format_str}

Example:
```json
{{
  "detected_poses": [
    {{
      "person_label": "student",
      "pose": "leaning towards the patient who is lying flat on their back in bed, right hand holding a syringe near the patient's left arm, left hand steadying the patient's arm.",
      "gaze_direction": "focused on the injection site"
    }},
    {{
      "person_label": "patient",
      "pose": "lying flat on their back, left arm out, looking at the student.",
      "gaze_direction": "towards student"
    }}
  ],
  "summary": "The student appears to be giving an injection in the patient's left arm, and both are focused on this action."
}}
```
"""

OSCE_KEYFRAME_OBJECT_DETECTOR_PROMPT = """
This image is a keyframe from a video recording of a clinical skills assessment (OSCE).
Your task is to identify all relevant medical instruments, tools, equipment, Personal Protective Equipment (PPE like gloves, masks), and any other significant medical objects visible in the scene.
This information will be used as direct, structured evidence for assessing a student's clinical performance against a rubric. 
Focus on objects that are actively used, about to be used, or whose presence or absence is clinically significant.

**YOUR TASK:**
1.  Scan the entire image for objects or tools relevant to a clinical setting or procedure.
2.  For each clearly identifiable relevant object:
    a.  Provide its common 'object_name' (e.g., "syringe," "stethoscope," "patient chart," "gloves," "hand sanitizer bottle"). 
        Be as specific as the image allows (e.g., "temporal thermometer" instead of just "device" if clear).
    b.  Briefly describe its 'context_or_location'. This should include its position relative to people or other key items, 
        or how it's being interacted with (e.g., "held in student's right hand," "on the bedside table," "worn by the student," "on a sterile drape," "absent from view").
    c.  Assign a 'confidence_score' between 0 and 1 indicating your confidence in the identification based on visual clarity and context (e.g., 0.85 for high confidence, 0.60 for moderate confidence).
3.  Focus on the most clinically relevant objects depicted in the image.
4.  After identifying all key objects, formulate a brief 'summary' highlighting the most important items and their general relevance.

**OUTPUT FORMAT:**:
Strictly output your final answer as a single JSON object. Do not include any explanations or conversational text outside of this JSON structure.

Format:
{json_format_str}

Example:
```json
{{
  "identified_objects": [
    {{"name": "stethoscope", "context_or_location": "around student's neck", "confidence_score": 0.85}},
    {{"name": "blood pressure cuff", "context_or_location": "on patient's upper left arm, appears to be in use", "confidence_score": 0.62}},
    {{"name": "gloves", "context_or_location": "worn on student's hands", "confidence_score": 0.90}},
    {{"name": "sharps container", "context_or_location": "on the medical cart to the student's right, lid open", "confidence_score": 0.85}}
  ],
  "summary": "Student is wearing gloves and has a stethoscope. A blood pressure cuff is actively being used on the patient's arm. A sharps container is accessible."
}}
```
"""

OSCE_KEYFRAME_SCENE_INTERACTION_ANALYZER_PROMPT = """
This image is a keyframe from a video recording of a clinical skills assessment (OSCE).
Your task is to identify and describe the key interactions between people (e.g., 'student', 'patient') and important objects/equipment, as well as interactions between other important entities. 
This information will be used as direct, structured evidence for assessing a student's clinical performance.

**YOUR TASK:**
1.  Identify the primary entities (people like "student", "patient"; and key objects like "thermometer", "syringe", "chart") involved in interactions.
2.  For each significant interaction, describe it using these components:
    a.  'subject_label': The person or object performing the action or in a state.
    b.  'action_predicate': The verb or phrase describing the action or relationship 
        (e.g., "using," "holding," "pointing at," "talking to," "is touching," "is placed on," "looking at").
    c.  'object_target_label': The person, object, or general area receiving the action or related to the subject.
    d.  'target_detail' (optional): Provide more specific context about the target or manner of interaction if visually apparent 
        (e.g., "patient's forehead," "left arm," "carefully," "while explaining"). Use null if not applicable.
3.  Focus on 2-4 of the most clinically relevant interactions depicted.
4.  After identifying these interactions, formulate a brief 'summary' that captures the primary event or purpose of the interactions in the scene.

**OUTPUT FORMAT:**
Strictly output your final answer as a single JSON object. Do not include any explanations or conversational text outside of this JSON structure.

Format:
{json_format_str}

Example:
```json
{{
  "scene_interactions": [
    {{"subject_label": "student", "action_predicate": "applying", "object_target_label": "blood pressure cuff", "target_detail": "to patient's upper left arm"}},
    {{"subject_label": "student", "action_predicate": "speaking_to", "object_target_label": "patient", "target_detail": "while facing them"}},
    {{"subject_label": "blood pressure cuff", "action_predicate": "is_on", "object_target_label": "patient's upper left arm", "target_detail": null}},
    {{"subject_label": "patient", "action_predicate": "listening_to", "object_target_label": "student", "target_detail": null}}
  ],
  "summary": "The student is applying a blood pressure cuff to the patient's arm and appears to be communicating with them during the procedure."
}}
```
"""