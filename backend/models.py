from sqlalchemy import Column, String, Text, Enum as SQLEnum, DateTime, Float, JSON, Index
from sqlalchemy.sql import func
from backend.database import Base
import enum
from datetime import datetime

class JobType(str, enum.Enum):
    DOCKING_ONLY = "docking_only"
    SEQUENCE_TO_DOCKING = "sequence_to_docking"

class JobStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PREDICTING_STRUCTURE = "predicting_structure"
    STRUCTURE_PREDICTED = "structure_predicted"
    DOCKING = "docking"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    job_name = Column(String, nullable=False, index=True)
    job_type = Column(SQLEnum(JobType), nullable=False, default=JobType.DOCKING_ONLY, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.SUBMITTED, index=True)
    
    # For DOCKING_ONLY jobs
    protein_pdb_path = Column(String, nullable=True)
    
    # For SEQUENCE_TO_DOCKING jobs
    protein_sequence = Column(Text, nullable=True)
    predicted_pdb_path = Column(String, nullable=True)
    plddt_score = Column(Float, nullable=True)  # AlphaFold confidence score
    
    # Ligand information
    ligand_files = Column(JSON, nullable=True)
    
    # Docking parameters and results
    docking_parameters = Column(JSON, nullable=True)
    docking_results = Column(JSON, nullable=True)
    top_binding_score = Column(Float, nullable=True)
    
    # AI Report
    ai_report_content = Column(Text, nullable=True)
    
    # Blockchain verification
    blockchain_tx_hash = Column(String, nullable=True, index=True)
    structure_hash = Column(String, nullable=True)
    report_hash = Column(String, nullable=True)
    
    # Metadata
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)

# Add composite indexes for common query patterns
Index('idx_job_status_created', Job.status, Job.created_at)
Index('idx_job_type_status', Job.job_type, Job.status)
