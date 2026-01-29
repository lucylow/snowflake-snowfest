// Advanced AI Agent for Molecular Docking Analysis
// Provides comprehensive analysis with stakeholder-specific insights

import { API_BASE_URL, ANALYSIS_TYPES, LOG_PREFIX } from "./constants"

const VALID_ANALYSIS_TYPES: string[] = [...Object.keys(ANALYSIS_TYPES), "custom"]

export interface AIAnalysisRequest {
  jobId: string
  analysisType: "binding_affinity" | "drug_likeness" | "toxicity" | "comprehensive" | "custom"
  customPrompt?: string
  stakeholderType?: "researcher" | "investor" | "regulator" | "clinician"
  includeVisualizations?: boolean
}

export interface AIAnalysisResponse {
  analysis: {
    summary: string
    detailed_analysis: {
      binding_analysis: string
      interaction_analysis: string
      pose_quality: string
      drug_likeness: string
      clinical_insights?: unknown
      [key: string]: unknown
    }
    limitations: string[]
  }
  visualizations?: Record<string, unknown>[]
  recommendations: string[]
  confidence: number
  metadata: {
    model: string
    timestamp: string
    tokenCount: number
    costEstimate: number
    processingTime?: number
  }

  /** Optional ML/cheminformatics outputs used by dashboard panels (may be absent depending on backend). */
  admet_properties?: unknown
  toxicity_predictions?: unknown
}

class AIAgent {
  private readonly apiUrl: string

  constructor(apiUrl = API_BASE_URL) {
    this.apiUrl = apiUrl
  }

  async analyzeDockingResults(request: AIAnalysisRequest): Promise<AIAnalysisResponse> {
    if (!request || !request.jobId) {
      throw new Error("Job ID is required for AI analysis")
    }

    if (!request.analysisType) {
      throw new Error("Analysis type is required")
    }

    if (!VALID_ANALYSIS_TYPES.includes(request.analysisType)) {
      throw new Error(`Invalid analysis type: ${request.analysisType}`)
    }

    try {
      // Call backend API endpoint
      const response = await fetch(`${this.apiUrl}/api/jobs/${request.jobId}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          analysis_type: request.analysisType,
          custom_prompt: request.customPrompt,
          stakeholder_type: request.stakeholderType || "researcher",
          include_visualizations: request.includeVisualizations ?? true,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `API request failed with status ${response.status}`)
      }

      const data = await response.json()
      
      if (!data || !data.analysis) {
        throw new Error("Invalid response from AI analysis")
      }

      // Ensure metadata has processingTime if missing
      if (!data.metadata.processingTime) {
        data.metadata.processingTime = 2.0
      }

      return data
    } catch (error) {
      console.error(`${LOG_PREFIX} AI analysis failed:`, error)
      const errorMessage = error instanceof Error ? error.message : "Unknown error"
      throw new Error(`Failed to generate AI analysis: ${errorMessage}`)
    }
  }

  private async generateMockAnalysis(request: AIAnalysisRequest): Promise<AIAnalysisResponse> {
    // Simulate processing delay
    await new Promise((resolve) => setTimeout(resolve, 2000))

    const analysisTypeContent = this.getAnalysisContent(request.analysisType)
    const stakeholderRecommendations = this.getStakeholderRecommendations(request.stakeholderType || "researcher")

    return {
      analysis: {
        summary: `Comprehensive ${request.analysisType.replace(/_/g, " ")} analysis for Job ID: ${request.jobId}. ${analysisTypeContent.summary}`,
        detailed_analysis: analysisTypeContent.details,
        limitations: [
          "Analysis based on computational docking results only",
          "No experimental validation performed",
          "Limited by scoring function accuracy",
          "Results may vary with different docking parameters",
        ],
      },
      recommendations: stakeholderRecommendations,
      confidence: 0.85,
      metadata: {
        model: "gpt-4-turbo-preview",
        timestamp: new Date().toISOString(),
        tokenCount: 1500,
        costEstimate: 0.045,
      },
    }
  }

  private getAnalysisContent(analysisType: string) {
    const content = {
      binding_affinity: {
        summary:
          "The binding affinity analysis reveals strong protein-ligand interactions with a favorable docking score.",
        details: {
          binding_analysis:
            "The docking score of -8.5 kcal/mol indicates strong binding affinity. This suggests a stable protein-ligand complex with significant therapeutic potential. The binding energy is within the range typically observed for successful drug candidates.",
          interaction_analysis:
            "Multiple hydrogen bonds (5) and hydrophobic interactions (8) stabilize the complex. Key residues include Lys123, Asp456, and Phe789. The ligand forms critical interactions with the active site, suggesting high selectivity.",
          pose_quality:
            "The top 10 poses show good clustering (RMSD < 2.0 Å) indicating high confidence in binding mode prediction. Pose diversity suggests multiple binding conformations are possible.",
          drug_likeness:
            "The compound exhibits favorable drug-like properties with good bioavailability predicted. Lipinski's Rule of Five is satisfied, suggesting oral drug potential.",
        },
      },
      drug_likeness: {
        summary: "The compound demonstrates excellent drug-like properties with favorable ADMET characteristics.",
        details: {
          binding_analysis:
            "Binding interactions support drug-like behavior with optimal shape complementarity to the binding pocket.",
          interaction_analysis: "Interactions are consistent with known drug molecules targeting this protein family.",
          pose_quality: "Consistent binding poses across multiple runs suggest reliable prediction of binding mode.",
          drug_likeness:
            "Molecular weight: 425 Da (optimal range). LogP: 3.2 (good lipophilicity). H-bond donors: 2, acceptors: 6 (within limits). Predicted high oral bioavailability. Low toxicity risk based on structural alerts.",
        },
      },
      toxicity: {
        summary: "Preliminary toxicity assessment indicates low risk profile with no major structural alerts.",
        details: {
          binding_analysis:
            "Binding mode does not suggest off-target interactions with major toxicity-related proteins.",
          interaction_analysis: "No reactive functional groups identified that would raise toxicity concerns.",
          pose_quality:
            "Stable binding poses without unusual conformational strain that could lead to metabolic issues.",
          drug_likeness:
            "Low predicted hepatotoxicity (10% risk). No mutagenic or carcinogenic structural alerts detected. Predicted LD50 indicates low acute toxicity. AMES test predicted negative.",
        },
      },
      comprehensive: {
        summary: "A thorough analysis across all parameters reveals this compound as a promising drug candidate.",
        details: {
          binding_analysis:
            "Strong binding affinity (-8.5 kcal/mol) with predicted Ki in the nanomolar range (5.7 nM). Binding free energy calculations suggest stable complex formation with favorable enthalpy and entropy contributions.",
          interaction_analysis:
            "Detailed interaction network includes 5 hydrogen bonds (Asp123, Lys456, Ser789), 8 hydrophobic contacts (Phe234, Leu345, Val678), and 2 π-π stacking interactions (Phe234, Trp890). Water-mediated interactions enhance binding specificity.",
          pose_quality:
            "Excellent pose clustering with 8 of 10 poses within 1.5 Å RMSD. High confidence score (0.92) from ensemble analysis. Binding mode consistent across different docking algorithms.",
          drug_likeness:
            "Comprehensive ADMET profile: High GI absorption (85%), BBB permeant (log BB: 0.3), P-gp substrate (no), CYP inhibition (minimal), oral bioavailability (F: 78%), half-life (t1/2: 6.5 hours), clearance (moderate). Synthetic accessibility score: 3.2/10 (easy to synthesize).",
        },
      },
      custom: {
        summary: "Custom analysis tailored to your specific research questions and objectives.",
        details: {
          binding_analysis: "Focused analysis on binding characteristics relevant to your custom prompt.",
          interaction_analysis: "Detailed interaction mapping based on your specific areas of interest.",
          pose_quality: "Quality assessment aligned with your research objectives.",
          drug_likeness: "Drug-like property evaluation customized to your therapeutic area.",
        },
      },
    }

    return content[analysisType as keyof typeof content] || content.comprehensive
  }

  private getStakeholderRecommendations(stakeholder: string): string[] {
    const recommendations = {
      researcher: [
        "Proceed with molecular dynamics simulation to validate binding stability over time",
        "Conduct experimental binding assays (SPR, ITC) to confirm computational predictions",
        "Investigate structure-activity relationships with analog compounds",
        "Perform quantum mechanics calculations for interaction energy refinement",
        "Consider ADMET optimization if any red flags emerge from detailed analysis",
      ],
      investor: [
        "Strong binding affinity indicates viable drug candidate worth continued investment",
        "Patent landscape search recommended to protect intellectual property",
        "Estimated 18-24 months to IND submission with adequate funding",
        "Market opportunity in target indication shows $2.5B+ potential",
        "Consider strategic partnerships with CROs for preclinical development acceleration",
      ],
      regulator: [
        "Computational docking data supports mechanistic understanding for IND package",
        "Recommend full ADMET profiling including hERG binding, CYP interactions, and mutagenicity",
        "Toxicology studies in two species required per ICH guidelines",
        "Manufacturing process development needed to demonstrate batch consistency",
        "Stability studies under ICH conditions recommended before clinical trials",
      ],
      clinician: [
        "Mechanism of action well-defined through computational analysis",
        "Predicted safety profile suggests manageable side effect potential",
        "Dosing strategy should target plasma concentration of 10-50 nM for efficacy",
        "Monitor for drug-drug interactions given CYP involvement",
        "Patient selection criteria should consider target expression levels and biomarkers",
      ],
    }

    return recommendations[stakeholder as keyof typeof recommendations] || recommendations.researcher
  }
}

export const aiAgent = new AIAgent()
