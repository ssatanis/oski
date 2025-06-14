"use client"

import { WorkflowSection } from "./workflow-section"
import { ResultsSection } from "./results-section"
import type { WorkflowStatus, ApiAssessVideoResponse } from "@/types/assessment"

interface MainContentProps {
  workflowStatus: WorkflowStatus
  assessmentResults: ApiAssessVideoResponse | null
  hasStarted?: boolean
}

export function MainContent({ workflowStatus, assessmentResults, hasStarted = false }: MainContentProps) {
  return (
    <div className="lg:col-span-6 space-y-6">
      <WorkflowSection workflowStatus={workflowStatus} hasStarted={hasStarted} />
      {assessmentResults && <ResultsSection assessmentResults={assessmentResults} />}
    </div>
  )
}
