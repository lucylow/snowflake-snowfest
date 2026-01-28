import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import aiofiles

logger = logging.getLogger(__name__)

class AlphaFoldError(Exception):
    """Base exception for AlphaFold-related errors"""
    pass

class AlphaFoldDockerError(AlphaFoldError):
    """Error running AlphaFold in Docker"""
    pass

class AlphaFoldAPIError(AlphaFoldError):
    """Error calling AlphaFold cloud API"""
    pass

class AlphaFoldCacheError(AlphaFoldError):
    """Error accessing AlphaFold cache"""
    pass

ALPHAFOLD_IMAGE = os.getenv("ALPHAFOLD_DOCKER_IMAGE", "alphafold")
ALPHAFOLD_DATA_DIR = os.getenv("ALPHAFOLD_DATA_DIR", "/data/alphafold")
USE_CLOUD_API = os.getenv("ALPHAFOLD_USE_CLOUD_API", "false").lower() == "true"

async def run_alphafold(sequence: str, job_id: str) -> Tuple[Path, float]:
    """
    Run AlphaFold structure prediction on a protein sequence.
    
    Args:
        sequence: Amino acid sequence (FASTA format)
        job_id: Unique job identifier
        
    Returns:
        Tuple of (predicted_pdb_path, plddt_confidence_score)
        
    Raises:
        AlphaFoldError: If prediction fails
        ValueError: If sequence is invalid
    """
    if not sequence or not sequence.strip():
        raise ValueError("Protein sequence cannot be empty")
    
    if len(sequence) < 10:
        raise ValueError("Protein sequence too short (minimum 10 amino acids)")
    
    if len(sequence) > 10000:
        raise ValueError("Protein sequence too long (maximum 10000 amino acids)")
    
    # Validate sequence contains only valid amino acids
    valid_amino_acids = set("ACDEFGHIKLMNPQRSTVWY")
    if not all(aa in valid_amino_acids for aa in sequence.upper()):
        raise ValueError("Sequence contains invalid amino acid characters")
    
    try:
        # Check cache first
        cached_result = await get_cached_structure(sequence)
        if cached_result:
            logger.info(f"Using cached structure for job {job_id}")
            return cached_result
        
        # Choose between local Docker or cloud API
        if USE_CLOUD_API:
            return await run_alphafold_cloud(sequence, job_id)
        else:
            return await run_alphafold_docker(sequence, job_id)
    except (AlphaFoldError, ValueError) as e:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_alphafold for job {job_id}: {str(e)}", exc_info=True)
        raise AlphaFoldError(f"Failed to run AlphaFold prediction: {str(e)}") from e

async def run_alphafold_docker(sequence: str, job_id: str) -> Tuple[Path, float]:
    """Run AlphaFold using local Docker container"""
    output_dir = Path(f"/workspace/predictions/{job_id}")
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory for job {job_id}: {str(e)}")
        raise AlphaFoldDockerError(f"Cannot create output directory: {str(e)}") from e
    
    # Create temporary FASTA file
    fasta_content = f">target\n{sequence}"
    fasta_path = output_dir / "input.fasta"
    
    try:
        async with aiofiles.open(fasta_path, 'w') as f:
            await f.write(fasta_content)
    except IOError as e:
        logger.error(f"Failed to write FASTA file for job {job_id}: {str(e)}")
        raise AlphaFoldDockerError(f"Cannot write input FASTA file: {str(e)}") from e
    
    # Check if Docker is available
    try:
        check_process = await asyncio.create_subprocess_exec(
            "docker", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await check_process.communicate()
        if check_process.returncode != 0:
            raise AlphaFoldDockerError("Docker is not available or not running")
    except FileNotFoundError:
        raise AlphaFoldDockerError("Docker command not found. Please install Docker.")
    except Exception as e:
        logger.warning(f"Docker availability check failed: {str(e)}")
    
    try:
        # Run AlphaFold via Docker
        cmd = [
            "docker", "run", "--gpus", "all", "--rm",
            "-v", f"{ALPHAFOLD_DATA_DIR}:/data",
            "-v", f"{output_dir}:/output",
            "-v", f"{fasta_path}:/input.fasta",
            ALPHAFOLD_IMAGE,
            "--fasta_paths=/input.fasta",
            "--max_template_date=2024-01-01",
            "--db_preset=reduced_dbs",
            "--model_preset=monomer",
            "--data_dir=/data",
            "--output_dir=/output",
            "--use_gpu_relax=true"
        ]
        
        logger.info(f"Running AlphaFold for job {job_id}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Failed to start Docker process for job {job_id}: {str(e)}")
            raise AlphaFoldDockerError(f"Cannot start AlphaFold Docker container: {str(e)}") from e
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3600)  # 1 hour timeout
        except asyncio.TimeoutError:
            logger.error(f"AlphaFold Docker process timed out for job {job_id}")
            process.kill()
            raise AlphaFoldDockerError("AlphaFold prediction timed out after 1 hour")
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
            logger.error(f"AlphaFold failed for job {job_id}: {error_msg}")
            raise AlphaFoldDockerError(f"AlphaFold prediction failed: {error_msg}")
        
        # Find the best predicted PDB file (ranked_0.pdb)
        predicted_pdb = output_dir / "ranked_0.pdb"
        if not predicted_pdb.exists():
            # Fallback to any .pdb file
            pdb_files = list(output_dir.glob("*.pdb"))
            if not pdb_files:
                raise AlphaFoldDockerError("No PDB file generated by AlphaFold. Check Docker logs for details.")
            predicted_pdb = pdb_files[0]
            logger.warning(f"Using fallback PDB file {predicted_pdb} for job {job_id}")
        
        # Extract pLDDT score from result
        try:
            plddt_score = await extract_plddt_score(output_dir)
        except Exception as e:
            logger.warning(f"Failed to extract pLDDT score for job {job_id}: {str(e)}")
            plddt_score = 0.0
        
        # Cache the result (non-blocking)
        try:
            await cache_structure(sequence, predicted_pdb, plddt_score)
        except Exception as e:
            logger.warning(f"Failed to cache structure for job {job_id}: {str(e)}")
            # Don't fail the whole operation if caching fails
        
        logger.info(f"AlphaFold completed for job {job_id}, pLDDT: {plddt_score:.2f}")
        return predicted_pdb, plddt_score
        
    except AlphaFoldDockerError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error running AlphaFold Docker for job {job_id}: {str(e)}", exc_info=True)
        raise AlphaFoldDockerError(f"Unexpected error during AlphaFold prediction: {str(e)}") from e

async def run_alphafold_cloud(sequence: str, job_id: str) -> Tuple[Path, float]:
    """Run AlphaFold using NVIDIA BioNeMo API via Snowflake"""
    import httpx
    
    api_key = os.getenv("BIONEMO_API_KEY")
    if not api_key:
        raise AlphaFoldAPIError("BIONEMO_API_KEY not set for cloud API")
    
    output_dir = Path(f"/workspace/predictions/{job_id}")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory for job {job_id}: {str(e)}")
        raise AlphaFoldAPIError(f"Cannot create output directory: {str(e)}") from e
    
    logger.info(f"Submitting job {job_id} to BioNeMo Cloud API")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Submit prediction request
            try:
                response = await client.post(
                    "https://api.bionemo.nvidia.com/v1/protein/structure/predict",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "sequence": sequence,
                        "model": "alphafold2",
                        "output_format": "pdb",
                        "include_confidence": True
                    }
                )
            except httpx.TimeoutException:
                raise AlphaFoldAPIError("BioNeMo API request timed out after 5 minutes")
            except httpx.NetworkError as e:
                raise AlphaFoldAPIError(f"Network error connecting to BioNeMo API: {str(e)}")
            except httpx.RequestError as e:
                raise AlphaFoldAPIError(f"Request error to BioNeMo API: {str(e)}")
            
            if response.status_code == 401:
                raise AlphaFoldAPIError("Invalid API key for BioNeMo API")
            elif response.status_code == 429:
                raise AlphaFoldAPIError("BioNeMo API rate limit exceeded. Please try again later.")
            elif response.status_code >= 500:
                raise AlphaFoldAPIError(f"BioNeMo API server error (status {response.status_code})")
            elif response.status_code != 200:
                error_text = response.text[:500]  # Limit error message length
                raise AlphaFoldAPIError(f"BioNeMo API error (status {response.status_code}): {error_text}")
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from BioNeMo API for job {job_id}: {str(e)}")
                raise AlphaFoldAPIError("Invalid response format from BioNeMo API")
            
            # Download predicted structure
            pdb_url = result.get("pdb_url")
            if not pdb_url:
                raise AlphaFoldAPIError("No PDB URL returned from BioNeMo API")
            
            try:
                pdb_response = await client.get(pdb_url, timeout=60.0)
                if pdb_response.status_code != 200:
                    raise AlphaFoldAPIError(f"Failed to download PDB file (status {pdb_response.status_code})")
            except httpx.TimeoutException:
                raise AlphaFoldAPIError("Timeout downloading PDB file from BioNeMo")
            except httpx.RequestError as e:
                raise AlphaFoldAPIError(f"Error downloading PDB file: {str(e)}")
            
            predicted_pdb = output_dir / "predicted_structure.pdb"
            
            try:
                async with aiofiles.open(predicted_pdb, 'wb') as f:
                    await f.write(pdb_response.content)
            except IOError as e:
                logger.error(f"Failed to write PDB file for job {job_id}: {str(e)}")
                raise AlphaFoldAPIError(f"Cannot save predicted structure: {str(e)}") from e
            
            # Extract confidence score
            plddt_score = result.get("plddt_score", 0.0)
            if not isinstance(plddt_score, (int, float)):
                logger.warning(f"Invalid pLDDT score type for job {job_id}, using default 0.0")
                plddt_score = 0.0
            
            # Cache the result (non-blocking)
            try:
                await cache_structure(sequence, predicted_pdb, float(plddt_score))
            except Exception as e:
                logger.warning(f"Failed to cache structure for job {job_id}: {str(e)}")
            
            logger.info(f"BioNeMo prediction completed for job {job_id}, pLDDT: {plddt_score:.2f}")
            return predicted_pdb, float(plddt_score)
            
    except AlphaFoldAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in BioNeMo API call for job {job_id}: {str(e)}", exc_info=True)
        raise AlphaFoldAPIError(f"Unexpected error calling BioNeMo API: {str(e)}") from e

async def extract_plddt_score(output_dir: Path) -> float:
    """Extract average pLDDT confidence score from AlphaFold output"""
    # Look for ranking_debug.json which contains pLDDT scores
    ranking_file = output_dir / "ranking_debug.json"
    
    if ranking_file.exists():
        try:
            async with aiofiles.open(ranking_file, 'r') as f:
                content = await f.read()
                try:
                    data = json.loads(content)
                    # Get pLDDT for the top-ranked model
                    if "plddts" in data and data["plddts"]:
                        score = data["plddts"].get("ranked_0")
                        if score is not None:
                            return float(score)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Failed to parse ranking_debug.json: {str(e)}")
        except IOError as e:
            logger.warning(f"Failed to read ranking_debug.json: {str(e)}")
    
    # Fallback: parse from PDB file B-factors (which store pLDDT)
    pdb_file = output_dir / "ranked_0.pdb"
    if not pdb_file.exists():
        # Try any PDB file
        pdb_files = list(output_dir.glob("*.pdb"))
        if pdb_files:
            pdb_file = pdb_files[0]
    
    if pdb_file.exists():
        try:
            plddts = []
            async with aiofiles.open(pdb_file, 'r') as f:
                async for line in f:
                    if line.startswith("ATOM"):
                        try:
                            plddt_str = line[60:66].strip()
                            if plddt_str:
                                plddt = float(plddt_str)
                                if 0 <= plddt <= 100:  # Valid pLDDT range
                                    plddts.append(plddt)
                        except (ValueError, IndexError):
                            continue
            
            if plddts:
                avg_score = sum(plddts) / len(plddts)
                logger.info(f"Extracted pLDDT score from PDB: {avg_score:.2f}")
                return avg_score
        except IOError as e:
            logger.warning(f"Failed to read PDB file for pLDDT extraction: {str(e)}")
    
    # Default fallback
    logger.warning("Could not extract pLDDT score, using default 0.0")
    return 0.0

async def get_cached_structure(sequence: str) -> Optional[Tuple[Path, float]]:
    """Check if structure prediction is cached"""
    try:
        seq_hash = hashlib.sha256(sequence.encode()).hexdigest()
        cache_dir = Path("/workspace/cache")
        
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create cache directory: {str(e)}")
            return None
        
        cache_pdb = cache_dir / f"{seq_hash}.pdb"
        cache_meta = cache_dir / f"{seq_hash}.meta"
        
        if cache_pdb.exists() and cache_meta.exists():
            try:
                async with aiofiles.open(cache_meta, 'r') as f:
                    import json
                    content = await f.read()
                    try:
                        meta = json.loads(content)
                        plddt_score = meta.get("plddt_score", 0.0)
                        if not isinstance(plddt_score, (int, float)):
                            logger.warning(f"Invalid pLDDT score in cache metadata: {plddt_score}")
                            return None
                        return cache_pdb, float(plddt_score)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Invalid cache metadata format: {str(e)}")
                        return None
            except IOError as e:
                logger.warning(f"Failed to read cache metadata: {str(e)}")
                return None
        
        return None
    except Exception as e:
        logger.warning(f"Error checking cache: {str(e)}")
        return None

async def cache_structure(sequence: str, pdb_path: Path, plddt_score: float):
    """Cache structure prediction result"""
    try:
        if not pdb_path.exists():
            logger.warning(f"Cannot cache structure: PDB file does not exist: {pdb_path}")
            return
        
        seq_hash = hashlib.sha256(sequence.encode()).hexdigest()
        cache_dir = Path("/workspace/cache")
        
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create cache directory: {str(e)}")
            return
        
        cache_pdb = cache_dir / f"{seq_hash}.pdb"
        cache_meta = cache_dir / f"{seq_hash}.meta"
        
        try:
            # Copy PDB file
            async with aiofiles.open(pdb_path, 'rb') as src:
                content = await src.read()
            async with aiofiles.open(cache_pdb, 'wb') as dst:
                await dst.write(content)
        except IOError as e:
            logger.warning(f"Failed to copy PDB file to cache: {str(e)}")
            return
        
        # Save metadata
        try:
            import json
            meta = {
                "sequence_hash": seq_hash,
                "plddt_score": float(plddt_score),
                "cached_at": datetime.now().isoformat()
            }
            async with aiofiles.open(cache_meta, 'w') as f:
                await f.write(json.dumps(meta))
            
            logger.info(f"Cached structure with hash {seq_hash}")
        except (IOError, ValueError) as e:
            logger.warning(f"Failed to write cache metadata: {str(e)}")
            # Try to clean up partial cache
            try:
                if cache_pdb.exists():
                    cache_pdb.unlink()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Unexpected error caching structure: {str(e)}")
