import type { AssessmentResults, ToolOutput } from "@/types/assessment"

export function generateMockResults(): { results: AssessmentResults; outputs: ToolOutput } {
  const results: AssessmentResults = {
    grade: 2,
    rationale:
      "The student demonstrated partial greeting behavior. They made eye contact and said 'Hello' but did not introduce themselves by name or explain their role, which are important components of a complete patient greeting.",
    audio_evidence: "Transcript: 'Hello, how are you feeling today?'",
    video_evidence: "Keyframe analysis shows student making eye contact and verbal interaction at timestamp 00:15",
    retrieved_audio_segments: ["Segment 1: 00:10-00:20", "Segment 2: 00:45-00:55"],
    retrieved_video_keyframes: ["Frame 1: 00:15", "Frame 2: 00:18", "Frame 3: 00:22"],
    reflector_output: {
      needs_human_review: true,
      confidence_score: 0.72,
      review_reasons: [
        "Ambiguous evidence for name introduction",
        "Low audio quality in greeting segment",
        "Partial occlusion during initial interaction",
      ],
      evidence_quality: "medium",
    },
  }

  const outputs: ToolOutput = {
    keyframe_retrieval: {
      retrieved_frames: 5,
      keyframes: [
        {
          id: "kf_001",
          timestamp: "00:15",
          similarity_score: 0.89,
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          id: "kf_002",
          timestamp: "00:18",
          similarity_score: 0.85,
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          id: "kf_003",
          timestamp: "00:22",
          similarity_score: 0.82,
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          id: "kf_004",
          timestamp: "00:35",
          similarity_score: 0.78,
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          id: "kf_005",
          timestamp: "00:42",
          similarity_score: 0.75,
          image_url: "/placeholder.svg?height=200&width=300",
        },
      ],
    },
    audio_retrieval: {
      retrieved_segments: 3,
      segments: [
        { timestamp: "00:10-00:20", similarity_score: 0.92, emotion: "Neutral", audio_url: "#" },
        { timestamp: "00:45-00:55", similarity_score: 0.87, emotion: "Happy", audio_url: "#" },
        { timestamp: "01:20-01:30", similarity_score: 0.81, emotion: "Sad", audio_url: "#" },
      ],
    },
    scene_captioner: {
      captions: [
        {
          caption: "A medical student in white coat standing beside patient bed",
          timestamp: "00:15",
          keyframe_id: "kf_001",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          caption: "Student making eye contact with elderly patient",
          timestamp: "00:18",
          keyframe_id: "kf_002",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          caption: "Student gesturing while speaking to patient",
          timestamp: "00:22",
          keyframe_id: "kf_003",
          image_url: "/placeholder.svg?height=200&width=300",
        },
      ],
    },
    object_detector: {
      identified_objects: [
        {
          name: "stethoscope",
          context_or_location: "around student's neck",
          timestamp: "00:15",
          confidence: 0.95,
          keyframe_id: "kf_001",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          name: "blood pressure cuff",
          context_or_location: "on patient's upper left arm, appears to be in use",
          timestamp: "00:18",
          confidence: 0.87,
          keyframe_id: "kf_002",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          name: "gloves",
          context_or_location: "worn on student's hands",
          timestamp: "00:22",
          confidence: 0.92,
          keyframe_id: "kf_003",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          name: "sharps container",
          context_or_location: "on the medical cart to the student's right, lid open",
          timestamp: "00:35",
          confidence: 0.89,
          keyframe_id: "kf_004",
          image_url: "/placeholder.svg?height=200&width=300",
        },
      ],
      summary:
        "Student is wearing gloves and has a stethoscope. A blood pressure cuff is actively being used on the patient's arm. A sharps container is accessible.",
    },
    object_interaction_analyzer: {
      scene_interactions: [
        {
          subject_label: "student",
          action_predicate: "applying",
          object_target_label: "blood pressure cuff",
          target_detail: "to patient's upper left arm",
          timestamp: "00:18",
          confidence: 0.91,
          keyframe_id: "kf_002",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          subject_label: "student",
          action_predicate: "speaking_to",
          object_target_label: "patient",
          target_detail: "while facing them",
          timestamp: "00:22",
          confidence: 0.88,
          keyframe_id: "kf_003",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          subject_label: "blood pressure cuff",
          action_predicate: "is_on",
          object_target_label: "patient's upper left arm",
          target_detail: null,
          timestamp: "00:25",
          confidence: 0.94,
          keyframe_id: "kf_004",
          image_url: "/placeholder.svg?height=200&width=300",
        },
      ],
      summary:
        "The student is applying a blood pressure cuff to the patient's arm and appears to be communicating with them during the procedure.",
    },
    pose_analyzer: {
      detected_poses: [
        {
          person_label: "student",
          key_action_or_posture:
            "leaning towards the patient who is lying flat on their back in bed, right hand holding a syringe near the patient's left arm, left hand steadying the patient's arm.",
          gaze_direction: "focused on the injection site",
          timestamp: "00:35",
          confidence: 0.89,
          keyframe_id: "kf_004",
          image_url: "/placeholder.svg?height=200&width=300",
        },
        {
          person_label: "patient",
          key_action_or_posture: "lying flat on their back, left arm out, looking at the student.",
          gaze_direction: "towards student",
          timestamp: "00:35",
          confidence: 0.92,
          keyframe_id: "kf_004",
          image_url: "/placeholder.svg?height=200&width=300",
        },
      ],
      summary:
        "The student appears to be giving an injection in the patient's left arm, and both are focused on this action.",
    },
    transcriber: {
      transcripts: [
        {
          text: "STUDENT: Hello, how are you feeling today?\nPATIENT: I'm feeling a bit nervous about this examination.",
          timestamp: "00:10-00:20",
          segment_id: "audio_001",
        },
        {
          text: "STUDENT: I'm going to take your blood pressure now. Please relax your arm.\nPATIENT: Okay, thank you for letting me know.",
          timestamp: "00:45-00:55",
          segment_id: "audio_002",
        },
        {
          text: "STUDENT: Please let me know if you feel any discomfort during this procedure.\nPATIENT: I will, thank you doctor.",
          timestamp: "01:20-01:30",
          segment_id: "audio_003",
        },
      ],
    },
    temporal_segmentation: {
      action_segments: [
        { start: "00:10", end: "00:25", action: "greeting_interaction" },
        { start: "00:30", end: "00:50", action: "examination_preparation" },
        { start: "00:55", end: "01:15", action: "physical_examination" },
      ],
    },
  }

  return { results, outputs }
}
