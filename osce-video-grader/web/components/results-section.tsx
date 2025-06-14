"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, AlertTriangle, FileBarChart, Search } from "lucide-react"
import { ToolOutputSection } from "./evidence/tool-output-section"
import { getGradeColor } from "@/lib/utils"
import type { ApiAssessVideoResponse } from "@/types/assessment"

interface ResultsSectionProps {
  assessmentResults: ApiAssessVideoResponse
}

export function ResultsSection({ assessmentResults }: ResultsSectionProps) {
  const grade = assessmentResults.scorer_output.grade
  const rationale = assessmentResults.scorer_output.rationale
  const reflectorOutput = assessmentResults.reflector_output

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment Results</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Grade Display */}
        <div className={`text-center p-8 rounded-lg border-2 mb-6 ${getGradeColor(grade)}`}>
          <div className="text-6xl font-bold mb-2">{grade}/5</div>
          <div className="text-lg font-medium">Grade</div>
        </div>

        {/* Rationale */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Rationale</h3>
          <div className="bg-gray-50 border-l-4 border-green-500 p-4 rounded">{rationale}</div>
        </div>

        {/* Reflector Output */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
            <Search className="h-5 w-5" />
            Review Assessment
          </h3>
          {reflectorOutput.flagged ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <span className="font-semibold text-yellow-800">Flagged for Human Review</span>
              </div>
              <div className="space-y-2">
                {reflectorOutput.needs_more_evidence && (
                  <Badge variant="destructive" className="mb-2">
                    Needs More Evidence
                  </Badge>
                )}
                {reflectorOutput.reasons.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2 text-yellow-800">Review Reasons:</p>
                    <ul className="text-sm space-y-1">
                      {reflectorOutput.reasons.map((reason, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-yellow-600 mt-0.5">•</span>
                          <span className="text-yellow-700">{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="font-semibold text-green-800">No Human Review Required</span>
              </div>
              <p className="text-sm text-green-700 mt-2">
                The assessment has sufficient evidence and confidence for automated grading.
              </p>
            </div>
          )}
        </div>

        {/* Tools Used */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
            <FileBarChart className="h-5 w-5" />
            Tools Analysis
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-2">Planner Selected Tools:</p>
              <div className="flex flex-wrap gap-2">
                {assessmentResults.planner_output.map((tool, i) => (
                  <div key={i} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-lg font-semibold text-sm">
                    {tool}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium mb-2">All Tools:</p>
              <div className="flex flex-wrap gap-2">
                {assessmentResults.tools_used.map((tool, i) => {
                  const isSelected = assessmentResults.planner_output.includes(tool)
                  return (
                    <Badge
                      key={i}
                      variant={isSelected ? "default" : "secondary"}
                      className={isSelected ? "bg-blue-100 text-blue-800" : ""}
                    >
                      {tool}
                    </Badge>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Evidence Tabs */}
        <Tabs defaultValue="tools" className="w-full">
          <TabsList className="grid w-full grid-cols-1">
            <TabsTrigger value="tools">Tool Outputs</TabsTrigger>
          </TabsList>

          <TabsContent value="tools" className="space-y-4">
            <ToolOutputSection
              toolOutputs={assessmentResults.executor_output}
              plannerSelected={assessmentResults.planner_output}
              showAll={true}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
