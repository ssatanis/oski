"use client"

import { Badge } from "@/components/ui/badge"

interface AudioSegment {
  timestamp: string
  similarity_score: number
  emotion: string
  audio_url: string
}

interface RetrievedAudioSegmentsProps {
  data?: {
    retrieved_segments: number
    segments: AudioSegment[]
  }
}

export function RetrievedAudioSegments({ data }: RetrievedAudioSegmentsProps) {
  if (!data) return <div className="text-sm text-gray-500">No audio segments available</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold">{data.retrieved_segments}</div>
          <div className="text-sm text-gray-600">Retrieved Segments</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">
            {(data.segments.reduce((a, b) => a + b.similarity_score, 0) / data.segments.length).toFixed(3)}
          </div>
          <div className="text-sm text-gray-600">Avg Similarity</div>
        </div>
      </div>
      <div className="space-y-3">
        {data.segments.map((segment, i) => (
          <div key={i} className="border rounded-lg p-4 bg-gray-50">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-mono">{segment.timestamp}</span>
              <div className="flex gap-2">
                <Badge
                  variant="outline"
                  className={`
                    ${segment.emotion === "Happy" ? "bg-green-100 text-green-800" : ""}
                    ${segment.emotion === "Sad" ? "bg-blue-100 text-blue-800" : ""}
                    ${segment.emotion === "Angry" ? "bg-red-100 text-red-800" : ""}
                    ${segment.emotion === "Neutral" ? "bg-gray-100 text-gray-800" : ""}
                  `}
                >
                  {segment.emotion}
                </Badge>
                <Badge variant="secondary">{segment.similarity_score.toFixed(3)}</Badge>
              </div>
            </div>
            <audio controls className="w-full mt-2" preload="none">
              <source src={segment.audio_url} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
          </div>
        ))}
      </div>
    </div>
  )
}
