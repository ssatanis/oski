"use client"

import { Brain, Zap, Search, PenTool, Users, Loader2, CheckCircle, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { WorkflowStatus } from "@/types/assessment"

interface WorkflowSectionProps {
  workflowStatus: WorkflowStatus
  hasStarted?: boolean
}

const WORKFLOW_STEPS = [
  {
    key: "planner" as const,
    name: "Planner",
    icon: Brain,
    description: "Analyzes rubric question and determines tool strategy",
  },
  {
    key: "executor" as const,
    name: "Executor",
    icon: Zap,
    description: "Invokes selected tools and gathers evidence",
  },
  {
    key: "scorer" as const,
    name: "Scorer",
    icon: PenTool,
    description: "Generates grade and rationale from evidence",
  },
  {
    key: "reflector" as const,
    name: "Reflector",
    icon: Search,
    description: "Evaluates evidence quality and flags for human review",
  },
  {
    key: "consensus" as const,
    name: "Consensus",
    icon: Users,
    description: "Refines answer through majority voting (optional)",
  },
]

function getStatusIcon(status: string, hasStarted: boolean) {
  if (!hasStarted) {
    return null
  }

  switch (status) {
    case "pending":
      return <Clock className="h-5 w-5 text-gray-400" />
    case "active":
      return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
    case "completed":
      return <CheckCircle className="h-5 w-5 text-green-600" />
    default:
      return <Clock className="h-5 w-5 text-gray-400" />
  }
}

export function WorkflowSection({ workflowStatus, hasStarted = false }: WorkflowSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment Workflow</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {WORKFLOW_STEPS.map((step) => {
            const status = workflowStatus[step.key]
            const Icon = step.icon
            const statusIcon = getStatusIcon(status, hasStarted)

            return (
              <div
                key={step.key}
                className={`border rounded-lg p-4 transition-all ${
                  hasStarted && status === "active"
                    ? "border-blue-500 bg-blue-50"
                    : hasStarted && status === "completed"
                      ? "border-green-500 bg-green-50"
                      : "border-gray-200 bg-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  {statusIcon && <div className="flex items-center">{statusIcon}</div>}
                  <Icon className="h-5 w-5" />
                  <div className="flex-1">
                    <h4 className="font-semibold">{step.name}</h4>
                    <p className="text-sm text-gray-600">{step.description}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
