"use client"

import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

interface Keyframe {
  id: string
  timestamp: string
  similarity_score: number
  image_url: string
}

interface RetrievedVideoKeyframesProps {
  data?: {
    retrieved_frames: number
    keyframes: Keyframe[]
  }
}

export function RetrievedVideoKeyframes({ data }: RetrievedVideoKeyframesProps) {
  if (!data) return <div className="text-sm text-gray-500">No keyframes available</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold">{data.retrieved_frames}</div>
          <div className="text-sm text-gray-600">Retrieved Frames</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">
            {(data.keyframes.reduce((a, b) => a + b.similarity_score, 0) / data.keyframes.length).toFixed(3)}
          </div>
          <div className="text-sm text-gray-600">Avg Similarity</div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.keyframes.map((keyframe, i) => (
          <Dialog key={i}>
            <DialogTrigger asChild>
              <div className="cursor-pointer border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                <img
                  src={keyframe.image_url || "/placeholder.svg"}
                  alt={`Keyframe ${keyframe.id}`}
                  className="w-full h-32 object-cover rounded mb-2"
                />
                <div className="flex justify-between items-center">
                  <span className="text-sm font-mono">{keyframe.timestamp}</span>
                  <Badge variant="secondary">{keyframe.similarity_score.toFixed(3)}</Badge>
                </div>
                <div className="text-xs text-gray-500 mt-1">ID: {keyframe.id}</div>
              </div>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>
                  Keyframe {keyframe.id} - {keyframe.timestamp}
                </DialogTitle>
              </DialogHeader>
              <img
                src={keyframe.image_url || "/placeholder.svg"}
                alt={`Keyframe ${keyframe.id}`}
                className="w-full h-auto rounded"
              />
              <div className="flex justify-between items-center mt-4">
                <span>Similarity Score: {keyframe.similarity_score.toFixed(3)}</span>
                <span>Timestamp: {keyframe.timestamp}</span>
              </div>
            </DialogContent>
          </Dialog>
        ))}
      </div>
    </div>
  )
}
