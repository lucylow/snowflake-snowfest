"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StatisticalAnalysis } from "./statistical-analysis"
import { ComparativeAnalysis } from "./comparative-analysis"
import { TrendAnalysis } from "./trend-analysis"
import { DataExport } from "./data-export"
import { BarChart3 } from "lucide-react"

type DockingResultsForStats =
  | {
      results?: Array<{
        ligand_name: string
        modes?: Array<{
          affinity: number
          rmsd_lb?: number
          rmsd_ub?: number
        }>
      }>
      best_score?: number
    }
  | {
      poses?: Array<{
        score: number
        rmsd: number
      }>
      best_pose?: {
        score: number
      }
    }

interface JobData {
  jobId: string
  jobName: string
  createdAt?: string
  results?: Array<{
    ligand_name: string
    modes?: Array<{
      affinity: number
    }>
  }>
  best_score?: number
}

interface DataAnalysisPanelProps {
  jobId: string
  dockingResults: DockingResultsForStats
  analysisResults?: Record<string, unknown>
  allJobs?: JobData[]
}

export function DataAnalysisPanel({
  jobId,
  dockingResults,
  analysisResults,
  allJobs = [],
}: DataAnalysisPanelProps) {
  const comparisonJobs = allJobs.map((j) => ({
    jobId: j.jobId,
    jobName: j.jobName,
    results: j.results,
    best_score: j.best_score,
  }))

  const trendJobs = allJobs
    .filter((j): j is JobData & { createdAt: string } => !!j.createdAt)
    .map((j) => ({
      jobId: j.jobId,
      jobName: j.jobName,
      createdAt: j.createdAt,
      best_score: j.best_score,
      results: j.results,
    }))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-6 h-6 text-primary" />
        <h2 className="text-2xl font-bold">Data Analysis</h2>
      </div>

      <Tabs defaultValue="statistics" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="statistics">Statistics</TabsTrigger>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>

        <TabsContent value="statistics" className="mt-6">
          <StatisticalAnalysis dockingResults={dockingResults} />
        </TabsContent>

        <TabsContent value="comparison" className="mt-6">
          {allJobs.length >= 2 ? (
            <ComparativeAnalysis jobs={comparisonJobs} />
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <p>Need at least 2 jobs to perform comparative analysis.</p>
              <p className="text-sm mt-2">Complete more docking jobs to enable this feature.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="trends" className="mt-6">
          {trendJobs.length >= 2 ? (
            <TrendAnalysis jobs={trendJobs} />
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <p>Need at least 2 jobs with timestamps to analyze trends.</p>
              <p className="text-sm mt-2">Complete more docking jobs to enable this feature.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="export" className="mt-6">
          <DataExport jobId={jobId} dockingResults={dockingResults} analysisResults={analysisResults} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
