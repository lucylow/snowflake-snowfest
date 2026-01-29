// API Client for backend communication
// Connects to the FastAPI backend for docking operations

import { API_BASE_URL, LOG_PREFIX, REQUEST_TIMEOUT_AI_MS, REQUEST_TIMEOUT_MS } from "./constants"

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

// AlphaFold quality metrics (frontend shape)
export interface QualityMetrics {
  plddt_score: number
  confidence_regions: {
    very_high: number
    confident: number
    low: number
    very_low: number
  }
  pae_score?: number | null
  structure_length: number
  per_residue_plddt: number[]
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
  job_type?: string
  quality_metrics?: QualityMetrics | Record<string, unknown>
}

/** Map backend job (id, error_message, status) to JobStatus (job_id, error, status). */
function mapBackendJobToStatus(raw: Record<string, unknown>): JobStatus {
  const status = raw.status === "submitted" ? "queued" : (raw.status as JobStatus["status"])
  return {
    job_id: (raw.id as string) ?? (raw.job_id as string),
    status,
    created_at: (raw.created_at as string) ?? new Date().toISOString(),
    completed_at: raw.completed_at as string | undefined,
    error: (raw.error_message as string) ?? (raw.error as string),
    progress: raw.progress as number | undefined,
    protein_sequence: raw.protein_sequence as string | undefined,
    predicted_pdb_path: raw.predicted_pdb_path as string | undefined,
    plddt_score: raw.plddt_score as number | undefined,
    top_binding_score: raw.top_binding_score as number | undefined,
    ai_report_content: raw.ai_report_content as string | undefined,
    blockchain_tx_hash: raw.blockchain_tx_hash as string | undefined,
    job_type: raw.job_type as string | undefined,
    quality_metrics: raw.quality_metrics as Record<string, unknown> | undefined,
  }
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

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = REQUEST_TIMEOUT_MS,
  retries = 0,
  maxRetries = 3
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    
    // Retry on 5xx errors (server errors)
    if (!response.ok && response.status >= 500 && retries < maxRetries) {
      const retryDelay = Math.min(1000 * Math.pow(2, retries), 10000) // Exponential backoff, max 10s
      console.warn(`Server error ${response.status}, retrying in ${retryDelay}ms (attempt ${retries + 1}/${maxRetries})`)
      await new Promise(resolve => setTimeout(resolve, retryDelay))
      return fetchWithTimeout(url, options, timeout, retries + 1, maxRetries)
    }
    
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    
    // Retry on network errors
    if (retries < maxRetries) {
      const isNetworkError = error instanceof Error && (
        error.name === "AbortError" ||
        error.message.includes("Failed to fetch") ||
        error.message.includes("NetworkError") ||
        error.message.includes("TypeError")
      )
      
      if (isNetworkError) {
        const retryDelay = Math.min(1000 * Math.pow(2, retries), 10000) // Exponential backoff
        console.warn(`Network error, retrying in ${retryDelay}ms (attempt ${retries + 1}/${maxRetries})`)
        await new Promise(resolve => setTimeout(resolve, retryDelay))
        return fetchWithTimeout(url, options, timeout, retries + 1, maxRetries)
      }
    }
    
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
      let errorDetails: any = null
      
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
        errorDetails = errorData
        
        // Provide more specific error messages based on status code
        if (response.status === 400) {
          errorMessage = errorData.detail || "Invalid request. Please check your input."
        } else if (response.status === 401) {
          errorMessage = "Authentication required. Please log in."
        } else if (response.status === 403) {
          errorMessage = "You don't have permission to perform this action."
        } else if (response.status === 404) {
          errorMessage = errorData.detail || "Resource not found."
        } else if (response.status === 422) {
          errorMessage = errorData.detail || "Validation error. Please check your input."
        } else if (response.status === 429) {
          errorMessage = "Too many requests. Please try again later."
        } else if (response.status >= 500) {
          errorMessage = errorData.message || "Server error. Please try again later."
        }
      } catch {
        // If JSON parsing fails, use status text
        if (response.status >= 500) {
          errorMessage = `Server error (${response.status}). Please try again later.`
        } else {
          errorMessage = `${operation} failed: ${response.statusText}`
        }
      }
      
      const apiError = new APIError(errorMessage, response.status, response.status.toString())
      if (errorDetails) {
        // Attach error details if available
        (apiError as any).details = errorDetails
      }
      throw apiError
    }
    
    try {
      const contentType = response.headers.get("content-type")
      if (!contentType || !contentType.includes("application/json")) {
        // Handle non-JSON responses
        const text = await response.text()
        if (!text) {
          return {} as T // Empty response
        }
        throw new APIError(`Unexpected response format from ${operation}`, 500, "PARSE_ERROR")
      }
      
      return await response.json()
    } catch (error) {
      if (error instanceof APIError) {
        throw error
      }
      throw new APIError(`Failed to parse response from ${operation}`, 500, "PARSE_ERROR")
    }
  }

  // Submit docking job (multipart upload)
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

      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/upload`, {
        method: "POST",
        body: formData,
      })

      const job = await this.handleResponse<{ id: string; status: string }>(response, "Job submission")
      const status = job.status === "submitted" ? "queued" : job.status
      return {
        job_id: job.id,
        status,
        message: "Job submitted successfully",
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

      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/upload`, {
        method: "POST",
        body: formData,
      })

      const job = await this.handleResponse<{ id: string; status: string }>(response, "Sequence docking job submission")
      const status = job.status === "submitted" ? "queued" : job.status
      return {
        job_id: job.id,
        status,
        message: "Job submitted successfully",
      }
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Network error - unable to connect to server", 0, "NETWORK_ERROR")
    }
  }

  /** List jobs with optional pagination. */
  async listJobs(skip = 0, limit = 20): Promise<JobStatus[]> {
    try {
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/jobs?skip=${skip}&limit=${limit}`,
      )
      const raw = (await this.handleResponse(response, "List jobs")) as Record<string, unknown>[]
      return raw.map((j) => mapBackendJobToStatus(j))
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to list jobs", 0, "NETWORK_ERROR")
    }
  }

  /** Retry a failed job. */
  async retryJob(jobId: string): Promise<JobStatus> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }
    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/${jobId}/retry`, {
        method: "POST",
      })
      const raw = (await this.handleResponse(response, "Retry job")) as Record<string, unknown>
      return mapBackendJobToStatus(raw)
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to retry job", 0, "NETWORK_ERROR")
    }
  }

  // Get docking status
  async getDockingStatus(jobId: string): Promise<JobStatus> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/${jobId}`)
      const raw = (await this.handleResponse(response, "Status check")) as Record<string, unknown>
      return mapBackendJobToStatus(raw)
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to retrieve job status", 0, "NETWORK_ERROR")
    }
  }

  // Get docking results (frontend-shaped from GET /api/jobs/{id}/results)
  async getDockingResults(jobId: string): Promise<DockingResult> {
    if (!jobId) {
      throw new APIError("Job ID is required", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(`${this.baseUrl}/api/jobs/${jobId}/results`)
      return this.handleResponse(response, "Results retrieval") as Promise<DockingResult>
    } catch (error) {
      if (error instanceof APIError) throw error
      throw new APIError("Unable to retrieve docking results", 0, "NETWORK_ERROR")
    }
  }

  // Analyze with AI (POST /api/jobs/{id}/analyze)
  async analyzeWithAI(request: AIAnalysisRequest): Promise<any> {
    if (!request.job_id) {
      throw new APIError("Job ID is required for analysis", 400, "VALIDATION_ERROR")
    }

    try {
      const response = await fetchWithTimeout(
        `${this.baseUrl}/api/jobs/${request.job_id}/analyze`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            analysis_type: request.analysis_type,
            custom_prompt: request.custom_prompt,
            stakeholder_type: request.stakeholder_type ?? "researcher",
          }),
        },
        REQUEST_TIMEOUT_AI_MS,
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
      const response = await fetchWithTimeout(`${this.baseUrl}/api/blockchain/verify/${txHash}`)
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

  // External API methods
  async proxyExternalAPI(
    apiName: string,
    endpoint: string,
    method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
    params?: Record<string, any>,
    jsonData?: Record<string, any>,
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
        ? `?${new URLSearchParams(params as any).toString()}`
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
        ? `?${new URLSearchParams(params as any).toString()}`
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
        ? `?${new URLSearchParams(params as any).toString()}`
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
        ? `?${new URLSearchParams(params as any).toString()}`
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
