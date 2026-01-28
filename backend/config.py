"""
Configuration management for the backend application.
Centralizes all configuration settings with environment variable support.
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "SNOWFLAKE API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    RELOAD: bool = Field(default=False, env="RELOAD")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./snowflake.db",
        env="DATABASE_URL"
    )
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    DB_POOL_SIZE: int = Field(default=5, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # File Storage
    WORKSPACE_DIR: Path = Field(
        default=Path("/workspace"),
        env="WORKSPACE_DIR"
    )
    UPLOADS_DIR: Path = Field(
        default=Path("/workspace/uploads"),
        env="UPLOADS_DIR"
    )
    PREDICTIONS_DIR: Path = Field(
        default=Path("/workspace/predictions"),
        env="PREDICTIONS_DIR"
    )
    CACHE_DIR: Path = Field(
        default=Path("/workspace/cache"),
        env="CACHE_DIR"
    )
    
    # AlphaFold
    ALPHAFOLD_DOCKER_IMAGE: str = Field(
        default="alphafold",
        env="ALPHAFOLD_DOCKER_IMAGE"
    )
    ALPHAFOLD_DATA_DIR: Path = Field(
        default=Path("/data/alphafold"),
        env="ALPHAFOLD_DATA_DIR"
    )
    ALPHAFOLD_USE_CLOUD_API: bool = Field(
        default=False,
        env="ALPHAFOLD_USE_CLOUD_API"
    )
    BIONEMO_API_KEY: Optional[str] = Field(default=None, env="BIONEMO_API_KEY")
    
    # Docking
    AUTODOCK_VINA_PATH: str = Field(
        default="/usr/local/bin/vina",
        env="AUTODOCK_VINA_PATH"
    )
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Blockchain
    SOLANA_RPC_URL: str = Field(
        default="https://api.devnet.solana.com",
        env="SOLANA_RPC_URL"
    )
    SOLANA_PRIVATE_KEY: Optional[str] = Field(
        default=None,
        env="SOLANA_PRIVATE_KEY"
    )
    
    # Redis/Celery
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # External APIs - PubChem
    PUBCHEM_BASE_URL: str = Field(
        default="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        env="PUBCHEM_BASE_URL"
    )
    PUBCHEM_API_KEY: Optional[str] = Field(default=None, env="PUBCHEM_API_KEY")
    
    # External APIs - ChEMBL
    CHEMBL_BASE_URL: str = Field(
        default="https://www.ebi.ac.uk/chembl/api/data",
        env="CHEMBL_BASE_URL"
    )
    CHEMBL_API_KEY: Optional[str] = Field(default=None, env="CHEMBL_API_KEY")
    
    # External APIs - UniProt
    UNIPROT_BASE_URL: str = Field(
        default="https://rest.uniprot.org",
        env="UNIPROT_BASE_URL"
    )
    UNIPROT_API_KEY: Optional[str] = Field(default=None, env="UNIPROT_API_KEY")
    
    # External APIs - PDB
    PDB_BASE_URL: str = Field(
        default="https://data.rcsb.org/rest/v1",
        env="PDB_BASE_URL"
    )
    PDB_API_KEY: Optional[str] = Field(default=None, env="PDB_API_KEY")
    
    # External API Settings
    EXTERNAL_API_TIMEOUT: float = Field(default=30.0, env="EXTERNAL_API_TIMEOUT")
    EXTERNAL_API_MAX_RETRIES: int = Field(default=3, env="EXTERNAL_API_MAX_RETRIES")
    EXTERNAL_API_RETRY_DELAY: float = Field(default=1.0, env="EXTERNAL_API_RETRY_DELAY")
    
    # Security
    API_KEY_HEADER: Optional[str] = Field(default=None, env="API_KEY_HEADER")
    RATE_LIMIT_ENABLED: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("WORKSPACE_DIR", "UPLOADS_DIR", "PREDICTIONS_DIR", "CACHE_DIR", "ALPHAFOLD_DATA_DIR", pre=True)
    def parse_path(cls, v):
        """Parse path from string."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
