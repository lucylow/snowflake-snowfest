import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiofiles
import logging
import asyncio
import math
from collections import defaultdict
import statistics

from backend.config import settings

logger = logging.getLogger(__name__)

# Constants
DEFAULT_GRID_SIZE = 20.0
MIN_GRID_SIZE = 5.0
MAX_GRID_SIZE = 100.0
DEFAULT_EXHAUSTIVENESS = 8
MIN_EXHAUSTIVENESS = 1
MAX_EXHAUSTIVENESS = 32
DEFAULT_NUM_MODES = 9
MIN_NUM_MODES = 1
MAX_NUM_MODES = 20
DEFAULT_ENERGY_RANGE = 3.0
PROTEIN_PREP_TIMEOUT = 300  # 5 minutes
LIGAND_PREP_TIMEOUT = 60  # 1 minute
GNINA_VERSION_CHECK_TIMEOUT = 5
BASE_DOCKING_TIMEOUT = 120  # 2 minutes base
MAX_DOCKING_TIMEOUT = 1200  # 20 minutes max
POSE_CLUSTERING_BIN_SIZE = 1.0  # kcal/mol bins for clustering
POSE_CONSISTENCY_TOP_N = 3

# Configuration from settings
VINA_PATH = settings.AUTODOCK_VINA_PATH
GNINA_PATH = settings.GNINA_PATH
USE_GPU_DOCKING = settings.USE_GPU_DOCKING
MAX_PARALLEL_LIGANDS = settings.MAX_PARALLEL_LIGANDS


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


async def _gnina_available() -> bool:
    """Check if Gnina executable is available for GPU-accelerated docking."""
    try:
        process = await asyncio.create_subprocess_exec(
            GNINA_PATH, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=GNINA_VERSION_CHECK_TIMEOUT)
        return process.returncode == 0
    except (FileNotFoundError, asyncio.TimeoutExpired, OSError):
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
    
    output_dir = settings.PREDICTIONS_DIR / job_id / "docking"
    
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
    docking_stats = calculate_docking_statistics(valid_results)
    
    # Perform pose clustering for top results
    clustered_results = perform_pose_clustering(valid_results)
    
    docking_summary = {
        "total_ligands": len(ligand_files),
        "successful_ligands": len(valid_results),
        "failed_ligands": len(all_results) - len(valid_results),
        "results": all_results,
        "best_score": valid_results[0]["binding_affinity"] if valid_results else None,
        "best_ligand": valid_results[0]["ligand_name"] if valid_results else None,
        "statistics": docking_stats,
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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=PROTEIN_PREP_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            raise ProteinPreparationError(
                f"Protein preparation timed out after {PROTEIN_PREP_TIMEOUT} seconds"
            )
        
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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=LIGAND_PREP_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            raise LigandPreparationError(
                f"Ligand preparation timed out for {ligand_name} "
                f"after {LIGAND_PREP_TIMEOUT} seconds"
            )
        
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
    normalized["size_x"] = float(
        parameters.get("size_x", parameters.get("grid_size_x", DEFAULT_GRID_SIZE))
    )
    normalized["size_y"] = float(
        parameters.get("size_y", parameters.get("grid_size_y", DEFAULT_GRID_SIZE))
    )
    normalized["size_z"] = float(
        parameters.get("size_z", parameters.get("grid_size_z", DEFAULT_GRID_SIZE))
    )
    
    # Validate grid size (reasonable range)
    for dim in ["size_x", "size_y", "size_z"]:
        if normalized[dim] < MIN_GRID_SIZE or normalized[dim] > MAX_GRID_SIZE:
            logger.warning(
                f"Grid {dim} ({normalized[dim]}) is outside recommended range "
                f"({MIN_GRID_SIZE}-{MAX_GRID_SIZE} Å)"
            )
    
    # Exhaustiveness (default 8, range 1-32)
    normalized["exhaustiveness"] = int(parameters.get("exhaustiveness", DEFAULT_EXHAUSTIVENESS))
    normalized["exhaustiveness"] = max(
        MIN_EXHAUSTIVENESS,
        min(MAX_EXHAUSTIVENESS, normalized["exhaustiveness"])
    )
    
    # Number of modes (default 9, range 1-20)
    normalized["num_modes"] = int(
        parameters.get("num_modes", parameters.get("energy_range", DEFAULT_NUM_MODES))
    )
    normalized["num_modes"] = max(
        MIN_NUM_MODES,
        min(MAX_NUM_MODES, normalized["num_modes"])
    )
    
    # Energy range (optional, for filtering poses)
    normalized["energy_range"] = float(parameters.get("energy_range", DEFAULT_ENERGY_RANGE))
    
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
    Calculate comprehensive statistics from docking results with advanced metrics.
    
    Args:
        results: List of successful docking results
        
    Returns:
        Dictionary with comprehensive statistical metrics including percentiles,
        distribution measures, and confidence intervals
    """
    if not results:
        return {}
    
    affinities = [r["binding_affinity"] for r in results]
    num_modes_list = [len(r.get("modes", [])) for r in results]
    
    # Basic statistics
    n = len(affinities)
    sorted_affinities = sorted(affinities)
    mean_affinity = statistics.mean(affinities)
    
    # Standard deviation (sample standard deviation)
    if n > 1:
        std_affinity = statistics.stdev(affinities)
        variance = statistics.variance(affinities)
    else:
        std_affinity = 0.0
        variance = 0.0
    
    # Percentiles
    median_score = statistics.median(affinities)
    q1 = statistics.median(sorted_affinities[:n//2]) if n > 1 else sorted_affinities[0]
    q3 = statistics.median(sorted_affinities[(n+1)//2:]) if n > 1 else sorted_affinities[-1]
    iqr = q3 - q1
    
    # Additional percentiles (with bounds checking)
    if n > 0:
        p25_idx = min(int(n * 0.25), n - 1)
        p75_idx = min(int(n * 0.75), n - 1)
        p90_idx = min(int(n * 0.90), n - 1)
        p10_idx = min(int(n * 0.10), n - 1)
        p25 = sorted_affinities[p25_idx]
        p75 = sorted_affinities[p75_idx]
        p90 = sorted_affinities[p90_idx]
        p10 = sorted_affinities[p10_idx]
    else:
        p25 = p75 = p90 = p10 = 0.0
    
    # Skewness (measure of asymmetry)
    if n > 2 and std_affinity > 0:
        skewness = sum(((x - mean_affinity) / std_affinity) ** 3 for x in affinities) / n
    else:
        skewness = 0.0
    
    # Kurtosis (measure of tail heaviness)
    if n > 3 and std_affinity > 0:
        kurtosis = sum(((x - mean_affinity) / std_affinity) ** 4 for x in affinities) / n - 3.0
    else:
        kurtosis = 0.0
    
    # Coefficient of variation (relative variability)
    cv = (std_affinity / abs(mean_affinity)) * 100 if mean_affinity != 0 else 0.0
    
    # Confidence interval (95% CI using t-distribution approximation)
    # For large samples, use z-score; for small samples, use t-distribution
    if n > 1:
        # Using t-distribution approximation (t-value ≈ 1.96 for large n, higher for small n)
        t_value = 2.0 if n >= 30 else (2.5 if n >= 10 else 3.0)
        margin_error = t_value * (std_affinity / math.sqrt(n))
        ci_lower = mean_affinity - margin_error
        ci_upper = mean_affinity + margin_error
    else:
        margin_error = 0.0
        ci_lower = mean_affinity
        ci_upper = mean_affinity
    
    # Outlier detection using IQR method
    outlier_threshold_low = q1 - 1.5 * iqr
    outlier_threshold_high = q3 + 1.5 * iqr
    outliers = [a for a in affinities if a < outlier_threshold_low or a > outlier_threshold_high]
    
    # Binding strength classification
    strong_binders = [a for a in affinities if a < -7.0]
    moderate_binders = [a for a in affinities if -7.0 <= a < -5.0]
    weak_binders = [a for a in affinities if a >= -5.0]
    
    # Improved clustering metric (using standard deviation-based bins)
    if std_affinity > 0:
        # Cluster by standard deviation bins
        num_clusters = max(1, int((max(affinities) - min(affinities)) / (std_affinity * 0.5)))
    else:
        num_clusters = 1
    
    # Confidence score based on multiple factors
    # Factors: mean affinity, consistency (low std), pose consistency, number of poses
    mean_pose_consistency = statistics.mean([
        r.get("pose_consistency", 0.5) for r in results 
        if r.get("pose_consistency") is not None
    ]) if any(r.get("pose_consistency") is not None for r in results) else 0.5
    
    # Normalize confidence: better scores (< -7) + low variance + high pose consistency = high confidence
    score_factor = min(1.0, max(0.0, (mean_affinity + 10) / 5))  # -10 to -5 maps to 0-1
    consistency_factor = min(1.0, max(0.0, 1.0 - (std_affinity / 3.0)))  # Low std = high consistency
    pose_factor = mean_pose_consistency
    confidence_score = (score_factor * 0.4 + consistency_factor * 0.3 + pose_factor * 0.3)
    
    return {
        # Basic statistics
        "mean_score": mean_affinity,
        "std_score": std_affinity,
        "variance": variance,
        "min_score": min(affinities),
        "max_score": max(affinities),
        "range": max(affinities) - min(affinities),
        
        # Central tendency
        "median_score": median_score,
        "mode_score": statistics.mode(affinities) if len(set(affinities)) < len(affinities) and len(affinities) > 0 else None,
        
        # Percentiles
        "percentile_10": p10,
        "percentile_25": p25,
        "percentile_75": p75,
        "percentile_90": p90,
        "interquartile_range": iqr,
        
        # Distribution measures
        "skewness": skewness,
        "kurtosis": kurtosis,
        "coefficient_of_variation": cv,
        
        # Confidence intervals
        "confidence_interval_95_lower": ci_lower,
        "confidence_interval_95_upper": ci_upper,
        "margin_of_error": margin_error,
        
        # Outlier analysis
        "num_outliers": len(outliers),
        "outlier_threshold_low": outlier_threshold_low,
        "outlier_threshold_high": outlier_threshold_high,
        "outliers": outliers if len(outliers) <= 10 else outliers[:10],  # Limit outliers list
        
        # Binding strength distribution
        "num_strong_binders": len(strong_binders),
        "num_moderate_binders": len(moderate_binders),
        "num_weak_binders": len(weak_binders),
        "strong_binder_percentage": (len(strong_binders) / n) * 100 if n > 0 else 0.0,
        
        # Clustering and consistency
        "num_clusters": num_clusters,
        "success_rate": 1.0,  # All results are successful at this point
        "mean_num_modes": statistics.mean(num_modes_list) if num_modes_list else 0,
        "std_num_modes": statistics.stdev(num_modes_list) if len(num_modes_list) > 1 else 0,
        "mean_pose_consistency": mean_pose_consistency,
        
        # Overall confidence
        "confidence_score": confidence_score,
        "sample_size": n
    }

def perform_pose_clustering(results: List[Dict[str, Any]], rmsd_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Perform sophisticated pose clustering based on binding affinity with quality metrics.
    
    Uses adaptive binning based on data distribution and calculates cluster quality metrics.
    
    Args:
        results: List of docking results
        rmsd_threshold: RMSD threshold for clustering (for future RMSD-based clustering)
        
    Returns:
        List of results with enhanced cluster information including quality metrics
    """
    if not results:
        return []
    
    affinities = [r["binding_affinity"] for r in results]
    if not affinities:
        return []
    
    # Calculate optimal bin size using Freedman-Diaconis rule or adaptive approach
    affinity_range = max(affinities) - min(affinities)
    n = len(affinities)
    
    # Adaptive binning: use smaller bins for tighter distributions
    if affinity_range < 2.0:
        bin_size = 0.5  # 0.5 kcal/mol bins for tight distributions
    elif affinity_range < 5.0:
        bin_size = 1.0  # 1 kcal/mol bins for moderate distributions
    else:
        # Use Freedman-Diaconis rule for larger ranges
        q1 = statistics.median(sorted(affinities)[:n//2]) if n > 1 else affinities[0]
        q3 = statistics.median(sorted(affinities)[(n+1)//2:]) if n > 1 else affinities[-1]
        iqr = q3 - q1
        bin_size = max(0.5, min(2.0, 2 * iqr / (n ** (1/3)))) if iqr > 0 else 1.0
    
    # Perform clustering
    clusters = defaultdict(list)
    
    for idx, result in enumerate(results):
        affinity = result["binding_affinity"]
        # Cluster by adaptive bins
        cluster_id = int(affinity / bin_size)
        clusters[cluster_id].append({
            **result,
            "cluster_id": cluster_id,
            "cluster_bin_center": cluster_id * bin_size + bin_size / 2
        })
    
    # Calculate cluster quality metrics and sort
    clustered = []
    cluster_metrics = {}
    
    for cluster_id in sorted(clusters.keys()):
        cluster_results = clusters[cluster_id]
        cluster_results.sort(key=lambda x: x["binding_affinity"])
        
        # Calculate cluster statistics
        cluster_affinities = [r["binding_affinity"] for r in cluster_results]
        cluster_mean = statistics.mean(cluster_affinities)
        cluster_std = statistics.stdev(cluster_affinities) if len(cluster_affinities) > 1 else 0.0
        cluster_size = len(cluster_results)
        
        # Cluster quality: tighter clusters (lower std) with more members = higher quality
        cluster_quality = min(1.0, cluster_size / 5.0) * (1.0 - min(1.0, cluster_std / 2.0))
        
        # Best pose in cluster
        best_pose = cluster_results[0]
        
        # Calculate pose consistency within cluster
        cluster_pose_consistencies = [
            r.get("pose_consistency", 0.5) for r in cluster_results 
            if r.get("pose_consistency") is not None
        ]
        cluster_pose_consistency = (
            statistics.mean(cluster_pose_consistencies) 
            if cluster_pose_consistencies else 0.5
        )
        
        cluster_metrics[cluster_id] = {
            "cluster_id": cluster_id,
            "size": cluster_size,
            "mean_affinity": cluster_mean,
            "std_affinity": cluster_std,
            "min_affinity": min(cluster_affinities),
            "max_affinity": max(cluster_affinities),
            "quality_score": cluster_quality,
            "best_pose_affinity": best_pose["binding_affinity"],
            "best_pose_name": best_pose.get("ligand_name", "unknown"),
            "pose_consistency": cluster_pose_consistency,
            "bin_size": bin_size
        }
        
        # Add cluster metrics to each result in the cluster
        for result in cluster_results:
            result["cluster_metrics"] = cluster_metrics[cluster_id]
            clustered.append(result)
    
    # Sort by cluster quality and then by affinity within clusters
    clustered.sort(key=lambda x: (
        -x.get("cluster_metrics", {}).get("quality_score", 0),
        x["binding_affinity"]
    ))
    
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
            timeout_seconds = min(
                MAX_DOCKING_TIMEOUT,
                max(BASE_DOCKING_TIMEOUT, exhaustiveness * BASE_DOCKING_TIMEOUT)
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
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
    
    # Use shared parsing function
    modes = _parse_docking_modes_from_content(content, tool_name="Vina")
    
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
    
    # Add comprehensive pose quality indicators
    if len(modes) > 1:
        # Enhanced consistency calculation using multiple metrics
        top_n_affinities = [m["affinity"] for m in modes[:POSE_CONSISTENCY_TOP_N]]
        all_affinities = [m["affinity"] for m in modes]
        
        min_affinity = min(top_n_affinities)
        max_top_n = max(top_n_affinities)
        
        # Metric 1: Top-N consistency (how similar are top poses)
        if min_affinity != 0:
            top_n_consistency = 1.0 - (max_top_n - min_affinity) / abs(min_affinity)
            top_n_consistency = max(0.0, min(1.0, top_n_consistency))
        else:
            top_n_consistency = 0.0
        
        # Metric 2: Overall pose spread (coefficient of variation)
        if len(all_affinities) > 1:
            mean_affinity = statistics.mean(all_affinities)
            std_affinity = statistics.stdev(all_affinities)
            cv = (std_affinity / abs(mean_affinity)) * 100 if mean_affinity != 0 else 100.0
            # Lower CV = higher consistency (normalize to 0-1)
            spread_consistency = max(0.0, min(1.0, 1.0 - (cv / 50.0)))
        else:
            spread_consistency = 1.0
        
        # Metric 3: RMSD consistency (if RMSD data available)
        rmsd_values = [m.get("rmsd_lb", 0) for m in modes if m.get("rmsd_lb") is not None]
        rmsd_consistency = 0.5  # Default
        if len(rmsd_values) > 1:
            # Lower RMSD spread = higher consistency
            rmsd_range = max(rmsd_values) - min(rmsd_values)
            rmsd_consistency = max(0.0, min(1.0, 1.0 - (rmsd_range / 5.0)))
        
        # Combined consistency score (weighted average)
        pose_consistency = (
            top_n_consistency * 0.5 + 
            spread_consistency * 0.3 + 
            rmsd_consistency * 0.2
        )
        
        result["pose_consistency"] = pose_consistency
        result["top_n_consistency"] = top_n_consistency
        result["spread_consistency"] = spread_consistency
        result["rmsd_consistency"] = rmsd_consistency
        
        # Additional metrics
        result["affinity_std"] = statistics.stdev(all_affinities) if len(all_affinities) > 1 else 0.0
        result["affinity_cv"] = (result["affinity_std"] / abs(statistics.mean(all_affinities))) * 100 if statistics.mean(all_affinities) != 0 else 0.0
    else:
        result["pose_consistency"] = 1.0  # Single pose = perfect consistency
        result["top_n_consistency"] = 1.0
        result["spread_consistency"] = 1.0
        result["rmsd_consistency"] = 1.0
        result["affinity_std"] = 0.0
        result["affinity_cv"] = 0.0
    
    return result


def _parse_docking_modes_from_content(content: str, tool_name: str = "Vina") -> List[Dict[str, Any]]:
    """
    Shared function to parse docking modes from log file content.
    
    Args:
        content: Log file content as string
        tool_name: Name of the docking tool (for error messages)
        
    Returns:
        List of parsed docking modes
        
    Raises:
        DockingParseError: If parsing fails
    """
    modes = []
    lines = content.split('\n')
    
    # Parse binding modes - both Vina and Gnina use similar formats
    parsing_results = False
    for line in lines:
        # Check for header line that indicates start of results table
        if ("mode |" in line and "affinity" in line.lower()) or "-----+------------" in line:
            parsing_results = True
            continue
        
        # Skip separator lines
        if "-----" in line and parsing_results and not modes:
            continue
        
        # Parse mode lines
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
                    logger.warning(f"Failed to parse line in {tool_name} log file: {line[:100]}")
                    # Don't break - continue parsing in case there are more valid lines
                    continue
    
    if not modes:
        raise DockingParseError(f"No valid docking modes found in {tool_name} log file")
    
    return modes


def _calculate_pose_consistency(modes: List[Dict[str, Any]]) -> float:
    """
    Calculate pose consistency score from docking modes.
    
    Args:
        modes: List of docking modes with affinity scores
        
    Returns:
        Consistency score between 0.0 and 1.0
    """
    if len(modes) <= 1:
        return 0.0
    
    top_n_affinities = [m["affinity"] for m in modes[:POSE_CONSISTENCY_TOP_N]]
    min_affinity = min(top_n_affinities)
    
    if min_affinity == 0:
        return 0.0
    
    consistency = 1.0 - (max(top_n_affinities) - min_affinity) / abs(min_affinity)
    return max(0.0, min(1.0, consistency))


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
        timeout_seconds = min(
            MAX_DOCKING_TIMEOUT,
            max(BASE_DOCKING_TIMEOUT, exhaustiveness * BASE_DOCKING_TIMEOUT)
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
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
    
    # Add comprehensive pose quality indicators (same as parse_vina_log)
    if len(modes) > 1:
        # Enhanced consistency calculation using multiple metrics
        top_n_affinities = [m["affinity"] for m in modes[:POSE_CONSISTENCY_TOP_N]]
        all_affinities = [m["affinity"] for m in modes]
        
        min_affinity = min(top_n_affinities)
        max_top_n = max(top_n_affinities)
        
        # Metric 1: Top-N consistency (how similar are top poses)
        if min_affinity != 0:
            top_n_consistency = 1.0 - (max_top_n - min_affinity) / abs(min_affinity)
            top_n_consistency = max(0.0, min(1.0, top_n_consistency))
        else:
            top_n_consistency = 0.0
        
        # Metric 2: Overall pose spread (coefficient of variation)
        if len(all_affinities) > 1:
            mean_affinity = statistics.mean(all_affinities)
            std_affinity = statistics.stdev(all_affinities)
            cv = (std_affinity / abs(mean_affinity)) * 100 if mean_affinity != 0 else 100.0
            # Lower CV = higher consistency (normalize to 0-1)
            spread_consistency = max(0.0, min(1.0, 1.0 - (cv / 50.0)))
        else:
            spread_consistency = 1.0
        
        # Metric 3: RMSD consistency (if RMSD data available)
        rmsd_values = [m.get("rmsd_lb", 0) for m in modes if m.get("rmsd_lb") is not None]
        rmsd_consistency = 0.5  # Default
        if len(rmsd_values) > 1:
            # Lower RMSD spread = higher consistency
            rmsd_range = max(rmsd_values) - min(rmsd_values)
            rmsd_consistency = max(0.0, min(1.0, 1.0 - (rmsd_range / 5.0)))
        
        # Combined consistency score (weighted average)
        pose_consistency = (
            top_n_consistency * 0.5 + 
            spread_consistency * 0.3 + 
            rmsd_consistency * 0.2
        )
        
        out["pose_consistency"] = pose_consistency
        out["top_n_consistency"] = top_n_consistency
        out["spread_consistency"] = spread_consistency
        out["rmsd_consistency"] = rmsd_consistency
        
        # Additional metrics
        out["affinity_std"] = statistics.stdev(all_affinities) if len(all_affinities) > 1 else 0.0
        out["affinity_cv"] = (out["affinity_std"] / abs(statistics.mean(all_affinities))) * 100 if statistics.mean(all_affinities) != 0 else 0.0
    else:
        out["pose_consistency"] = 1.0  # Single pose = perfect consistency
        out["top_n_consistency"] = 1.0
        out["spread_consistency"] = 1.0
        out["rmsd_consistency"] = 1.0
        out["affinity_std"] = 0.0
        out["affinity_cv"] = 0.0
    
    return out
