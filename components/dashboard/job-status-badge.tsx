import { Badge } from "@/components/ui/badge"
import { CheckCircle, XCircle, Loader2, Clock, Dna, Activity } from "lucide-react"
import type { JobStatus } from "@/lib/api-client"

interface JobStatusBadgeProps {
  status: JobStatus["status"]
  className?: string
}

export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const statusConfig = {
    queued: {
      label: "Queued",
      icon: Clock,
      variant: "secondary" as const,
      color: "text-gray-500",
    },
    predicting_structure: {
      label: "Predicting Structure",
      icon: Dna,
      variant: "default" as const,
      color: "text-blue-500",
    },
    structure_predicted: {
      label: "Structure Predicted",
      icon: CheckCircle,
      variant: "default" as const,
      color: "text-green-500",
    },
    docking: {
      label: "Docking",
      icon: Activity,
      variant: "default" as const,
      color: "text-purple-500",
    },
    analyzing: {
      label: "Analyzing",
      icon: Loader2,
      variant: "default" as const,
      color: "text-yellow-500",
    },
    running: {
      label: "Running",
      icon: Loader2,
      variant: "default" as const,
      color: "text-blue-500",
    },
    completed: {
      label: "Completed",
      icon: CheckCircle,
      variant: "default" as const,
      color: "text-green-500",
    },
    failed: {
      label: "Failed",
      icon: XCircle,
      variant: "destructive" as const,
      color: "text-red-500",
    },
  }

  const config = statusConfig[status] || statusConfig.queued
  const Icon = config.icon

  return (
    <Badge variant={config.variant} className={className}>
      <Icon
        className={`w-3 h-3 mr-1 ${config.color} ${status === "running" || status === "analyzing" ? "animate-spin" : ""}`}
      />
      {config.label}
    </Badge>
  )
}
