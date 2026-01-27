from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.models import JobType, JobStatus

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
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobStatusUpdate(BaseModel):
    status: JobStatus
    message: Optional[str] = None
