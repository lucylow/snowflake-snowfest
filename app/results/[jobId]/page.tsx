"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Header } from "@/components/landing/header"
import { Footer } from "@/components/landing/footer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { MoleculeViewer } from "@/components/dashboard/molecule-viewer"
import { AIAnalysisPanel } from "@/components/dashboard/ai-analysis-panel"
import { ReportGenerator } from "@/components/dashboard/report-generator"
import { ErrorAlert } from "@/components/ui/error-alert"
import { apiClient, APIError, type DockingResult } from "@/lib/api-client"
import { ArrowLeft, Loader2, TrendingDown, Activity, Zap } from "lucide-react"
import Link from "next/link"
import { mockDockingResults } from "@/lib/mock-data"
import { BindingAffinityChart } from "@/components/dashboard/binding-affinity-chart"
import { RMSDConvergenceChart } from "@/components/dashboard/rmsd-convergence-chart"

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.jobId as string
  const [results, setResults] = useState<DockingResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPose, setSelectedPose] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadResults = async () => {
      if (!jobId) {
        setError("Invalid job ID")
        setIsLoading(false)
        return
      }

      try {
        setError(null)
        const mockData = mockDockingResults[jobId as keyof typeof mockDockingResults]
        if (mockData) {
          setResults(mockData as DockingResult)
          setIsLoading(false)
          return
        }

        const data = await apiClient.getDockingResults(jobId)
        setResults(data)
      } catch (error) {
        console.error("[v0] Failed to load results:", error)
        if (error instanceof APIError) {
          setError(error.message)
        } else {
          setError("Unable to load results. Please try again.")
        }
      } finally {
        setIsLoading(false)
      }
    }

    loadResults()
  }, [jobId])

  const handleRetry = () => {
    setIsLoading(true)
    setError(null)
    const loadResults = async () => {
      try {
        const data = await apiClient.getDockingResults(jobId)
        setResults(data)
      } catch (error) {
        if (error instanceof APIError) {
          setError(error.message)
        } else {
          setError("Unable to load results. Please try again.")
        }
      } finally {
        setIsLoading(false)
      }
    }
    loadResults()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading results...</p>
        </div>
      </div>
    )
  }

  if (error || !results) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="container py-8 md:py-12">
          <div className="max-w-2xl mx-auto">
            <ErrorAlert
              title="Unable to Load Results"
              message={error || "Results not found for this job"}
              onRetry={error ? handleRetry : undefined}
            />
            <div className="mt-6 text-center">
              <Button asChild>
                <Link href="/dashboard">Return to Dashboard</Link>
              </Button>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  const safeSelectedPose = Math.min(selectedPose, results.poses.length - 1)

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 md:py-12 lg:py-16">
        <div className="mb-8 space-y-6">
          <Button variant="ghost" asChild className="gap-2">
            <Link href="/dashboard">
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Link>
          </Button>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">Docking Results</h1>
              <p className="text-sm text-muted-foreground sm:text-base">Job ID: {jobId}</p>
            </div>
            <Badge variant="secondary" className="text-sm px-4 py-2 w-fit sm:text-base">
              {results.poses.length} Poses Generated
            </Badge>
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 lg:gap-8 mb-10">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <TrendingDown className="w-5 h-5 text-green-500" />
                <Badge variant="outline">Best Score</Badge>
              </div>
              <p className="text-2xl font-bold">{results.best_pose.score.toFixed(2)}</p>
              <p className="text-sm text-muted-foreground">kcal/mol</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Activity className="w-5 h-5 text-blue-500" />
                <Badge variant="outline">Mean Score</Badge>
              </div>
              <p className="text-2xl font-bold">{results.metrics.mean_score.toFixed(2)}</p>
              <p className="text-sm text-muted-foreground">Average binding affinity</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Zap className="w-5 h-5 text-purple-500" />
                <Badge variant="outline">Confidence</Badge>
              </div>
              <p className="text-2xl font-bold">{Math.round(results.metrics.confidence_score * 100)}%</p>
              <p className="text-sm text-muted-foreground">Prediction accuracy</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="visualization" className="space-y-8">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="visualization">Visualization</TabsTrigger>
            <TabsTrigger value="poses">All Poses</TabsTrigger>
            <TabsTrigger value="analysis">AI Analysis</TabsTrigger>
            <TabsTrigger value="report">Generate Report</TabsTrigger>
          </TabsList>

          <TabsContent value="visualization" className="space-y-6">
            {results.poses[safeSelectedPose]?.pose_file ? (
              <MoleculeViewer
                pdbData={results.poses[safeSelectedPose].pose_file}
                jobId={jobId}
                poseId={safeSelectedPose}
                title={`Pose ${safeSelectedPose + 1} - Score: ${results.poses[safeSelectedPose].score.toFixed(2)} kcal/mol`}
              />
            ) : (
              <ErrorAlert title="Visualization Error" message="Unable to load molecular structure data" />
            )}
            <div className="grid lg:grid-cols-2 gap-6">
              <BindingAffinityChart poses={results.poses} />
              <RMSDConvergenceChart poses={results.poses} />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Select Pose</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {results.poses.map((pose, idx) => (
                    <Button
                      key={pose.pose_id}
                      variant={selectedPose === idx ? "default" : "outline"}
                      onClick={() => setSelectedPose(idx)}
                      className="flex-col h-auto py-3"
                    >
                      <span className="font-bold">Pose {idx + 1}</span>
                      <span className="text-xs">{pose.score.toFixed(2)} kcal/mol</span>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="poses">
            <Card>
              <CardHeader>
                <CardTitle>All Generated Poses</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {results.poses.map((pose, idx) => (
                    <div
                      key={pose.pose_id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="font-bold">#{idx + 1}</div>
                        <div>
                          <p className="font-medium">Binding Score: {pose.score.toFixed(2)} kcal/mol</p>
                          <p className="text-sm text-muted-foreground">
                            RMSD: {pose.rmsd.toFixed(2)} Å | Cluster: {pose.cluster_id}
                          </p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => setSelectedPose(idx)}>
                        View
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis">
            <AIAnalysisPanel jobId={jobId} />
          </TabsContent>

          <TabsContent value="report">
            <ReportGenerator jobId={jobId} />
          </TabsContent>
        </Tabs>
      </main>
      <Footer />
    </div>
  )
}
