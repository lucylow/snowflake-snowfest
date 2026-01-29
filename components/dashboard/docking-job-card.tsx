"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, CheckCircle, XCircle, Loader2, Dna, Sparkles } from "lucide-react"
import type { JobStatus } from "@/lib/api-client"

interface DockingJobCardProps {
  job: JobStatus
}

export function DockingJobCard({ job }: DockingJobCardProps) {
  const qualityMetrics =
    job.quality_metrics && typeof job.quality_metrics === "object" ? (job.quality_metrics as Record<string, unknown>) : undefined

  const confidenceRegions = qualityMetrics?.confidence_regions as
    | { very_high?: number; confident?: number }
    | undefined

  const paeScore = qualityMetrics?.pae_score

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
    <Card className="p-5 hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 border-l-4 border-l-transparent hover:border-l-primary/50 group">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 flex-1">
          <div className="p-2 rounded-lg bg-muted/50 group-hover:bg-muted transition-colors">
            {getStatusIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-base truncate group-hover:text-primary transition-colors">Job {job.job_id.slice(0, 8)}</p>
            <p className="text-sm text-muted-foreground mt-1">{new Date(job.created_at).toLocaleString()}</p>
          </div>
        </div>
        <div className="group-hover:scale-105 transition-transform">
          {getStatusBadge()}
        </div>
      </div>

      {job.plddt_score !== undefined && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-muted/50 to-muted/30 rounded-lg border border-border/50 hover:border-primary/20 transition-colors">
            <span className="text-sm font-medium text-muted-foreground">AlphaFold Confidence</span>
            <div className="flex items-center gap-2">
              <div className="h-2 w-16 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                  style={{ width: `${job.plddt_score}%` }}
                />
              </div>
              <span className="text-sm font-bold">
                {job.plddt_score.toFixed(1)}
                <span className="text-muted-foreground font-normal">/100</span>
              </span>
            </div>
          </div>
          {job.quality_metrics && (
            <div className="px-4 py-2.5 bg-muted/30 rounded-lg border border-border/30 text-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">High Confidence:</span>
                <span className="font-semibold text-foreground">
                  {(confidenceRegions?.very_high ?? 0) + (confidenceRegions?.confident ?? 0)} residues
                </span>
              </div>
              {typeof paeScore === "number" && (
                <div className="flex items-center justify-between pt-2 border-t border-border/30">
                  <span className="text-muted-foreground">PAE Score:</span>
                  <span className="font-semibold text-foreground">{paeScore.toFixed(2)} Å</span>
                </div>
              )}
            </div>
          )}
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
      {job.error && (
        <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-sm text-destructive leading-relaxed font-medium">{job.error}</p>
        </div>
      )}
    </Card>
  )
}
