"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

interface ObjectDetectorData {
  name: string
  context: string
  timestamp: number
  keyframe_id: string
  keyframe_image_url: string
  confidence_score: number
}

interface ObjectDetectorOutputProps {
  data: ObjectDetectorData[]
}

export function ObjectDetectorOutput({ data }: ObjectDetectorOutputProps) {
  if (!data || data.length === 0) return <div className="text-sm text-gray-500">No object detection data available</div>

  const avgConfidence = data.reduce((sum, obj) => sum + obj.confidence_score, 0) / data.length

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold">{data.length}</div>
          <div className="text-sm text-gray-600">Objects Detected</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{avgConfidence.toFixed(3)}</div>
          <div className="text-sm text-gray-600">Avg Confidence</div>
        </div>
      </div>
      <div className="space-y-3">
        {data.map((obj, i) => (
          <div key={i} className="border rounded-lg p-3 bg-gray-50">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm capitalize">{obj.name.replace(/[-_]/g, " ")}</span>
                  <Badge variant="secondary">{obj.confidence_score.toFixed(3)}</Badge>
                </div>
                <p className="text-sm text-gray-600 mb-2">{obj.context}</p>
                <div className="flex gap-2 text-xs text-gray-500">
                  <span>Timestamp: {obj.timestamp}s</span>
                  <span>•</span>
                  <span>Keyframe: {obj.keyframe_id.slice(0, 8)}...</span>
                </div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    View Frame
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>
                      {obj.name} at {obj.timestamp}s
                    </DialogTitle>
                  </DialogHeader>
                  <img
                    src={obj.keyframe_image_url || "/placeholder.svg"}
                    alt={`Object ${obj.name}`}
                    className="w-full h-auto rounded"
                  />
                  <div className="mt-4 space-y-2">
                    <p className="text-sm">
                      <strong>Object:</strong> {obj.name}
                    </p>
                    <p className="text-sm">
                      <strong>Context:</strong> {obj.context}
                    </p>
                    <p className="text-sm">
                      <strong>Confidence:</strong> {obj.confidence_score.toFixed(3)}
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
