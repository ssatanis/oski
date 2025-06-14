"use client"

import type React from "react"

import { Settings, Upload, Play, RotateCcw, Database, Check, Target, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import type { AssessmentConfig, IndexedVideo } from "@/types/assessment"
import { Dispatch, SetStateAction } from "react"

interface ConfigurationSidebarProps {
  config: AssessmentConfig
  setConfig: (config: AssessmentConfig) => void
  uploadedVideo: File | null
  handleVideoUpload: (event: React.ChangeEvent<HTMLInputElement>) => void
  isAssessing: boolean
  assessmentProgress: number
  onStartAssessment: () => void
  onResetAssessment: () => void
  indexedVideos: IndexedVideo[]
  selectedVideoId: string | null
  onSelectVideo: (videoId: string) => void
  onIndexVideo: () => void
  isIndexing: boolean
  indexingProgress: number
  rubricQuestion: string
  setRubricQuestion: Dispatch<SetStateAction<string>>
  videoFileInputRef: React.RefObject<HTMLInputElement>
}

const EXAMPLE_QUESTIONS = [
  "Did the student greet the patient?",
  "Did the student wash their hands before examination?",
  "Did the student use a stethoscope properly?",
  "Did the student explain the procedure to the patient?",
  "Did the student maintain eye contact during conversation?",
]

export function ConfigurationSidebar({
  config,
  setConfig,
  uploadedVideo,
  handleVideoUpload,
  isAssessing,
  assessmentProgress,
  onStartAssessment,
  onResetAssessment,
  indexedVideos,
  selectedVideoId,
  onSelectVideo,
  onIndexVideo,
  isIndexing,
  indexingProgress,
  rubricQuestion, 
  setRubricQuestion,
  videoFileInputRef
}: ConfigurationSidebarProps) {
  const updateConfig = (updates: Partial<AssessmentConfig>) => {
    setConfig({ ...config, ...updates })
  }

  const canStartAssessment = selectedVideoId && rubricQuestion && !isAssessing

  return (
    <div className="lg:col-span-4 space-y-6">
      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Video Input */}
          <div>
            <label className="block text-sm font-medium mb-2">Video Management</label>

            {/* Upload for Indexing */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Upload & Index Video</label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
                <input 
                  type="file" 
                  accept="video/*" 
                  onChange={handleVideoUpload}
                  className="hidden"
                  id="video-upload" 
                  disabled={isIndexing}
                  ref={videoFileInputRef}
                />
                <label htmlFor="video-upload" className="cursor-pointer">
                  <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600">
                    {uploadedVideo ? `Ready to index: ${uploadedVideo.name}` : "Upload video for indexing"}
                  </p>
                </label>
              </div>
              {uploadedVideo && (
                <div className="space-y-2 mt-3">
                  <video controls className="w-full rounded-lg border" src={URL.createObjectURL(uploadedVideo)}>
                    Your browser does not support the video tag.
                  </video>
                  <Button onClick={onIndexVideo} disabled={isIndexing} className="w-full" variant="outline">
                    {isIndexing ? "Indexing..." : "Index Video"}
                  </Button>
                  {isIndexing && (
                    <div className="space-y-2">
                      <Progress value={indexingProgress} className="w-full" />
                      <p className="text-sm text-center text-gray-600">{indexingProgress.toFixed(0)}% Indexed</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Select Indexed Video */}
            <div>
              <label className="block text-sm font-medium mb-2">Select Video for Assessment</label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                {indexedVideos.length === 0 ? (
                  <div className="text-center py-4 text-gray-500">
                    <Database className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p className="text-sm">No indexed videos available</p>
                    <p className="text-xs text-gray-400">Upload and index a video first</p>
                  </div>
                ) : (
                  indexedVideos.map((video) => (
                    <div
                      key={video.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        selectedVideoId === video.id ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:bg-gray-50"
                      }`}
                      onClick={() => onSelectVideo(video.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium truncate">
                            {video.name} 
                            <Button onClick={() => window.open(
                            video.videoUrl as string, 
                            '_blank', 
                            'noopener,noreferrer'
                            )} 
                            variant={"ghost"}
                            ><ExternalLink />
                            </Button>
                          </p>
                          <p className="text-xs text-gray-500">{video.uploadDate}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          {video.duration && (
                            <Badge variant="outline" className="text-xs">
                              {video.duration}
                            </Badge>
                          )}
                          <Badge variant="secondary" className="text-xs">
                            Indexed
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              {selectedVideoId && (
                <Badge variant="secondary" className="mt-2">
                  <span className="flex items-center gap-1">
                    <Check className="h-3 w-3" />
                    Selected: {indexedVideos.find((v) => v.id === selectedVideoId)?.name.slice(0, 20)}...
                  </span>
                </Badge>
              )}
            </div>
          </div>

          {/* Rubric Question */}
          <div>
            <label className="block text-sm font-medium mb-2">Rubric Question</label>
            <Textarea
              value={rubricQuestion}
              onChange={(e) => setRubricQuestion(e.target.value)}
              placeholder="Enter the rubric question..."
              className="min-h-[80px]"
            />
            <div className="mt-2">
              <label className="block text-xs text-gray-500 mb-2">Example Questions:</label>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUESTIONS.map((example, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => setRubricQuestion(example)}
                  >
                    {example}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Model Settings */}
          <div>
            <label className="block text-sm font-medium mb-2">Model Settings</label>
            <div className="space-y-2">
              <Select value={config.clipModel} onValueChange={(value) => updateConfig({ clipModel: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="CLIP Model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ViT-B/32">ViT-B/32</SelectItem>
                  <SelectItem value="ViT-L/14">ViT-L/14</SelectItem>
                  <SelectItem value="RN50x64">RN50x64</SelectItem>
                </SelectContent>
              </Select>

              <Select value={config.clapModel} onValueChange={(value) => updateConfig({ clapModel: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="CLAP Model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CLAP-base">CLAP-base</SelectItem>
                  <SelectItem value="CLAP-large">CLAP-large</SelectItem>
                </SelectContent>
              </Select>

              <Select value={config.llmModel} onValueChange={(value) => updateConfig({ llmModel: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="LLM Model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GPT-4">GPT-4</SelectItem>
                  <SelectItem value="Claude-3">Claude-3</SelectItem>
                  <SelectItem value="Gemini-Pro">Gemini-Pro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Processing Parameters */}
          <div>
            <label className="block text-sm font-medium mb-2">Processing Parameters</label>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-600">Number of Keyframes: {config.numKeyframes}</label>
                <Slider
                  value={[config.numKeyframes]}
                  onValueChange={([value]) => updateConfig({ numKeyframes: value })}
                  max={60}
                  min={1}
                  step={1}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">Video Keyframe Retrieval Confidence Threshold: {config.videoKeyframeRetrievalConfThresh}</label>
                <Slider
                  value={[config.videoKeyframeRetrievalConfThresh]}
                  onValueChange={([value]) => updateConfig({ videoKeyframeRetrievalConfThresh: value })}
                  max={1}
                  min={0.1}
                  step={0.1}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">Audio Segment Retrieval Confidence Threshold: {config.audioSegmentRetrievalConfThresh}</label>
                <Slider
                  value={[config.audioSegmentRetrievalConfThresh]}
                  onValueChange={([value]) => updateConfig({ audioSegmentRetrievalConfThresh: value })}
                  max={1}
                  min={0.1}
                  step={0.1}
                  className=  "mt-1"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!selectedVideoId ? (
            <div className="text-center py-4">
              <p className="text-sm text-gray-600 mb-2">Select an indexed video to start assessment</p>
              <Button disabled className="w-full" size="lg">
                <Play className="h-4 w-4 mr-2" />
                Select Video First
              </Button>
            </div>
          ) : (
            <Button onClick={onStartAssessment} disabled={!canStartAssessment} className="w-full" size="lg">
              <Play className="h-4 w-4 mr-2" />
              {isAssessing ? "Assessing..." : "Start Assessment"}
            </Button>
          )}

          <Button onClick={onResetAssessment} variant="outline" className="w-full">
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset Assessment
          </Button>

          {isAssessing && (
            <div className="space-y-2">
              <Progress value={assessmentProgress} className="w-full" />
              <p className="text-sm text-center text-gray-600">{assessmentProgress.toFixed(0)}% Complete</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
