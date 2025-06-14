export interface ApiVideoItem {
  filename: string;
  duration_seconds: number | null;
  fps: number | null;
  resolution_width: number | null;
  resolution_height: number | null;
  size_bytes: number | null;
  id: string;
  minio_video_url: string | null;
  minio_audio_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiVideosListResponse {
  videos: ApiVideoItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApiAssessVideoPayload {
  video_id: string; 
  rubric_question: string;
}

export interface AssessmentConfig {
  useAllTools: boolean;
  clipModel: string
  clapModel: string
  llmModel: string
  numKeyframes: number,
  videoKeyframeRetrievalConfThresh: number 
  audioSegmentRetrievalConfThresh: number  
}

export interface WorkflowStatus {
  planner: "pending" | "active" | "completed"
  executor: "pending" | "active" | "completed"
  scorer: "pending" | "active" | "completed"
  reflector: "pending" | "active" | "completed"
  consensus: "pending" | "active" | "completed"
}

export interface IndexedVideo {
  id: string
  name: string
  uploadDate: string
  duration?: string
  videoUrl: string | null
  audioUrl: string | null 
}

export interface ApiDeleteVideoResponse {
  status: boolean;
  message: string;
}

export interface ApiAssessVideoResponse {
  rubric_question: string
  video_id: string
  planner_output: string[]
  tools_used: string[]
  executor_output: {
    keyframe_captioner?: Array<{
      keyframe_id: string
      keyframe_image_url: string
      timestamp: number
      keyframe_description: string
    }>
    object_detector?: Array<{
      name: string
      context: string
      timestamp: number
      keyframe_id: string
      keyframe_image_url: string
      confidence_score: number
    }>
    pose_analyzer?: Array<{
      timestamp: number
      keyframe_id: string
      keyframe_image_url: string
      person_label: string
      pose: string
      gaze: string
    }>
    temporal_action_segmenter?: Array<{
      action_label: string
      start_time: number
      end_time: number
    }>
    scene_interaction_analyzer?: any
    audio_transcript_extractor?: Array<{
      start_time: number
      end_time: number
      audio_segment_id: string
      transcript: string
      audio_segment_url: string
    }>
  }
  scorer_output: {
    grade: number
    rationale: string
  }
  reflector_output: {
    flagged: boolean
    reasons: string[]
    needs_more_evidence: boolean
  }
}

export interface ToolOutput {
  [key: string]: any
}
