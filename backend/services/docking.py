import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import aiofiles
import logging
import json
import asyncio
import math
from collections import defaultdict

logger = logging.getLogger(__name__)

class DockingError(Exception):
    """Base exception for docking-related errors"""
    pass

class ProteinPreparationError(DockingError):
    """Error preparing protein for docking"""
    pass

class LigandPreparationError(DockingError):
    """Error preparing ligand for docking"""
    pass

class VinaExecutionError(DockingError):
    """Error executing AutoDock Vina"""
    pass

class DockingParseError(DockingError):
    """Error parsing docking results"""
    pass


class GninaExecutionError(DockingError):
    """Error executing Gnina (GPU-accelerated docking)"""
    pass


VINA_PATH = os.getenv("AUTODOCK_VINA_PATH", "/usr/local/bin/vina")
GNINA_PATH = os.getenv("GNINA_PATH", "gnina")
USE_GPU_DOCKING = os.getenv("USE_GPU_DOCKING", "0").lower() in ("1", "true", "yes")
MAX_PARALLEL_LIGANDS = int(os.getenv("MAX_PARALLEL_LIGANDS", "4"))  # Process up to 4 ligands in parallel


def _gnina_available() -> bool:
    """Check if Gnina executable is available for GPU-accelerated docking."""
    try:
        subprocess.run(
            [GNINA_PATH, "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False

async def run_autodock_vina(
    protein_pdb_path: Path,
    ligand_files: List[str],
    parameters: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Run AutoDock Vina for molecular docking with enhanced features.
    
    Args:
        protein_pdb_path: Path to protein PDB file
        ligand_files: List of ligand file contents (SDF format)
        parameters: Docking parameters (center, size, exhaustiveness, etc.)
        job_id: Unique job identifier
        
    Returns:
        Dictionary with comprehensive docking results including pose clustering and statistics
        
    Raises:
        DockingError: If docking fails
        ValueError: If inputs are invalid
    """
    # Validate inputs
    if not protein_pdb_path or not protein_pdb_path.exists():
        raise ValueError(f"Protein PDB file does not exist: {protein_pdb_path}")
    
    if not ligand_files or len(ligand_files) == 0:
        raise ValueError("At least one ligand file is required")
    
    if not parameters:
        raise ValueError("Docking parameters are required")
    
    # Validate and normalize parameters
    parameters = validate_and_normalize_parameters(parameters)
    
    output_dir = Path(f"/workspace/predictions/{job_id}/docking")
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create docking output directory for job {job_id}: {str(e)}")
        raise DockingError(f"Cannot create output directory: {str(e)}") from e
    
    logger.info(f"Starting docking for job {job_id} with {len(ligand_files)} ligand(s)")
    
    try:
        # Prepare protein (convert to PDBQT) - only once for all ligands
        protein_pdbqt = await prepare_protein(protein_pdb_path, output_dir)
        logger.info(f"Protein prepared successfully for job {job_id}")
    except ProteinPreparationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing protein for job {job_id}: {str(e)}")
        raise ProteinPreparationError(f"Failed to prepare protein: {str(e)}") from e
    
    # Process ligands with optional parallelization
    all_results = await process_ligands_parallel(
        protein_pdbqt=protein_pdbqt,
        ligand_files=ligand_files,
        parameters=parameters,
        output_dir=output_dir,
        job_id=job_id
    )
    
    if not all_results or all(all_results[i].get("binding_affinity") is None for i in range(len(all_results))):
        raise DockingError("All ligands failed to dock. Check logs for details.")
    
    # Sort by binding affinity (best score first), filtering out failed results
    valid_results = [r for r in all_results if r.get("binding_affinity") is not None]
    valid_results.sort(key=lambda x: x["binding_affinity"])
    
    # Calculate comprehensive statistics
    statistics = calculate_docking_statistics(valid_results)
    
    # Perform pose clustering for top results
    clustered_results = perform_pose_clustering(valid_results)
    
    docking_summary = {
        "total_ligands": len(ligand_files),
        "successful_ligands": len(valid_results),
        "failed_ligands": len(all_results) - len(valid_results),
        "results": all_results,
        "best_score": valid_results[0]["binding_affinity"] if valid_results else None,
        "best_ligand": valid_results[0]["ligand_name"] if valid_results else None,
        "statistics": statistics,
        "clustered_results": clustered_results,
        "parameters_used": parameters
    }
    
    best_score_str = f"{docking_summary['best_score']:.2f}" if docking_summary['best_score'] is not None else "N/A"
    logger.info(
        f"Docking completed for job {job_id}: "
        f"{len(valid_results)}/{len(ligand_files)} successful, "
        f"best score: {best_score_str} kcal/mol"
    )
    
    return docking_summary

async def prepare_protein(pdb_path: Path, output_dir: Path) -> Path:
    """Convert PDB to PDBQT format for docking"""
    if not pdb_path.exists():
        raise ProteinPreparationError(f"Protein PDB file does not exist: {pdb_path}")
    
    pdbqt_path = output_dir / "protein.pdbqt"
    
    # Check if obabel is available
    try:
        check_process = await asyncio.create_subprocess_exec(
            "obabel", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await check_process.communicate()
        if check_process.returncode != 0:
            raise ProteinPreparationError("Open Babel (obabel) is not available or not working correctly")
    except FileNotFoundError:
        raise ProteinPreparationError("Open Babel (obabel) command not found. Please install Open Babel.")
    
    # Use Open Babel or MGLTools for conversion
    cmd = [
        "obabel",
        str(pdb_path),
        "-O", str(pdbqt_path),
        "-xr"  # Add hydrogens and charges
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)  # 5 minute timeout
        except asyncio.TimeoutError:
            process.kill()
            raise ProteinPreparationError("Protein preparation timed out after 5 minutes")
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
            logger.error(f"Protein preparation failed: {error_msg}")
            raise ProteinPreparationError(f"Protein preparation failed: {error_msg}")
        
        if not pdbqt_path.exists():
            raise ProteinPreparationError(f"Protein PDBQT file was not created: {pdbqt_path}")
        
        return pdbqt_path
    except ProteinPreparationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing protein: {str(e)}")
        raise ProteinPreparationError(f"Unexpected error during protein preparation: {str(e)}") from e

async def prepare_ligand(ligand_content: str, ligand_name: str, output_dir: Path) -> Path:
    """Convert ligand SDF to PDBQT format"""
    if not ligand_content or not ligand_content.strip():
        raise LigandPreparationError(f"Ligand content is empty for {ligand_name}")
    
    sdf_path = output_dir / f"{ligand_name}.sdf"
    pdbqt_path = output_dir / f"{ligand_name}.pdbqt"
    
    # Save SDF content
    try:
        async with aiofiles.open(sdf_path, 'w') as f:
            await f.write(ligand_content)
    except IOError as e:
        logger.error(f"Failed to write ligand SDF file for {ligand_name}: {str(e)}")
        raise LigandPreparationError(f"Cannot write ligand file: {str(e)}") from e
    
    # Convert to PDBQT
    cmd = [
        "obabel",
        str(sdf_path),
        "-O", str(pdbqt_path),
        "-h",  # Add hydrogens
        "--partialcharge", "gasteiger"  # Add charges
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)  # 1 minute timeout
        except asyncio.TimeoutError:
            process.kill()
            raise LigandPreparationError(f"Ligand preparation timed out for {ligand_name}")
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
            logger.error(f"Ligand preparation failed for {ligand_name}: {error_msg}")
            raise LigandPreparationError(f"Ligand preparation failed: {error_msg}")
        
        if not pdbqt_path.exists():
            raise LigandPreparationError(f"Ligand PDBQT file was not created: {pdbqt_path}")
        
        return pdbqt_path
    except LigandPreparationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing ligand {ligand_name}: {str(e)}")
        raise LigandPreparationError(f"Unexpected error during ligand preparation: {str(e)}") from e

def validate_and_normalize_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize docking parameters with sensible defaults.
    
    Args:
        parameters: Raw parameters dictionary
        
    Returns:
        Validated and normalized parameters dictionary
    """
    normalized = {}
    
    # Grid center (required)
    normalized["center_x"] = float(parameters.get("center_x", parameters.get("grid_center_x", 0.0)))
    normalized["center_y"] = float(parameters.get("center_y", parameters.get("grid_center_y", 0.0)))
    normalized["center_z"] = float(parameters.get("center_z", parameters.get("grid_center_z", 0.0)))
    
    # Grid size (default 20Å)
    normalized["size_x"] = float(parameters.get("size_x", parameters.get("grid_size_x", 20.0)))
    normalized["size_y"] = float(parameters.get("size_y", parameters.get("grid_size_y", 20.0)))
    normalized["size_z"] = float(parameters.get("size_z", parameters.get("grid_size_z", 20.0)))
    
    # Validate grid size (reasonable range)
    for dim in ["size_x", "size_y", "size_z"]:
        if normalized[dim] < 5.0 or normalized[dim] > 100.0:
            logger.warning(f"Grid {dim} ({normalized[dim]}) is outside recommended range (5-100 Å)")
    
    # Exhaustiveness (default 8, range 1-32)
    normalized["exhaustiveness"] = int(parameters.get("exhaustiveness", 8))
    if normalized["exhaustiveness"] < 1:
        normalized["exhaustiveness"] = 1
    elif normalized["exhaustiveness"] > 32:
        normalized["exhaustiveness"] = 32
    
    # Number of modes (default 9, range 1-20)
    normalized["num_modes"] = int(parameters.get("num_modes", parameters.get("energy_range", 9)))
    if normalized["num_modes"] < 1:
        normalized["num_modes"] = 1
    elif normalized["num_modes"] > 20:
        normalized["num_modes"] = 20
    
    # Energy range (optional, for filtering poses)
    normalized["energy_range"] = float(parameters.get("energy_range", 3.0))
    
    return normalized

async def process_ligands_parallel(
    protein_pdbqt: Path,
    ligand_files: List[str],
    parameters: Dict[str, Any],
    output_dir: Path,
    job_id: str
) -> List[Dict[str, Any]]:
    """
    Process multiple ligands with optional parallelization.
    
    Args:
        protein_pdbqt: Prepared protein PDBQT file
        ligand_files: List of ligand file contents
        parameters: Docking parameters
        output_dir: Output directory
        job_id: Job identifier
        
    Returns:
        List of docking results for each ligand
    """
    async def process_single_ligand(idx: int, ligand_content: str) -> Dict[str, Any]:
        """Process a single ligand"""
        if not ligand_content or not ligand_content.strip():
            logger.warning(f"Skipping empty ligand {idx} for job {job_id}")
            return {
                "ligand_name": f"ligand_{idx}",
                "ligand_index": idx,
                "binding_affinity": None,
                "modes": [],
                "error": "Empty ligand content"
            }
        
        ligand_name = f"ligand_{idx}"
        logger.info(f"Processing {ligand_name} for job {job_id}")
        
        try:
            # Prepare ligand (convert SDF to PDBQT)
            ligand_pdbqt = await prepare_ligand(ligand_content, ligand_name, output_dir)
            
            use_gnina = (
                USE_GPU_DOCKING
                and parameters.get("use_gpu", False)
                and _gnina_available()
            )
            if use_gnina:
                logger.info("Using GPU-accelerated Gnina for %s (job %s)", ligand_name, job_id)
                result = await run_gnina_docking(
                    protein_pdbqt,
                    ligand_pdbqt,
                    parameters,
                    output_dir,
                    ligand_name
                )
            else:
                result = await run_vina_docking(
                    protein_pdbqt,
                    ligand_pdbqt,
                    parameters,
                    output_dir,
                    ligand_name
                )
            
            return {
                "ligand_name": ligand_name,
                "ligand_index": idx,
                **result
            }
        except (LigandPreparationError, VinaExecutionError, GninaExecutionError) as e:
            logger.error(f"Failed to dock {ligand_name} for job {job_id}: {str(e)}")
            return {
                "ligand_name": ligand_name,
                "ligand_index": idx,
                "binding_affinity": None,
                "modes": [],
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error docking {ligand_name} for job {job_id}: {str(e)}")
            return {
                "ligand_name": ligand_name,
                "ligand_index": idx,
                "binding_affinity": None,
                "modes": [],
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Process ligands with controlled parallelism
    if len(ligand_files) == 1:
        # Single ligand - no need for parallelization
        result = await process_single_ligand(0, ligand_files[0])
        return [result]
    else:
        # Multiple ligands - use semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(MAX_PARALLEL_LIGANDS)
        
        async def process_with_semaphore(idx: int, ligand_content: str):
            async with semaphore:
                return await process_single_ligand(idx, ligand_content)
        
        tasks = [
            process_with_semaphore(idx, ligand_content)
            for idx, ligand_content in enumerate(ligand_files)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that weren't caught
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception processing ligand {idx} for job {job_id}: {str(result)}")
                processed_results.append({
                    "ligand_name": f"ligand_{idx}",
                    "ligand_index": idx,
                    "binding_affinity": None,
                    "modes": [],
                    "error": f"Exception: {str(result)}"
                })
            else:
                processed_results.append(result)
        
        return processed_results

def calculate_docking_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics from docking results.
    
    Args:
        results: List of successful docking results
        
    Returns:
        Dictionary with statistical metrics
    """
    if not results:
        return {}
    
    affinities = [r["binding_affinity"] for r in results]
    num_modes_list = [len(r.get("modes", [])) for r in results]
    
    mean_affinity = sum(affinities) / len(affinities)
    std_affinity = math.sqrt(sum((x - mean_affinity) ** 2 for x in affinities) / len(affinities))
    
    return {
        "mean_score": mean_affinity,
        "std_score": std_affinity,
        "min_score": min(affinities),
        "max_score": max(affinities),
        "median_score": sorted(affinities)[len(affinities) // 2],
        "num_clusters": len(set(round(a, 1) for a in affinities)),  # Rough clustering by score
        "success_rate": 1.0,  # All results are successful at this point
        "mean_num_modes": sum(num_modes_list) / len(num_modes_list) if num_modes_list else 0,
        "confidence_score": min(1.0, max(0.0, (mean_affinity + 10) / 5))  # Normalize to 0-1
    }

def perform_pose_clustering(results: List[Dict[str, Any]], rmsd_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Perform simple pose clustering based on binding affinity.
    
    Args:
        results: List of docking results
        rmsd_threshold: RMSD threshold for clustering (not used in simple version)
        
    Returns:
        List of results with cluster information
    """
    if not results:
        return []
    
    # Simple clustering: group by similar binding affinity ranges
    clusters = defaultdict(list)
    
    for idx, result in enumerate(results):
        affinity = result["binding_affinity"]
        # Cluster by 1 kcal/mol bins
        cluster_id = int(affinity // 1.0)
        clusters[cluster_id].append({
            **result,
            "cluster_id": cluster_id
        })
    
    # Sort clusters by best affinity in each cluster
    clustered = []
    for cluster_id in sorted(clusters.keys()):
        cluster_results = clusters[cluster_id]
        cluster_results.sort(key=lambda x: x["binding_affinity"])
        clustered.extend(cluster_results)
    
    return clustered

async def run_vina_docking(
    protein_pdbqt: Path,
    ligand_pdbqt: Path,
    parameters: Dict[str, Any],
    output_dir: Path,
    ligand_name: str
) -> Dict[str, Any]:
    """Run AutoDock Vina docking simulation with enhanced parameter support"""
    
    if not protein_pdbqt.exists():
        raise VinaExecutionError(f"Protein PDBQT file does not exist: {protein_pdbqt}")
    
    if not ligand_pdbqt.exists():
        raise VinaExecutionError(f"Ligand PDBQT file does not exist: {ligand_pdbqt}")
    
    # Validate Vina executable
    if not os.path.exists(VINA_PATH):
        raise VinaExecutionError(f"AutoDock Vina executable not found at: {VINA_PATH}")
    
    # Parameters are already validated
    center_x = parameters["center_x"]
    center_y = parameters["center_y"]
    center_z = parameters["center_z"]
    size_x = parameters["size_x"]
    size_y = parameters["size_y"]
    size_z = parameters["size_z"]
    exhaustiveness = parameters["exhaustiveness"]
    num_modes = parameters["num_modes"]
    energy_range = parameters.get("energy_range", 3.0)
    
    output_pdbqt = output_dir / f"{ligand_name}_out.pdbqt"
    log_file = output_dir / f"{ligand_name}_log.txt"
    
    cmd = [
        VINA_PATH,
        "--receptor", str(protein_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--center_x", str(center_x),
        "--center_y", str(center_y),
        "--center_z", str(center_z),
        "--size_x", str(size_x),
        "--size_y", str(size_y),
        "--size_z", str(size_z),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
        "--out", str(output_pdbqt),
        "--log", str(log_file)
    ]
    
    # Add energy_range if specified (Vina 1.2+)
    if energy_range > 0:
        cmd.extend(["--energy_range", str(energy_range)])
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Timeout based on exhaustiveness (more exhaustive = longer time)
            # Base timeout: 2 minutes per exhaustiveness level, max 20 minutes
            timeout_seconds = min(1200, max(120, exhaustiveness * 120))
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            raise VinaExecutionError(f"Vina docking timed out after {timeout_seconds} seconds")
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
            logger.error(f"Vina docking failed for {ligand_name}: {error_msg}")
            raise VinaExecutionError(f"Vina docking failed: {error_msg}")
        
        # Parse results from log file
        try:
            result = await parse_vina_log(log_file, output_pdbqt)
            return result
        except DockingParseError as e:
            logger.error(f"Failed to parse Vina log for {ligand_name}: {str(e)}")
            raise
    except VinaExecutionError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error running Vina for {ligand_name}: {str(e)}")
        raise VinaExecutionError(f"Unexpected error during Vina execution: {str(e)}") from e

async def parse_vina_log(log_file: Path, output_pdbqt: Optional[Path] = None) -> Dict[str, Any]:
    """
    Parse AutoDock Vina log file to extract binding scores and additional information.
    
    Args:
        log_file: Path to Vina log file
        output_pdbqt: Optional path to output PDBQT file
        
    Returns:
        Dictionary with parsed docking results
    """
    if not log_file.exists():
        raise DockingParseError(f"Log file does not exist: {log_file}")
    
    modes = []
    
    try:
        async with aiofiles.open(log_file, 'r') as f:
            content = await f.read()
    except IOError as e:
        raise DockingParseError(f"Cannot read log file: {str(e)}") from e
    
    if not content:
        raise DockingParseError("Log file is empty")
    
    lines = content.split('\n')
    
    # Parse binding modes
    parsing_results = False
    for line in lines:
        if "mode |   affinity" in line or "-----+------------" in line:
            parsing_results = True
            continue
        
        if parsing_results and line.strip():
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                try:
                    mode = {
                        "mode": int(parts[0]),
                        "affinity": float(parts[1]),
                        "rmsd_lb": float(parts[2]),
                        "rmsd_ub": float(parts[3])
                    }
                    modes.append(mode)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse line in log file: {line[:100]}")
                    # Don't break - continue parsing in case there are more valid lines
                    continue
    
    if not modes:
        raise DockingParseError("No valid docking modes found in log file")
    
    # Calculate additional metrics
    best_affinity = modes[0]["affinity"]
    affinity_range = modes[-1]["affinity"] - modes[0]["affinity"] if len(modes) > 1 else 0.0
    
    result = {
        "binding_affinity": best_affinity,
        "modes": modes,
        "num_poses": len(modes),
        "affinity_range": affinity_range,
        "output_pdbqt": str(output_pdbqt) if output_pdbqt else None
    }
    
    # Add pose quality indicators
    if len(modes) > 1:
        # Calculate consistency: how similar are the top poses?
        top_3_affinities = [m["affinity"] for m in modes[:3]]
        consistency = 1.0 - (max(top_3_affinities) - min(top_3_affinities)) / abs(min(top_3_affinities))
        result["pose_consistency"] = max(0.0, min(1.0, consistency))
    
    return result


async def run_gnina_docking(
    protein_pdbqt: Path,
    ligand_pdbqt: Path,
    parameters: Dict[str, Any],
    output_dir: Path,
    ligand_name: str
) -> Dict[str, Any]:
    """
    Run Gnina (GPU-accelerated) molecular docking.
    Uses same PDBQT prep as Vina; Gnina is Vina/smina-compatible.
    """
    if not protein_pdbqt.exists():
        raise GninaExecutionError(f"Protein PDBQT file does not exist: {protein_pdbqt}")
    if not ligand_pdbqt.exists():
        raise GninaExecutionError(f"Ligand PDBQT file does not exist: {ligand_pdbqt}")

    center_x = parameters["center_x"]
    center_y = parameters["center_y"]
    center_z = parameters["center_z"]
    size_x = parameters["size_x"]
    size_y = parameters["size_y"]
    size_z = parameters["size_z"]
    exhaustiveness = parameters["exhaustiveness"]
    num_modes = parameters["num_modes"]

    output_pdbqt = output_dir / f"{ligand_name}_out.pdbqt"
    log_file = output_dir / f"{ligand_name}_log.txt"

    cmd = [
        GNINA_PATH,
        "-r", str(protein_pdbqt),
        "-l", str(ligand_pdbqt),
        "--center_x", str(center_x),
        "--center_y", str(center_y),
        "--center_z", str(center_z),
        "--size_x", str(size_x),
        "--size_y", str(size_y),
        "--size_z", str(size_z),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
        "-o", str(output_pdbqt),
        "--log", str(log_file),
    ]
    # GPU used by default; optional --device N via env not added here

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        timeout_seconds = min(1200, max(120, exhaustiveness * 120))
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            raise GninaExecutionError(f"Gnina docking timed out after {timeout_seconds} seconds")

        if process.returncode != 0:
            err = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
            logger.error("Gnina docking failed for %s: %s", ligand_name, err)
            raise GninaExecutionError(f"Gnina docking failed: {err}")

        result = await parse_gnina_log(log_file, output_pdbqt)
        return result
    except GninaExecutionError:
        raise
    except Exception as e:
        logger.error("Unexpected error running Gnina for %s: %s", ligand_name, e)
        raise GninaExecutionError(f"Unexpected error during Gnina execution: {e}") from e


async def parse_gnina_log(log_file: Path, output_pdbqt: Optional[Path] = None) -> Dict[str, Any]:
    """
    Parse Gnina log file. Gnina/smina use Vina-like affinity tables;
    we extract best affinity and modes in the same shape as parse_vina_log.
    """
    if not log_file.exists():
        raise DockingParseError(f"Gnina log file does not exist: {log_file}")
    try:
        async with aiofiles.open(log_file, "r") as f:
            content = await f.read()
    except IOError as e:
        raise DockingParseError(f"Cannot read Gnina log file: {e}") from e
    if not content:
        raise DockingParseError("Gnina log file is empty")

    modes = []
    lines = content.split("\n")
    parsing = False
    for line in lines:
        if "mode |" in line and "affinity" in line.lower():
            parsing = True
            continue
        if "-----" in line and parsing and not modes:
            continue
        if parsing and line.strip():
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                try:
                    modes.append({
                        "mode": int(parts[0]),
                        "affinity": float(parts[1]),
                        "rmsd_lb": float(parts[2]),
                        "rmsd_ub": float(parts[3]),
                    })
                except (ValueError, IndexError):
                    continue

    if not modes:
        raise DockingParseError("No valid docking modes found in Gnina log file")

    best = modes[0]["affinity"]
    affinity_range = modes[-1]["affinity"] - best if len(modes) > 1 else 0.0
    out = {
        "binding_affinity": best,
        "modes": modes,
        "num_poses": len(modes),
        "affinity_range": affinity_range,
        "output_pdbqt": str(output_pdbqt) if output_pdbqt else None,
    }
    if len(modes) > 1:
        top3 = [m["affinity"] for m in modes[:3]]
        consistency = 1.0 - (max(top3) - min(top3)) / abs(min(top3) or 1e-9)
        out["pose_consistency"] = max(0.0, min(1.0, consistency))
    return out
