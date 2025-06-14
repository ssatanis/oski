"use client"

import { useMemo, useRef, useState } from "react"
import { Video } from "lucide-react"
import { ConfigurationSidebar } from "./configuration-sidebar"
import { MainContent } from "./main-content"
import { useAssessVideoMutation } from "@/hooks/use-assessment"
import { useVideoUpload } from "@/hooks/use-video-upload"
import type { ApiVideoItem, AssessmentConfig, IndexedVideo } from "@/types/assessment"
import { useGetIndexedVideos, useUploadAndIndexVideoMutation } from "@/hooks/use-videos"

export function OSCEAssessmentSystem() {
  const videoFileInputRef = useRef<HTMLInputElement>(null)

  const [config, setConfig] = useState<AssessmentConfig>({
    useAllTools: true,
    clipModel: "ViT-B/32",
    clapModel: "CLAP-base",
    llmModel: "GPT-4",
    numKeyframes: 50,
    videoKeyframeRetrievalConfThresh: 0.6,
    audioSegmentRetrievalConfThresh: 0.6,
  })

  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null)
  const [rubricQuestion, setRubricQuestion] = useState<string>("Did the student use the stethoscope?")
  const [isIndexing, setIsIndexing] = useState(false)
  const [indexingProgress, setIndexingProgress] = useState(0)
  const [hasStartedAssessment, setHasStartedAssessment] = useState(false)

  const { 
    uploadedVideo, 
    handleVideoUpload,
    clearVideo,
    objectUrl: videoPreviewUrl 
  } = useVideoUpload(videoFileInputRef)
  const { 
    isAssessing,
    assessmentProgress,
    assessmentResults,
    workflowStatus,
    assessVideo, 
    resetAssessment
  } = useAssessVideoMutation()

  const { data: apiVideosData, isLoading: isLoadingVideos, error: videosError } = useGetIndexedVideos();
  const uploadAndIndexVideoMutation = useUploadAndIndexVideoMutation()
  
  const indexedVideos: IndexedVideo[] = useMemo(() => {
    if (!apiVideosData?.videos) return [];
    return apiVideosData.videos.map((video: ApiVideoItem) => ({
      id: video.id,
      name: video.filename,
      uploadDate: new Date(video.created_at).toISOString().split("T")[0],
      duration: video.duration_seconds
        ? `${Math.floor(video.duration_seconds / 60)}:${String(Math.floor(video.duration_seconds % 60)).padStart(2, '0')}`
        : "N/A",
      videoUrl: video.minio_video_url,
      audioUrl: video.minio_audio_url
    }));
  }, [apiVideosData]);

  const handleIndexVideo = async () => {
    // if (!uploadedVideo) return

    setIsIndexing(true)
    setIndexingProgress(0)

    // // Simulate indexing process
    // for (let i = 0; i <= 100; i += 10) {
    //   setIndexingProgress(i)
    //   await new Promise((resolve) => setTimeout(resolve, 200))
    // }

    if (!uploadedVideo) {
      alert("Please select a video file to upload and index.")
      return;
    }

    const formData = new FormData()
    formData.append("video_file", uploadedVideo);
    formData.append("num_keyframes_to_extract", config.numKeyframes.toString())
    
    try {
      await uploadAndIndexVideoMutation.mutateAsync(formData)
      alert(`Video "${uploadedVideo.name}" successfully indexed and saved in the database.`)
      clearVideo()
    } catch (error) {
      alert(`An error occurred while indexing video: ${error}`)
    } finally {
      setIsIndexing(true)
      setIndexingProgress(100)
    }
  }

  const handleReset = () => {
    resetAssessment()
    setSelectedVideoId(null)
    setHasStartedAssessment(false)
  }

  const handleStartAssessment = () => {
    if (!selectedVideoId) return
    setHasStartedAssessment(true)

    assessVideo({
      payload: {
        video_id: selectedVideoId, 
        rubric_question: rubricQuestion
      }, 
      config: config
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Video className="h-8 w-8" />
            OSCE Video Assessment System
          </h1>
          <p className="text-blue-100 mt-2">Multi-Agent Planner-Executor-Scorer-Reflector-Consensus Framework</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
          <ConfigurationSidebar
            config={config}
            setConfig={setConfig}
            rubricQuestion={rubricQuestion}
            setRubricQuestion={setRubricQuestion}
            uploadedVideo={uploadedVideo}
            handleVideoUpload={handleVideoUpload}
            isAssessing={isAssessing}
            assessmentProgress={assessmentProgress}
            onStartAssessment={handleStartAssessment}
            onResetAssessment={handleReset}
            indexedVideos={indexedVideos}
            selectedVideoId={selectedVideoId}
            onSelectVideo={setSelectedVideoId}
            isIndexing={isIndexing}
            indexingProgress={indexingProgress}
            onIndexVideo={handleIndexVideo}
            videoFileInputRef={videoFileInputRef}
          />

          <MainContent
            workflowStatus={workflowStatus}
            assessmentResults={assessmentResults ?? null}
            hasStarted={hasStartedAssessment}
          />
        </div>
      </div>
    </div>
  )
}
