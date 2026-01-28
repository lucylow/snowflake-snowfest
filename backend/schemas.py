from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.models import JobType, JobStatus

class AlphaFoldConfig(BaseModel):
    """Configuration for AlphaFold structure prediction"""
    model_preset: str = Field(default="monomer", description="Model preset: monomer, monomer_ptm, multimer, multimer_v2")
    max_template_date: Optional[str] = Field(None, description="Maximum template date (YYYY-MM-DD)")
    db_preset: str = Field(default="reduced_dbs", description="Database preset: reduced_dbs or full_dbs")
    use_gpu_relax: bool = Field(default=True, description="Use GPU-accelerated relaxation")

class AlphaFoldPredictionRequest(BaseModel):
    """Request for AlphaFold-only structure prediction"""
    job_name: str = Field(..., description="Name for the job")
    protein_sequence: str = Field(..., description="Amino acid sequence in FASTA format")
    alphafold_config: Optional[AlphaFoldConfig] = Field(None, description="AlphaFold configuration options")

class AlphaFoldPredictionResponse(BaseModel):
    """Response for AlphaFold structure prediction"""
    id: str
    job_name: str
    status: JobStatus
    protein_sequence: Optional[str] = None
    predicted_pdb_path: Optional[str] = None
    plddt_score: Optional[float] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    job_name: str = Field(..., description="Name for the job")
    job_type: JobType = Field(default=JobType.DOCKING_ONLY, description="Type of job to run")
    
    # For DOCKING_ONLY
    protein_pdb: Optional[str] = Field(None, description="PDB file content as string")
    
    # For SEQUENCE_TO_DOCKING
    protein_sequence: Optional[str] = Field(None, description="Amino acid sequence in FASTA format")
    
    # Common fields
    ligand_files: List[str] = Field(..., description="List of ligand file contents (SDF format)")
    docking_parameters: Dict[str, Any] = Field(default_factory=dict, description="Docking parameters")

class JobResponse(BaseModel):
    id: str
    job_name: str
    job_type: JobType
    status: JobStatus
    protein_pdb_path: Optional[str] = None
    protein_sequence: Optional[str] = None
    predicted_pdb_path: Optional[str] = None
    plddt_score: Optional[float] = None
    top_binding_score: Optional[float] = None
    ai_report_content: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    error_message: Optional[str] = None
    progress: Optional[float] = None  # Progress percentage (0-100)
    progress_message: Optional[str] = None  # Human-readable progress message
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobStatusUpdate(BaseModel):
    status: JobStatus
    message: Optional[str] = None

class AIAnalysisRequest(BaseModel):
    """Request model for AI analysis"""
    analysis_type: str = Field(..., description="Type of analysis: binding_affinity, drug_likeness, toxicity, comprehensive, or custom")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for analysis")
    stakeholder_type: str = Field(default="researcher", description="Stakeholder perspective: researcher, investor, regulator, or clinician")
    include_visualizations: bool = Field(default=True, description="Include visualization data")

class AIAnalysisResponse(BaseModel):
    """Response model for AI analysis"""
    analysis: Dict[str, Any] = Field(..., description="Analysis results")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    confidence: float = Field(..., description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the analysis")
    molecular_properties: Optional[Dict[str, Any]] = Field(None, description="ML-predicted molecular properties")
    admet_properties: Optional[Dict[str, Any]] = Field(None, description="ADMET property predictions")
    toxicity_predictions: Optional[Dict[str, Any]] = Field(None, description="Toxicity predictions")

class MolecularPropertiesResponse(BaseModel):
    """Response model for ML-powered molecular property predictions"""
    ligand_name: str
    molecular_properties: Dict[str, Any] = Field(..., description="Basic molecular descriptors")
    drug_likeness: Dict[str, Any] = Field(..., description="Drug-likeness scores (Lipinski, QED, SA)")
    admet: Dict[str, Any] = Field(..., description="ADMET property predictions")
    toxicity: Dict[str, Any] = Field(..., description="Toxicity predictions")
    binding_affinity_prediction: Dict[str, Any] = Field(..., description="ML-predicted binding affinity")
    overall_score: Dict[str, Any] = Field(..., description="Overall drug candidate score")

class DrugLikenessScores(BaseModel):
    """Drug-likeness scoring results"""
    lipinski_rule_of_five: Dict[str, Any]
    qed_score: float
    veber_rule: Dict[str, Any]
    egan_rule: Dict[str, Any]
    muegge_rule: Dict[str, Any]
    synthetic_accessibility: Dict[str, Any]
    overall_drug_likeness_score: float

class ADMETProperties(BaseModel):
    """ADMET property predictions"""
    absorption: Dict[str, Any]
    distribution: Dict[str, Any]
    metabolism: Dict[str, Any]
    excretion: Dict[str, Any]

class ToxicityPredictions(BaseModel):
    """Toxicity prediction results"""
    structural_alerts: Dict[str, Any]
    ld50: Dict[str, Any]
    hepatotoxicity: Dict[str, Any]
    mutagenicity: Dict[str, Any]
    carcinogenicity: Dict[str, Any]
    herg_inhibition: Dict[str, Any]
    skin_sensitization: Dict[str, Any]
    overall_toxicity_risk: Dict[str, Any]
