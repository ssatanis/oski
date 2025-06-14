"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

interface SceneInteractionAnalyzerData {
  subject_label: string
  action_predicate: string
  object_target_label: string
  target_detail?: string | null
  timestamp: number
  keyframe_id: string
  keyframe_image_url: string
}

interface SceneInteractionAnalyzerOutputProps {
  data: SceneInteractionAnalyzerData[]
}

export function SceneInteractionAnalyzerOutput({ data }: SceneInteractionAnalyzerOutputProps) {
  if (!data || data.length === 0)
    return <div className="text-sm text-gray-500">No scene interaction data available</div>

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-2xl font-bold">{data.length}</div>
        <div className="text-sm text-gray-600">Interactions Detected</div>
      </div>
      <div className="space-y-3">
        {data.map((interaction, i) => (
          <div key={i} className="border rounded-lg p-3 bg-gray-50">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm">
                    {interaction.subject_label} → {interaction.action_predicate} → {interaction.object_target_label}
                  </span>
                  <Badge variant="outline">{interaction.timestamp}s</Badge>
                </div>
                {interaction.target_detail && <p className="text-sm text-gray-600 mb-2">{interaction.target_detail}</p>}
                <div className="text-xs text-gray-500">Keyframe: {interaction.keyframe_id.slice(0, 8)}...</div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    View Frame
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Interaction at {interaction.timestamp}s</DialogTitle>
                  </DialogHeader>
                  <img
                    src={interaction.keyframe_image_url || "/placeholder.svg"}
                    alt={`Interaction ${interaction.keyframe_id}`}
                    className="w-full h-auto rounded"
                  />
                  <div className="mt-4 space-y-2">
                    <p className="text-sm">
                      <strong>Subject:</strong> {interaction.subject_label}
                    </p>
                    <p className="text-sm">
                      <strong>Action:</strong> {interaction.action_predicate}
                    </p>
                    <p className="text-sm">
                      <strong>Object:</strong> {interaction.object_target_label}
                    </p>
                    {interaction.target_detail && (
                      <p className="text-sm">
                        <strong>Detail:</strong> {interaction.target_detail}
                      </p>
                    )}
                    <p className="text-sm">
                      <strong>Timestamp:</strong> {interaction.timestamp}s
                    </p>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
