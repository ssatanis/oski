"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

interface PoseAnalyzerData {
  timestamp: number
  keyframe_id: string
  keyframe_image_url: string
  person_label: string
  pose: string
  gaze: string
}

interface PoseAnalyzerOutputProps {
  data: PoseAnalyzerData[]
}

export function PoseAnalyzerOutput({ data }: PoseAnalyzerOutputProps) {
  if (!data || data.length === 0) return <div className="text-sm text-gray-500">No pose analysis data available</div>

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-2xl font-bold">{data.length}</div>
        <div className="text-sm text-gray-600">Poses Analyzed</div>
      </div>
      <div className="space-y-3">
        {data.map((pose, i) => (
          <div key={i} className="border rounded-lg p-3 bg-gray-50">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm capitalize">{pose.person_label}</span>
                  <Badge variant="outline">{pose.timestamp}s</Badge>
                </div>
                <p className="text-sm text-gray-600 mb-1">
                  <strong>Pose:</strong> {pose.pose}
                </p>
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Gaze:</strong> {pose.gaze}
                </p>
                <div className="text-xs text-gray-500">Keyframe: {pose.keyframe_id.slice(0, 8)}...</div>
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
                      {pose.person_label} at {pose.timestamp}s
                    </DialogTitle>
                  </DialogHeader>
                  <img
                    src={pose.keyframe_image_url || "/placeholder.svg"}
                    alt={`Pose ${pose.keyframe_id}`}
                    className="w-full h-auto rounded"
                  />
                  <div className="mt-4 space-y-2">
                    <p className="text-sm">
                      <strong>Person:</strong> {pose.person_label}
                    </p>
                    <p className="text-sm">
                      <strong>Pose:</strong> {pose.pose}
                    </p>
                    <p className="text-sm">
                      <strong>Gaze:</strong> {pose.gaze}
                    </p>
                    <p className="text-sm">
                      <strong>Timestamp:</strong> {pose.timestamp}s
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
