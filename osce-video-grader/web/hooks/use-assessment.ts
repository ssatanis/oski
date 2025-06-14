"use client"

import { useCallback, useState } from "react"
import type { WorkflowStatus, ApiAssessVideoResponse, AssessmentConfig, ApiAssessVideoPayload } from "@/types/assessment"
import { useMutation } from "@tanstack/react-query";
import { assessVideo } from "@/services/api";

// Updated mock API response based on the provided JSON
const MOCK_API_RESPONSE: ApiAssessVideoResponse = {
  rubric_question: "Did the student use a stethoscope?",
  video_id: "46dc4868-15e9-4f27-b277-726bf9f0023c",
  planner_output: ["object_detector"],
  tools_used: [
    "keyframe_captioner",
    "object_detector",
    "pose_analyzer",
    "temporal_action_segmenter",
    "scene_interaction_analyzer",
    "audio_transcript_extractor",
  ],
  executor_output: {
    keyframe_captioner: [
      {
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        timestamp: 198.0,
        keyframe_description:
          "A student is using a stethoscope to auscultate the blood pressure of a patient lying on an examination bed, with a blood pressure cuff on the patient's arm. A table with medical equipment is visible in the background.",
      },
      {
        keyframe_id: "52046146-1d71-472d-9480-238a694d2a87",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        timestamp: 180.0,
        keyframe_description:
          "A student is using a stethoscope and sphygmomanometer to measure the blood pressure of a patient who is sitting in a chair. The student is leaning over the patient and looking at the sphygmomanometer.",
      },
      {
        keyframe_id: "2dfb3846-7428-47f0-a0f6-a712656a5e15",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        timestamp: 189.0,
        keyframe_description:
          "A student is using a stethoscope and a blood pressure monitor to measure the blood pressure of a patient lying on an examination bed. A small table with medical supplies is visible in the background.",
      },
    ],
    object_detector: [
      {
        name: "stethoscope",
        context: "being used by the student on the patient's arm",
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        confidence_score: 0.95,
      },
      {
        name: "blood pressure cuff",
        context: "on the patient's left arm",
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        confidence_score: 0.95,
      },
      {
        name: "stethoscope",
        context: "around student's neck and being used on patient's arm",
        timestamp: 180.0,
        keyframe_id: "52046146-1d71-472d-9480-238a694d2a87",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        confidence_score: 0.95,
      },
    ],
    pose_analyzer: [
      {
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        person_label: "student",
        pose: "leaning forward, holding a stethoscope to the patient's arm, listening for blood pressure.",
        gaze: "focused on the patient's arm",
      },
      {
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
        person_label: "patient",
        pose: "reclining on the examination table, arm extended for blood pressure measurement.",
        gaze: "towards student",
      },
    ],
    temporal_action_segmenter: [
      { action_label: "explaining_procedure", start_time: 0.0, end_time: 14.61 },
      { action_label: "history_taking", start_time: 12.61, end_time: 27.21 },
      { action_label: "hand_hygiene", start_time: 25.21, end_time: 39.82 },
      { action_label: "applying_blood_pressure_cuff", start_time: 138.67, end_time: 153.28 },
      { action_label: "using_sphygmomanometer", start_time: 151.28, end_time: 165.88 },
    ],
    scene_interaction_analyzer: [
      {
        subject_label: "student",
        action_predicate: "using",
        object_target_label: "stethoscope",
        target_detail: "to listen to patient's arm",
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
      },
      {
        subject_label: "stethoscope",
        action_predicate: "is_on",
        object_target_label: "patient's arm",
        target_detail: null,
        timestamp: 198.0,
        keyframe_id: "988fd36d-78d2-420d-ac2c-d6932b7046a1",
        keyframe_image_url: "/placeholder.svg?height=200&width=300",
      },
    ],
    audio_transcript_extractor: [
      {
        start_time: 164.9,
        end_time: 167.26,
        audio_segment_id: "912fe336-b29f-47c8-aeb9-56bbbc5e47f1",
        transcript: "UNKNOWN: Okay,\nSTUDENT: so we're just going to do that again with the stethoscope.",
        audio_segment_url: "#",
      },
      {
        start_time: 130.5,
        end_time: 137.02,
        audio_segment_id: "332298c6-63a7-4a93-87d1-a7e0aa375370",
        transcript:
          "UNKNOWN: So\nSTUDENT: we're going to do this twice. We're going to do it once without the stethoscope and then once with. So just checking the size.",
        audio_segment_url: "#",
      },
    ],
  },
  scorer_output: {
    grade: 5,
    rationale:
      "The student clearly used a stethoscope during the examination. Keyframe captions at 180.0s, 189.0s, and 198.0s all describe the student using a stethoscope. Object detection at 198.0s confirms the presence of a stethoscope with high confidence (0.95) and its use on the patient's arm. Pose analysis at 180.0s, 189.0s, and 198.0s further supports this, detailing the student's posture and interaction with the stethoscope. Scene interaction analysis at 180.0s and 198.0s explicitly states the student was 'using' the stethoscope. The audio transcript from 164.9s to 167.26s also mentions using the stethoscope again.",
  },
  reflector_output: {
    flagged: false,
    reasons: [],
    needs_more_evidence: false,
  },
}

// export function useAssessment() {
//   const [isAssessing, setIsAssessing] = useState(false)
//   const [assessmentProgress, setAssessmentProgress] = useState(0)
//   const [assessmentResults, setAssessmentResults] = useState<AssessmentResults | null>(null)
//   const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>({
//     planner: "pending",
//     executor: "pending",
//     scorer: "pending",
//     reflector: "pending",
//     consensus: "pending",
//   })

//   const startAssessment = async (videoId: string, rubricQuestion: string) => {
//     if (!videoId || !rubricQuestion) return

//     setIsAssessing(true)
//     setAssessmentProgress(0)

//     const steps: (keyof WorkflowStatus)[] = ["planner", "executor", "scorer", "reflector", "consensus"]

//     for (let i = 0; i < steps.length; i++) {
//       const step = steps[i]
//       setWorkflowStatus((prev) => ({ ...prev, [step]: "active" }))

//       // Simulate processing time
//       await new Promise((resolve) => setTimeout(resolve, 1500))

//       setWorkflowStatus((prev) => ({ ...prev, [step]: "completed" }))
//       setAssessmentProgress(((i + 1) / steps.length) * 100)
//     }

//     // Use mock API response
//     setAssessmentResults(MOCK_API_RESPONSE)
//     setIsAssessing(false)
//   }

//   const resetAssessment = () => {
//     setAssessmentResults(null)
//     setWorkflowStatus({
//       planner: "pending",
//       executor: "pending",
//       scorer: "pending",
//       reflector: "pending",
//       consensus: "pending",
//     })
//     setAssessmentProgress(0)
//   }

//   return {
//     isAssessing,
//     assessmentProgress,
//     assessmentResults,
//     workflowStatus,
//     startAssessment,
//     resetAssessment,
//   }
// }

const initialWorkflowStatus: WorkflowStatus = {
  planner: "pending",
  executor: "pending",
  scorer: "pending",
  reflector: "pending",
  consensus: "pending",
};

interface AssessVideoInput {
  payload: ApiAssessVideoPayload 
  config: AssessmentConfig 
}

export function useAssessVideoMutation() {
  const [currentWorkflowStatus, setCurrentWorkflowStatus] = useState<WorkflowStatus>(initialWorkflowStatus);
  const [assessmentProgress, setAssessmentProgress] = useState(0)

  const mutation = useMutation<ApiAssessVideoResponse, Error, AssessVideoInput>({
    mutationFn: async (variables) => {
      const { payload, config } = variables;
      const useAllToolsFlag = config.useAllTools || false; 

      setCurrentWorkflowStatus(initialWorkflowStatus)
      setAssessmentProgress(0)

      const steps: (keyof WorkflowStatus)[] = [
        "planner", 
        "executor",
        "scorer", 
        "reflector"
      ]
      let currentProgress = 0; 
      const progressIncrement = 100 / steps.length

      const updateStep = (stepKey: keyof WorkflowStatus, status: "active" | "completed") => {
        setCurrentWorkflowStatus((prev) => ({
          ...prev, 
          [stepKey]: status 
        }))

        if (status === "active" && stepKey == "planner") {
          currentProgress = 0;
        }

        if (status == "completed") {
          const completedStepIndex = steps.indexOf(stepKey)
          currentProgress = ((completedStepIndex + 1) * progressIncrement)
        } else if (status == "active") {
          const activeStepIndex = steps.indexOf(stepKey);
          currentProgress = (activeStepIndex * progressIncrement) + (progressIncrement / 2)
        }

        setAssessmentProgress(Math.min(currentProgress, 99));
      }

      updateStep("planner", "active")

      const results = await assessVideo(payload, useAllToolsFlag)

      updateStep("planner", "completed")
      updateStep("executor", "completed")
      updateStep("scorer", "completed")
      updateStep("reflector", "completed")

      setCurrentWorkflowStatus((prev) => ({ ...prev, consensus: "completed" }))
      setAssessmentProgress(100);

      return results; 
    }, 
    onSuccess: (data) => {
      console.log("Assessment successful:", data)
    }, 
    onError: (error) => {
      console.error("Assessment error: ", error)
      setCurrentWorkflowStatus(initialWorkflowStatus)
      setAssessmentProgress(0)
    }
  })

  const resetAssessment = useCallback(() => {
    mutation.reset();
    setCurrentWorkflowStatus(initialWorkflowStatus);
    setAssessmentProgress(0);
  }, [mutation])

  return {
    assessVideo: mutation.mutate, 
    assessmentResults: mutation.data, 
    isAssessing: mutation.isPending, 
    assessmentError: mutation.error, 
    workflowStatus: currentWorkflowStatus, 
    assessmentProgress, 
    resetAssessment: resetAssessment
  }
}