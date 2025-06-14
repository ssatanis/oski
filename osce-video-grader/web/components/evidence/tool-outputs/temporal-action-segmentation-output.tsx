"use client"

import { Badge } from "@/components/ui/badge"

interface TemporalActionSegmenterData {
  action_label: string
  start_time: number
  end_time: number
}

interface TemporalActionSegmenterOutputProps {
  data: TemporalActionSegmenterData[]
}

export function TemporalActionSegmenterOutput({ data }: TemporalActionSegmenterOutputProps) {
  if (!data || data.length === 0)
    return <div className="text-sm text-gray-500">No temporal segmentation data available</div>

  const totalDuration = Math.max(...data.map((segment) => segment.end_time))

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-2xl font-bold">{data.length}</div>
        <div className="text-sm text-gray-600">Action Segments</div>
      </div>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {data.map((segment, i) => {
          const duration = segment.end_time - segment.start_time
          return (
            <div key={i} className="p-3 bg-gray-50 rounded border-l-4 border-blue-500">
              <div className="flex justify-between items-center">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-mono">
                      {segment.start_time.toFixed(1)}s - {segment.end_time.toFixed(1)}s
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {duration.toFixed(1)}s
                    </Badge>
                  </div>
                  <Badge variant="secondary">{segment.action_label.replace(/_/g, " ")}</Badge>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
