import { useEffect, useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
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
import { BindingAffinityChart } from "@/components/dashboard/binding-affinity-chart"
import { RMSDConvergenceChart } from "@/components/dashboard/rmsd-convergence-chart"
import { DataAnalysisPanel } from "@/components/dashboard/data-analysis-panel"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Skeleton } from "@/components/ui/skeleton"

export default function Results() {
  const params = useParams()
  const navigate = useNavigate()
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
        const data = await apiClient.getDockingResults(jobId)
        setResults(data)
      } catch (err) {
        if (err instanceof APIError) setError(err.message)
        else setError("Unable to load results. Please try again.")
      } finally {
        setIsLoading(false)
      }
    }

    loadResults()
  }, [jobId])

  const handleRetry = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await apiClient.getDockingResults(jobId)
      setResults(data)
    } catch (err) {
      if (err instanceof APIError) setError(err.message)
      else setError("Unable to load results. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 md:py-12 lg:py-16">
          <div className="mb-8 space-y-6">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-10 w-64" />
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 lg:gap-8 mb-10">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </main>
        <Footer />
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
                <Link to="/dashboard">Return to Dashboard</Link>
              </Button>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  const hasPoses = results.poses.length > 0
  const safeSelectedPose = hasPoses ? Math.min(selectedPose, results.poses.length - 1) : 0

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 md:py-12 lg:py-16">
        <div className="mb-8 space-y-6">
          <Breadcrumb
          >
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to="/dashboard">Dashboard</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{`Job ${jobId.slice(0, 8)}`}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
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
          <TabsList className="grid w-full grid-cols-4 bg-muted/50 p-1.5">
            <TabsTrigger value="visualization" className="data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">Visualization</TabsTrigger>
            <TabsTrigger value="poses" className="data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">All Poses</TabsTrigger>
            <TabsTrigger value="analysis" className="data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">AI Analysis</TabsTrigger>
            <TabsTrigger value="report" className="data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">Generate Report</TabsTrigger>
          </TabsList>

          <TabsContent value="visualization" className="space-y-6">
            {!hasPoses ? (
              <ErrorAlert title="No poses" message="No docking poses were generated for this job." />
            ) : results.poses[safeSelectedPose]?.pose_file ? (
              <MoleculeViewer
                pdbData={results.poses[safeSelectedPose].pose_file}
                jobId={jobId}
                poseId={safeSelectedPose}
                title={`Pose ${safeSelectedPose + 1} - Score: ${results.poses[safeSelectedPose].score.toFixed(2)} kcal/mol`}
              />
            ) : (
              <ErrorAlert title="Visualization unavailable" message="Structure data for poses is not available. Metrics and analysis are still shown." />
            )}
            {hasPoses && (
              <>
                <div className="grid lg:grid-cols-2 gap-6">
                  <BindingAffinityChart poses={results.poses} />
                  <RMSDConvergenceChart poses={results.poses} />
                </div>
                <Card className="shadow-md">
                  <CardHeader>
                    <CardTitle className="text-xl font-bold">Select Pose</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {results.poses.map((pose, idx) => (
                        <Button
                          key={pose.pose_id}
                          variant={selectedPose === idx ? "default" : "outline"}
                          onClick={() => setSelectedPose(idx)}
                          className={`flex-col h-auto py-4 transition-all duration-300 ${
                            selectedPose === idx
                              ? "shadow-lg scale-105 border-2 border-primary"
                              : "hover:scale-102 hover:shadow-md"
                          }`}
                        >
                          <span className="font-bold text-base mb-1">Pose {idx + 1}</span>
                          <span className={`text-xs ${selectedPose === idx ? "text-primary-foreground/90" : "text-muted-foreground"}`}>
                            {pose.score.toFixed(2)} kcal/mol
                          </span>
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>

          <TabsContent value="poses">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="text-xl font-bold">All Generated Poses</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {!hasPoses ? (
                    <p className="text-muted-foreground py-8 text-center">No poses generated for this job.</p>
                  ) : (
                    results.poses.map((pose, idx) => (
                      <div
                        key={pose.pose_id}
                        className={`flex items-center justify-between p-4 border rounded-lg transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 ${
                          idx === selectedPose ? "bg-primary/5 border-primary/30" : "hover:bg-muted/50"
                        }`}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`font-bold text-lg ${idx === selectedPose ? "text-primary" : ""}`}>#{idx + 1}</div>
                          <div>
                            <p className="font-semibold text-base">Binding Score: <span className="text-primary">{pose.score.toFixed(2)} kcal/mol</span></p>
                            <p className="text-sm text-muted-foreground mt-1">
                              RMSD: {pose.rmsd.toFixed(2)} Å | Cluster: {pose.cluster_id}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant={idx === selectedPose ? "default" : "outline"}
                          size="sm"
                          onClick={() => setSelectedPose(idx)}
                          className="transition-all"
                        >
                          {idx === selectedPose ? "Selected" : "View"}
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis">
            <AIAnalysisPanel jobId={jobId} />
          </TabsContent>

          <TabsContent value="data-analysis">
            <DataAnalysisPanel
              jobId={jobId}
              dockingResults={{
                results: results.poses.map((pose) => ({
                  ligand_name: `pose_${pose.pose_id}`,
                  modes: [
                    {
                      affinity: pose.score,
                      rmsd_lb: pose.rmsd,
                      rmsd_ub: pose.rmsd,
                    },
                  ],
                })),
                best_score: results.best_pose.score,
              }}
            />
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
