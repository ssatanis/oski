"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight, Star } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import { SceneCaptionerOutput } from "./tool-outputs/scene-captioner-output"
import { ObjectDetectorOutput } from "./tool-outputs/object-detector-output"
import { PoseAnalyzerOutput } from "./tool-outputs/pose-analyzer-output"
import { TemporalActionSegmenterOutput } from "./tool-outputs/temporal-action-segmentation-output"
import { SceneInteractionAnalyzerOutput } from "./tool-outputs/scene-interaction-analyzer"
import { AudioTranscriptExtractorOutput } from "./tool-outputs/audio-transcript-extractor-output"

interface ToolOutputSectionProps {
  toolOutputs: any
  plannerSelected: string[]
  showAll?: boolean
}

const ALL_TOOLS = [
  { name: "Scene Describer", key: "keyframe_captioner", component: SceneCaptionerOutput },
  { name: "Object Detector", key: "object_detector", component: ObjectDetectorOutput },
  { name: "Pose Analyzer", key: "pose_analyzer", component: PoseAnalyzerOutput },
  { name: "Temporal Action Segmenter", key: "temporal_action_segmenter", component: TemporalActionSegmenterOutput },
  {
    name: "Scene Interaction Analyzer",
    key: "scene_interaction_analyzer",
    component: SceneInteractionAnalyzerOutput,
  },
  {
    name: "Audio Transcript Extractor",
    key: "audio_transcript_extractor",
    component: AudioTranscriptExtractorOutput,
  },
]

function ToolOutputCard({
  name,
  toolKey,
  data,
  component: Component,
  isSelected,
  showAll,
}: {
  name: string
  toolKey: string
  data: any
  component: any
  isSelected: boolean
  showAll: boolean
}) {
  const [isOpen, setIsOpen] = useState(isSelected)

  // If showAll is false, only show selected tools
  if (!showAll && !isSelected) {
    return null
  }

  const hasData = data && (Array.isArray(data) ? data.length > 0 : Object.keys(data).length > 0)

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className={isSelected ? "border-blue-200 bg-blue-50/30" : ""}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-gray-50">
            <CardTitle className="text-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                {name}
                {!hasData && <Badge variant="outline">No Data</Badge>}
              </div>
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </CardTitle>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent>
            {hasData ? (
              <Component data={data} />
            ) : (
              <p className="text-sm text-gray-500">No output available for this tool</p>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}

export function ToolOutputSection({ toolOutputs, plannerSelected, showAll = true }: ToolOutputSectionProps) {
  return (
    <div className="space-y-3">
      {ALL_TOOLS.map((tool) => {
        const isSelected = plannerSelected.includes(tool.key)
        return (
          <ToolOutputCard
            key={tool.key}
            name={tool.name}
            toolKey={tool.key}
            data={toolOutputs[tool.key]}
            component={tool.component}
            isSelected={isSelected}
            showAll={showAll}
          />
        )
      })}
    </div>
  )
}
