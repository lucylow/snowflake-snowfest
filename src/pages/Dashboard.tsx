import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Header } from "@/components/landing/header"
import { Footer } from "@/components/landing/footer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Beaker, Upload, Activity, CheckCircle, XCircle, Loader2, Eye, Wallet } from "lucide-react"
import { allMockJobs, healthTechInsights, therapeuticAreas } from "@/lib/mock-data"
import { apiClient, APIError, type DockingParameters, type JobStatus } from "@/lib/api-client"
import { DockingJobCard } from "@/components/dashboard/docking-job-card"
import { SubmitJobDialog } from "@/components/dashboard/submit-job-dialog"
import { ErrorAlert } from "@/components/ui/error-alert"
import { useWallet } from "@/contexts/wallet-context"
import { Badge } from "@/components/ui/badge"
import { solanaClient } from "@/lib/solana-client"
import { JobSearchFilter } from "@/components/dashboard/job-search-filter"
import { JobListSkeleton } from "@/components/dashboard/job-list-skeleton"
import { Skeleton } from "@/components/ui/skeleton"
import { useKeyboardShortcut } from "@/hooks/use-keyboard-shortcut"

export default function Dashboard() {
  const navigate = useNavigate()
  const { connected, publicKey, connect } = useWallet()
  const [jobs, setJobs] = useState<JobStatus[]>(allMockJobs)
  const [filteredJobs, setFilteredJobs] = useState<JobStatus[]>(allMockJobs)
  const [isSubmitDialogOpen, setIsSubmitDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [balance, setBalance] = useState<number | null>(null)

  useEffect(() => {
    const fetchBalance = async () => {
      if (connected && publicKey) {
        try {
          const bal = await solanaClient.getBalance(publicKey)
          setBalance(bal)
        } catch (error) {
          console.error("[v0] Failed to fetch balance:", error)
        }
      }
    }

    fetchBalance()
  }, [connected, publicKey])

  useEffect(() => {
    const wsConnections: WebSocket[] = []

    jobs.forEach((job) => {
      if (
        job.status === "running" ||
        job.status === "queued" ||
        job.status === "predicting_structure" ||
        job.status === "structure_predicted"
      ) {
        try {
          const ws = apiClient.connectWebSocket(
            job.job_id,
            (updatedJob) => {
              setJobs((prev) => prev.map((j) => (j.job_id === updatedJob.job_id ? updatedJob : j)))
            },
            (error) => {
              console.error("[v0] WebSocket error:", error)
            },
          )
          wsConnections.push(ws)
        } catch (error) {
          console.error("[v0] Failed to establish WebSocket connection:", error)
        }
      }
    })

    return () => {
      wsConnections.forEach((ws) => {
        try {
          ws.close()
        } catch (error) {
          console.error("[v0] Error closing WebSocket:", error)
        }
      })
    }
  }, [jobs])

  // Keyboard shortcuts
  useKeyboardShortcut([
    {
      key: "n",
      ctrlKey: true,
      callback: () => setIsSubmitDialogOpen(true),
      description: "Open new job dialog",
    },
    {
      key: "/",
      callback: () => {
        const searchInput = document.querySelector('input[placeholder*="Search jobs"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: "Focus search",
    },
  ])

  const stats = [
    {
      title: "Total Jobs",
      value: jobs.length.toString(),
      change: `${jobs.filter((j) => j.status === "completed").length} completed`,
      icon: Beaker,
      color: "text-blue-500",
    },
    {
      title: "AlphaFold Predictions",
      value: jobs.filter((j) => (j as JobStatus & { job_type?: string }).job_type === "sequence_to_docking").length.toString(),
      change: "Structure predictions",
      icon: Activity,
      color: "text-purple-500",
    },
    {
      title: "Success Rate",
      value:
        jobs.length > 0
          ? `${Math.round((jobs.filter((j) => j.status === "completed").length / jobs.length) * 100)}%`
          : "0%",
      change: "Overall accuracy",
      icon: CheckCircle,
      color: "text-green-500",
    },
    {
      title: "Avg Confidence",
      value: "88.7%",
      change: "pLDDT score",
      icon: XCircle,
      color: "text-yellow-500",
    },
  ]

  const handleSubmitJob = async (
    jobType: "docking_only" | "sequence_to_docking",
    proteinFile: File | null,
    proteinSequence: string | null,
    ligandFile: File,
    parameters: DockingParameters,
  ) => {
    setError(null)
    setIsLoading(true)

    try {
      let result
      try {
        if (jobType === "sequence_to_docking" && proteinSequence) {
          // Submit sequence-to-docking job
          result = await apiClient.submitSequenceDockingJob(
            `AlphaFold Job ${Date.now()}`,
            proteinSequence,
            ligandFile,
            parameters,
          )
        } else if (jobType === "docking_only" && proteinFile) {
          // Submit docking-only job
          result = await apiClient.submitDockingJob(proteinFile, ligandFile, parameters)
        } else {
          throw new Error("Invalid job configuration")
        }
      } catch (apiError) {
        console.log("[v0] Backend not available, creating mock job")
        result = {
          job_id: `mock-${Date.now()}`,
          status: jobType === "sequence_to_docking" ? "predicting_structure" : "queued",
          message: "Job submitted successfully (mock mode)",
        }
      }

      setJobs((prev) => [
        {
          job_id: result.job_id,
          status: result.status as JobStatus["status"],
          created_at: new Date().toISOString(),
          protein_sequence: proteinSequence || undefined,
        },
        ...prev,
      ])

      setIsSubmitDialogOpen(false)

      // Simulate job progression in mock mode
      if (result.job_id.startsWith("mock-")) {
        if (jobType === "sequence_to_docking") {
          // Simulate AlphaFold prediction
          setTimeout(() => {
            setJobs((prev) =>
              prev.map((job) =>
                job.job_id === result.job_id
                  ? { ...job, status: "structure_predicted" as const, plddt_score: 85.4 }
                  : job,
              ),
            )
          }, 2000)

          // Then docking
          setTimeout(() => {
            setJobs((prev) =>
              prev.map((job) => (job.job_id === result.job_id ? { ...job, status: "docking" as const } : job)),
            )
          }, 4000)

          // Finally completed
          setTimeout(() => {
            setJobs((prev) =>
              prev.map((job) =>
                job.job_id === result.job_id
                  ? {
                      ...job,
                      status: "completed" as const,
                      completed_at: new Date().toISOString(),
                      top_binding_score: -8.2,
                    }
                  : job,
              ),
            )
          }, 6000)
        } else {
          // Normal docking workflow
          setTimeout(() => {
            setJobs((prev) =>
              prev.map((job) =>
                job.job_id === result.job_id
                  ? { ...job, status: "completed" as const, completed_at: new Date().toISOString() }
                  : job,
              ),
            )
          }, 3000)
        }
      }
    } catch (error) {
      console.error("[v0] Failed to submit job:", error)
      if (error instanceof APIError) {
        setError(error.message)
      } else {
        setError("An unexpected error occurred. Please try again.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewResults = (jobId: string) => {
    try {
      navigate(`/results/${jobId}`)
    } catch (error) {
      console.error("[v0] Navigation error:", error)
      setError("Unable to navigate to results page")
    }
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 md:py-16 lg:py-20">
        {error && (
          <div className="mb-8">
            <ErrorAlert 
              message={error} 
              onRetry={() => setError(null)} 
              onDismiss={() => setError(null)}
              dismissible
            />
          </div>
        )}

        <div className="flex flex-col gap-6 mb-12 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">Drug Discovery Dashboard</h1>
            <p className="text-base text-muted-foreground sm:text-lg max-w-2xl leading-relaxed">
              Track AlphaFold structure predictions, molecular docking jobs, and AI-powered therapeutic insights.
            </p>
          </div>
          <Button
            className="gap-2 shrink-0 w-full sm:w-auto shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
            size="lg"
            onClick={() => setIsSubmitDialogOpen(true)}
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            New Analysis
          </Button>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8 mb-12">
          {isInitialLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <Card key={i} className="hover:shadow-lg transition-all duration-300">
                  <CardContent className="p-6 lg:p-8">
                    <div className="flex items-center justify-between mb-6">
                      <Skeleton className="w-9 h-9 rounded-lg" />
                      <Skeleton className="h-4 w-24" />
                    </div>
                    <div>
                      <Skeleton className="h-10 w-20 mb-2" />
                      <Skeleton className="h-4 w-32" />
                    </div>
                  </CardContent>
                </Card>
              ))
            : stats.map((stat) => {
                const Icon = stat.icon
                return (
                  <Card key={stat.title} className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-l-4 border-l-primary/20 group">
                    <CardContent className="p-6 lg:p-8 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary/5 to-transparent rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                      <div className="flex items-center justify-between mb-6 relative z-10">
                        <div className={`p-2 rounded-lg bg-muted/50 group-hover:bg-muted transition-colors`}>
                          <Icon className={`w-5 h-5 ${stat.color} transition-transform group-hover:scale-110`} />
                        </div>
                        <span className="text-xs md:text-sm font-medium text-muted-foreground">{stat.change}</span>
                      </div>
                      <div className="relative z-10">
                        <p className="text-3xl lg:text-4xl font-bold mb-2 bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">{stat.value}</p>
                        <p className="text-sm md:text-base text-muted-foreground font-medium">{stat.title}</p>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
        </div>

        <Card className="mb-8 shadow-md hover:shadow-lg transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="text-2xl font-bold">Therapeutic Areas</CardTitle>
            <CardDescription className="text-base">Active drug discovery programs by disease category</CardDescription>
          </CardHeader>
          <CardContent className="px-6 pb-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {therapeuticAreas.map((area) => (
                <div key={area.name} className="p-5 border rounded-lg hover:shadow-lg hover:border-primary/20 transition-all duration-300 hover:-translate-y-0.5 bg-gradient-to-br from-card to-card/50 group">
                  <h4 className="font-semibold mb-3 text-lg group-hover:text-primary transition-colors">{area.name}</h4>
                  <div className="space-y-2 text-sm">
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">{area.targets}</span> targets • <span className="font-medium text-foreground">{area.compounds.toLocaleString()}</span> compounds
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                      <p className="text-green-600 dark:text-green-400 font-semibold">{area.successRate}% success rate</p>
                    </div>
                    <p className="text-xs text-muted-foreground pt-1 border-t border-border/50">{area.topTarget}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-8 lg:grid-cols-2 lg:gap-10">
          <Card className="shadow-md hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold">Recent Analysis Jobs</CardTitle>
              <CardDescription className="text-base mt-2">
                AlphaFold predictions and molecular docking workflows
              </CardDescription>
            </CardHeader>
            <CardContent className="px-6 pb-6">
              {isInitialLoading ? (
                <JobListSkeleton count={3} />
              ) : jobs.length === 0 ? (
                <div className="text-center py-16 text-muted-foreground">
                  <div className="mb-6 flex justify-center">
                    <div className="rounded-full bg-gradient-to-br from-primary/10 to-primary/5 p-8 border-2 border-dashed border-primary/20 animate-pulse">
                      <Beaker className="w-16 h-16 text-primary/50" />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-foreground mb-3">No jobs yet</h3>
                  <p className="text-base mb-8 max-w-md mx-auto leading-relaxed">
                    Get started by submitting your first molecular docking job or AlphaFold structure prediction.
                  </p>
                  <Button
                    onClick={() => setIsSubmitDialogOpen(true)}
                    className="gap-2 shadow-lg hover:shadow-xl transition-all duration-300"
                    size="lg"
                  >
                    <Upload className="w-4 h-4" />
                    Submit Your First Job
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <JobSearchFilter jobs={jobs} onFilteredJobsChange={setFilteredJobs} />
                  <div className="space-y-5">
                    {filteredJobs.slice(0, 5).map((job) => (
                      <div key={job.job_id} className="space-y-2">
                        <DockingJobCard job={job} />
                        {job.status === "completed" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full gap-2 bg-transparent"
                            onClick={() => handleViewResults(job.job_id)}
                          >
                            <Eye className="w-4 h-4" />
                            View Results
                          </Button>
                        )}
                      </div>
                    ))}
                    {filteredJobs.length === 0 && jobs.length > 0 && (
                      <div className="text-center py-8 text-muted-foreground">
                        <p>No jobs match your search criteria.</p>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="mt-4"
                          onClick={() => {
                            setFilteredJobs(jobs)
                          }}
                        >
                          Clear filters
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold">Health Tech Insights</CardTitle>
              <CardDescription className="text-base mt-2">AI-powered discoveries and impact metrics</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 px-6 pb-6">
              {healthTechInsights.map((insight) => (
                <div key={insight.category} className="p-4 border rounded-lg hover:shadow-md hover:border-primary/20 transition-all duration-300 group">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={insight.impact === "critical" ? "default" : "secondary"} className="group-hover:scale-105 transition-transform">{insight.category}</Badge>
                    <span className="text-xs text-muted-foreground font-medium">{insight.metric}</span>
                  </div>
                  <p className="text-sm leading-relaxed mt-2">{insight.insight}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {!connected && (
          <Card className="mt-8 border-muted">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">Optional: Connect wallet for blockchain verification</p>
                <Button variant="outline" size="sm" onClick={connect}>
                  <Wallet className="w-4 h-4 mr-2" />
                  Connect
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
      <Footer />

      <SubmitJobDialog open={isSubmitDialogOpen} onOpenChange={setIsSubmitDialogOpen} onSubmit={handleSubmitJob} />
      <KeyboardShortcutsHint />
    </div>
  )
}
