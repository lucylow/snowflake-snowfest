// API Client for backend communication
// Connects to the FastAPI backend for docking operations

import { API_BASE_URL, LOG_PREFIX, REQUEST_TIMEOUT_AI_MS, REQUEST_TIMEOUT_MS } from "./constants"
import {
  getMockDockingResult,
  getMockJobStatus,
  getMockAIAnalysis,
  mockDockingJobs,
  mockAlphaFoldJobs,
} from "./mock-data"

const LIGAND_EXT = /\.(sdf|mol2)$/i

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
  custom_config?: Record<string, unknown>
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
  ai_analysis?: Record<string, unknown>
}

export interface QualityMetrics {
  plddt_score: number
  pae_score?: number | null
  per_residue_plddt: number[]
  confidence_regions: {
    very_high: number  // pLDDT >= 90
    confident: number  // 70 <= pLDDT < 90
    low: number  // 50 <= pLDDT < 70
    very_low: number  // pLDDT < 50
  }
  structure_length: number
}

export interface AlphaFoldConfig {
  model_preset?: "monomer" | "monomer_ptm" | "multimer" | "multimer_v2"
  max_template_date?: string
  db_preset?: "reduced_dbs" | "full_dbs"
  use_gpu_relax?: boolean
}

export interface AlphaFoldPredictionRequest {
  job_name: string
  protein_sequence: string
  alphafold_config?: AlphaFoldConfig
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
  quality_metrics?: QualityMetrics
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

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = REQUEST_TIMEOUT_MS): Promise<Response> {
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
    if (error instanceof Error) {
      if (error.name === "AbortError") {
        throw new APIError("Request timeout - please try again", 408, "TIMEOUT")
      }
      if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
        throw new APIError("Network error - unable to connect to server. Please check your connection.", 0, "NETWORK_ERROR")
      }
      if (error.message.includes("TypeError")) {
        throw new APIError("Network request failed. Please check your connection.", 0, "NETWORK_ERROR")
      }
    }
    throw new APIError(`Request failed: ${error instanceof Error ? error.message : String(error)}`, 0, "REQUEST_ERROR")
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

    if (!LIGAND_EXT.test(ligandFile.name)) {
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
      console.error(`${LOG_PREFIX} Error submitting sequence docking job:`, error)
      throw error
    }
  }

  /**
   * Submit an AlphaFold-only structure prediction job (no docking)
   */
  async submitAlphaFoldPrediction(
    request: AlphaFoldPredictionRequest,
  ): Promise<{ id: string; status: string; job_name: string }> {
    if (!request.protein_sequence || !request.protein_sequence.trim()) {
      throw new APIError("Protein sequence is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/alphafold/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      })

      const result = await this.handleResponse(response, "AlphaFold prediction submission")
      return {
        id: result.id,
        status: result.status,
        job_name: result.job_name,
      }
    } catch (error) {
      console.error(`${LOG_PREFIX} Error submitting AlphaFold prediction:`, error)
      throw error
    }
  }
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
      console.warn(`${LOG_PREFIX} API call failed, falling back to mock data for job ${jobId}:`, error)
      // Fallback to mock data
      const mockStatus = getMockJobStatus(jobId)
      if (mockStatus) {
        return mockStatus as JobStatus
      }
      // If no mock data available, throw the original error
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
      console.warn(`${LOG_PREFIX} API call failed, falling back to mock data for job ${jobId}:`, error)
      // Fallback to mock data
      const mockResult = getMockDockingResult(jobId)
      if (mockResult) {
        return mockResult as DockingResult
      }
      // If no mock data available, throw the original error
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
        REQUEST_TIMEOUT_AI_MS,
      )

      return this.handleResponse(response, "AI analysis")
    } catch (error) {
      console.warn(
        `${LOG_PREFIX} AI analysis API call failed, falling back to mock data for job ${request.job_id}:`,
        error,
      )
      // Fallback to mock data
      const mockAnalysis = getMockAIAnalysis(
        request.job_id,
        request.stakeholder_type || "researcher",
      )
      if (mockAnalysis) {
        return mockAnalysis
      }
      // If no mock data available, throw the original error
      if (error instanceof APIError) throw error
      throw new APIError("AI analysis failed - please try again", 0, "NETWORK_ERROR")
    }
  }

  // Generate report
  async generateReport(request: ReportRequest): Promise<Record<string, unknown>> {
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
  async getVisualization(jobId: string, poseId = 0): Promise<Record<string, unknown>> {
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
    // Handle both http and https protocols correctly
    const wsUrl = this.baseUrl.replace(/^https?/, (match) => match === "https" ? "wss" : "ws")
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

  // External API methods
  async proxyExternalAPI(
    apiName: string,
    endpoint: string,
    method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
    params?: Record<string, unknown>,
    jsonData?: Record<string, unknown>,
    headers?: Record<string, string>,
    apiKey?: string,
    baseUrl?: string,
  ): Promise<any> {
    if (!apiName || !endpoint) {
      throw new APIError("API name and endpoint are required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/external/proxy`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            api_name: apiName,
            endpoint,
            method,
            params,
            json_data: jsonData,
            headers,
            api_key: apiKey,
            base_url: baseUrl,
          }),
        },
        60000, // 60 seconds for external API calls
      )

      return this.handleResponse(response, "External API proxy")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("External API request failed", 0, "NETWORK_ERROR")
    }
  }

  async getPubChemData(
    endpoint: string,
    params?: Record<string, any>,
  ): Promise<any> {
    try {
      const queryString = params
        ? `?${new URLSearchParams(params as Record<string, string>).toString()}`
        : ""
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/external/pubchem/${endpoint}${queryString}`,
      )
      return this.handleResponse(response, "PubChem API")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("PubChem API request failed", 0, "NETWORK_ERROR")
    }
  }

  async getChEMBLData(
    endpoint: string,
    params?: Record<string, any>,
  ): Promise<any> {
    try {
      const queryString = params
        ? `?${new URLSearchParams(params as Record<string, string>).toString()}`
        : ""
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/external/chembl/${endpoint}${queryString}`,
      )
      return this.handleResponse(response, "ChEMBL API")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("ChEMBL API request failed", 0, "NETWORK_ERROR")
    }
  }

  async getUniProtData(
    endpoint: string,
    params?: Record<string, any>,
  ): Promise<any> {
    try {
      const queryString = params
        ? `?${new URLSearchParams(params as Record<string, string>).toString()}`
        : ""
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/external/uniprot/${endpoint}${queryString}`,
      )
      return this.handleResponse(response, "UniProt API")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("UniProt API request failed", 0, "NETWORK_ERROR")
    }
  }

  async getPDBData(
    endpoint: string,
    params?: Record<string, any>,
  ): Promise<any> {
    try {
      const queryString = params
        ? `?${new URLSearchParams(params as Record<string, string>).toString()}`
        : ""
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/external/pdb/${endpoint}${queryString}`,
      )
      return this.handleResponse(response, "PDB API")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("PDB API request failed", 0, "NETWORK_ERROR")
    }
  }

  async listAvailableAPIs(): Promise<any> {
    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/external/apis`)
      return this.handleResponse(response, "List APIs")
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Failed to list available APIs", 0, "NETWORK_ERROR")
    }
  }
}

export const apiClient = new APIClient()
export { APIError }
