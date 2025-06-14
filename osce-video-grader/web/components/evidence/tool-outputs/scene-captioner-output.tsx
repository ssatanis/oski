"use client"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

type SceneCaptionerData = {
  keyframe_id: string
  keyframe_image_url: string
  timestamp: number
  keyframe_description: string
}[]

interface SceneCaptionerOutputProps {
  data: SceneCaptionerData
}

export function SceneCaptionerOutput({ data }: SceneCaptionerOutputProps) {
  return (
    <div className="space-y-3">
      {data.map((item, i) => (
        <div key={i} className="border rounded-lg p-3 bg-gray-50">
          <div className="flex justify-between items-start mb-2">
            <div className="flex-1">
              <div className="font-semibold text-sm mb-1">Caption {i + 1}:</div>
              <div className="text-sm mb-2">{item.keyframe_description}</div>
              <div className="flex gap-2 text-xs text-gray-500">
                <span>Timestamp: {item.timestamp}</span>
                <span>•</span>
                <span>Keyframe ID: {item.keyframe_id}</span>
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
                    Keyframe {item.keyframe_id} - {item.timestamp}
                  </DialogTitle>
                </DialogHeader>
                <img
                  src={item.keyframe_image_url || "/placeholder.svg"}
                  alt={`Keyframe ${item.keyframe_id}`}
                  className="w-full h-auto rounded"
                />
                <div className="mt-4">
                  <p className="text-sm">
                    <strong>Caption:</strong> {item.keyframe_description}
                  </p>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      ))}
    </div>
  )
}
