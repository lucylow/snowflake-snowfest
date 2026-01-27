// API Client for backend communication
// Connects to the FastAPI backend for docking operations

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const REQUEST_TIMEOUT = 30000 // 30 seconds

export interface DockingParameters {
  job_id?: string
  grid_center_x: number
  grid_center_y: number
  grid_center_z: number
  grid_size_x: number
  grid_size_y: number
  grid_size_z: number
  exhaustiveness: number
  energy_range: number
  num_modes: number
  use_gpu?: boolean
  flexible_sidechains?: boolean
  flexible_residues?: string[]
  scoring_function?: string
  custom_config?: Record<string, any>
}

export interface Pose {
  pose_id: number
  score: number
  binding_energy: number
  rmsd: number
  pose_file: string
  interactions: Record<string, any>
  cluster_id: number
}

export interface DockingResult {
  job_id: string
  protein_structure: string
  ligand_structure: string
  poses: Pose[]
  best_pose: Pose
  metrics: {
    mean_score: number
    std_score: number
    min_score: number
    max_score: number
    num_clusters: number
    success_rate: number
    confidence_score: number
    mean_binding_energy?: number
    predicted_ic50?: number
    drug_likeness_score?: number
  }
  output_directory: string
  raw_results_path: string
  analysis_plots: Record<string, string>
  ai_analysis?: any
}

export interface JobStatus {
  job_id: string
  status:
    | "queued"
    | "running"
    | "completed"
    | "failed"
    | "predicting_structure"
    | "structure_predicted"
    | "docking"
    | "analyzing"
  created_at: string
  completed_at?: string
  error?: string
  progress?: number
  protein_sequence?: string
  predicted_pdb_path?: string
  plddt_score?: number
  top_binding_score?: number
  ai_report_content?: string
  blockchain_tx_hash?: string
}

export interface AIAnalysisRequest {
  job_id: string
  analysis_type: "binding_affinity" | "drug_likeness" | "toxicity" | "comprehensive" | "custom"
  custom_prompt?: string
  stakeholder_type?: "researcher" | "investor" | "regulator" | "clinician"
}

export interface ReportRequest {
  job_id: string
  report_type: "pdf" | "html" | "json"
  include_visualizations: boolean
  store_on_blockchain?: boolean
  stakeholder_type?: "researcher" | "investor" | "regulator" | "clinician"
}

class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
  ) {
    super(message)
    this.name = "APIError"
  }
}

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = REQUEST_TIMEOUT): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === "AbortError") {
      throw new APIError("Request timeout - please try again", 408, "TIMEOUT")
    }
    throw error
  }
}

class APIClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async handleResponse<T>(response: Response, operation: string): Promise<T> {
    if (!response.ok) {
      let errorMessage = `${operation} failed`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        errorMessage = `${operation} failed: ${response.statusText}`
      }
      throw new APIError(errorMessage, response.status, response.status.toString())
    }
    try {
      return await response.json()
    } catch (error) {
      throw new APIError(`Failed to parse response from ${operation}`, 500, "PARSE_ERROR")
    }
  }

  // Submit docking job
  async submitDockingJob(
    proteinFile: File,
    ligandFile: File,
    parameters: DockingParameters,
  ): Promise<{ job_id: string; status: string; message: string }> {
    if (!proteinFile || !ligandFile) {
      throw new APIError("Both protein and ligand files are required", 400, "VALIDATION_ERROR")
    }

    if (!proteinFile.name.endsWith(".pdb")) {
      throw new APIError("Protein file must be in PDB format", 400, "INVALID_FORMAT")
    }

    if (!ligandFile.name.match(/\.(sdf|mol2)$/i)) {
      throw new APIError("Ligand file must be in SDF or MOL2 format", 400, "INVALID_FORMAT")
    }

    try {
      const formData = new FormData()
      formData.append("job_name", `Docking Job ${Date.now()}`)
      formData.append("job_type", "docking_only")
      formData.append("protein_pdb", await proteinFile.text())
      formData.append("ligand_file", ligandFile)
      formData.append("docking_parameters", JSON.stringify(parameters))

      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs`, {
        method: "POST",
        body: formData,
      })

      return this.handleResponse(response, "Job submission")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Network error - unable to connect to server", 0, "NETWORK_ERROR")
    }
  }

  async submitSequenceDockingJob(
    jobName: string,
    proteinSequence: string,
    ligandFile: File,
    parameters: DockingParameters,
  ): Promise<{ job_id: string; status: string; message: string }> {
    if (!proteinSequence) {
      throw new APIError("Protein sequence is required", 400, "VALIDATION_ERROR")
    }

    if (!ligandFile) {
      throw new APIError("Ligand file is required", 400, "VALIDATION_ERROR")
    }

    if (!ligandFile.name.match(/\.(sdf|mol2)$/i)) {
      throw new APIError("Ligand file must be in SDF or MOL2 format", 400, "INVALID_FORMAT")
    }

    try {
      const formData = new FormData()
      formData.append("job_name", jobName)
      formData.append("job_type", "sequence_to_docking")
      formData.append("protein_sequence", proteinSequence)
      formData.append("ligand_file", ligandFile)
      formData.append("docking_parameters", JSON.stringify(parameters))

      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs`, {
        method: "POST",
        body: formData,
      })

      return this.handleResponse(response, "Sequence docking job submission")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Network error - unable to connect to server", 0, "NETWORK_ERROR")
    }
  }

  // Get docking status
  async getDockingStatus(jobId: string): Promise<JobStatus> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/${jobId}`)
      return this.handleResponse(response, "Status check")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to retrieve job status", 0, "NETWORK_ERROR")
    }
  }

  // Get docking results
  async getDockingResults(jobId: string): Promise<DockingResult> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/docking/results/${jobId}`)
      return this.handleResponse(response, "Results retrieval")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to retrieve docking results", 0, "NETWORK_ERROR")
    }
  }

  // Analyze with AI
  async analyzeWithAI(request: AIAnalysisRequest): Promise<any> {
    if (!request.job_id) {
      throw new APIError("Job ID is required for analysis", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/ai/analyze`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        },
        60000, // 60 seconds for AI analysis
      )

      return this.handleResponse(response, "AI analysis")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("AI analysis failed - please try again", 0, "NETWORK_ERROR")
    }
  }

  // Generate report
  async generateReport(request: ReportRequest): Promise<any> {
    if (!request.job_id) {
      throw new APIError("Job ID is required for report generation", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/report/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        },
        60000, // 60 seconds for report generation
      )

      return this.handleResponse(response, "Report generation")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Report generation failed", 0, "NETWORK_ERROR")
    }
  }

  // Get visualization
  async getVisualization(jobId: string, poseId = 0): Promise<any> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/visualization/${jobId}/${poseId}`)
      return this.handleResponse(response, "Visualization retrieval")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to load visualization", 0, "NETWORK_ERROR")
    }
  }

  // Verify blockchain transaction
  async verifyTransaction(txHash: string): Promise<any> {
    if (!txHash) {
      throw new APIError("Transaction hash is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/solana/verify/${txHash}`)
      return this.handleResponse(response, "Transaction verification")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to verify transaction", 0, "NETWORK_ERROR")
    }
  }

  connectWebSocket(jobId: string, onMessage: (data: JobStatus) => void, onError?: (error: Event) => void): WebSocket {
    const wsUrl = this.baseUrl.replace("http", "ws")
    const ws = new WebSocket(`${wsUrl}/ws/status/${jobId}`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (error) {
        console.error("[v0] WebSocket parse error:", error)
      }
    }

    ws.onerror = (error) => {
      console.error("[v0] WebSocket connection error:", error)
      if (onError) onError(error)
    }

    ws.onclose = (event) => {
      if (!event.wasClean) {
        console.warn("[v0] WebSocket closed unexpectedly, code:", event.code)
      }
    }

    return ws
  }
}

export const apiClient = new APIClient()
export { APIError }
