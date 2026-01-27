"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, CheckCircle, XCircle, Loader2, Dna, Sparkles } from "lucide-react"
import type { JobStatus } from "@/lib/api-client"

interface DockingJobCardProps {
  job: JobStatus
}

export function DockingJobCard({ job }: DockingJobCardProps) {
  const getStatusIcon = () => {
    switch (job.status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case "failed":
        return <XCircle className="w-4 h-4 text-red-500" />
      case "running":
      case "docking":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
      case "predicting_structure":
        return <Dna className="w-4 h-4 text-purple-500 animate-pulse" />
      case "structure_predicted":
        return <CheckCircle className="w-4 h-4 text-blue-500" />
      case "analyzing":
        return <Sparkles className="w-4 h-4 text-yellow-500 animate-pulse" />
      case "queued":
        return <Clock className="w-4 h-4 text-yellow-500" />
    }
  }

  const getStatusBadge = () => {
    const config: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      completed: { variant: "default", label: "Completed" },
      failed: { variant: "destructive", label: "Failed" },
      running: { variant: "secondary", label: "Running" },
      predicting_structure: { variant: "secondary", label: "Predicting Structure" },
      structure_predicted: { variant: "default", label: "Structure Ready" },
      docking: { variant: "secondary", label: "Docking" },
      analyzing: { variant: "secondary", label: "Analyzing" },
      queued: { variant: "outline", label: "Queued" },
    }

    const status = config[job.status] || { variant: "outline", label: job.status }
    return <Badge variant={status.variant}>{status.label}</Badge>
  }

  return (
    <Card className="p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 flex-1">
          {getStatusIcon()}
          <div className="flex-1 min-w-0">
            <p className="font-medium text-base truncate">Job {job.job_id.slice(0, 8)}</p>
            <p className="text-sm text-muted-foreground mt-1">{new Date(job.created_at).toLocaleString()}</p>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {job.plddt_score !== undefined && (
        <div className="mt-4 flex items-center justify-between px-3 py-2 bg-muted/50 rounded-md">
          <span className="text-sm text-muted-foreground">AlphaFold Confidence</span>
          <span className="text-sm font-medium">
            {job.plddt_score.toFixed(1)}
            <span className="text-muted-foreground">/100</span>
          </span>
        </div>
      )}

      {job.top_binding_score !== undefined && job.status === "completed" && (
        <div className="mt-2 flex items-center justify-between px-3 py-2 bg-muted/50 rounded-md">
          <span className="text-sm text-muted-foreground">Best Binding Score</span>
          <span className="text-sm font-medium">
            {job.top_binding_score.toFixed(1)}
            <span className="text-muted-foreground"> kcal/mol</span>
          </span>
        </div>
      )}

      {job.progress !== undefined && (job.status === "running" || job.status === "docking") && (
        <div className="mt-4">
          <div className="w-full bg-muted rounded-full h-2.5">
            <div
              className="bg-primary h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>
      )}
      {job.error && <p className="text-sm text-destructive mt-3 leading-relaxed">{job.error}</p>}
    </Card>
  )
}
