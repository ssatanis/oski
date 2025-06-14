"use client"

import { Badge } from "@/components/ui/badge"

interface AudioTranscriptExtractorData {
  start_time: number
  end_time: number
  audio_segment_id: string
  transcript: string
  audio_segment_url: string
}

interface AudioTranscriptExtractorOutputProps {
  data: AudioTranscriptExtractorData[]
}

export function AudioTranscriptExtractorOutput({ data }: AudioTranscriptExtractorOutputProps) {
  if (!data || data.length === 0) return <div className="text-sm text-gray-500">No audio transcript data available</div>

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-2xl font-bold">{data.length}</div>
        <div className="text-sm text-gray-600">Audio Segments</div>
      </div>
      <div className="space-y-3">
        {data.map((segment, i) => (
          <div key={i} className="border rounded-lg p-3 bg-gray-50">
            <div className="flex justify-between items-center mb-2">
              <div className="font-semibold text-sm">
                {segment.start_time.toFixed(1)}s - {segment.end_time.toFixed(1)}s
              </div>
              <Badge variant="outline" className="text-xs">
                {segment.audio_segment_id.slice(0, 8)}...
              </Badge>
            </div>
            <div className="text-sm whitespace-pre-line font-mono bg-white p-2 rounded border mb-2">
              {segment.transcript}
            </div>
            <audio controls className="w-full" preload="none">
              <source src={segment.audio_segment_url} type="audio/wav" />
              Your browser does not support the audio element.
            </audio>
          </div>
        ))}
      </div>
    </div>
  )
}
