import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any
import aiofiles
import logging
import json
import asyncio

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

VINA_PATH = os.getenv("AUTODOCK_VINA_PATH", "/usr/local/bin/vina")

async def run_autodock_vina(
    protein_pdb_path: Path,
    ligand_files: List[str],
    parameters: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Run AutoDock Vina for molecular docking.
    
    Args:
        protein_pdb_path: Path to protein PDB file
        ligand_files: List of ligand file contents (SDF format)
        parameters: Docking parameters (center, size, exhaustiveness)
        job_id: Unique job identifier
        
    Returns:
        Dictionary with docking results
        
    Raises:
        DockingError: If docking fails
        ValueError: If inputs are invalid
    """
    if not protein_pdb_path or not protein_pdb_path.exists():
        raise ValueError(f"Protein PDB file does not exist: {protein_pdb_path}")
    
    if not ligand_files or len(ligand_files) == 0:
        raise ValueError("At least one ligand file is required")
    
    if not parameters:
        raise ValueError("Docking parameters are required")
    
    output_dir = Path(f"/workspace/predictions/{job_id}/docking")
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create docking output directory for job {job_id}: {str(e)}")
        raise DockingError(f"Cannot create output directory: {str(e)}") from e
    
    logger.info(f"Starting docking for job {job_id}")
    
    try:
        # Prepare protein (convert to PDBQT)
        protein_pdbqt = await prepare_protein(protein_pdb_path, output_dir)
    except ProteinPreparationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing protein for job {job_id}: {str(e)}")
        raise ProteinPreparationError(f"Failed to prepare protein: {str(e)}") from e
    
    # Process each ligand
    all_results = []
    for idx, ligand_content in enumerate(ligand_files):
        if not ligand_content or not ligand_content.strip():
            logger.warning(f"Skipping empty ligand {idx} for job {job_id}")
            continue
        
        ligand_name = f"ligand_{idx}"
        logger.info(f"Processing {ligand_name} for job {job_id}")
        
        try:
            # Prepare ligand (convert SDF to PDBQT)
            ligand_pdbqt = await prepare_ligand(ligand_content, ligand_name, output_dir)
            
            # Run Vina
            result = await run_vina_docking(
                protein_pdbqt,
                ligand_pdbqt,
                parameters,
                output_dir,
                ligand_name
            )
            
            all_results.append({
                "ligand_name": ligand_name,
                "ligand_index": idx,
                **result
            })
        except (LigandPreparationError, VinaExecutionError) as e:
            logger.error(f"Failed to dock {ligand_name} for job {job_id}: {str(e)}")
            # Continue with other ligands instead of failing completely
            all_results.append({
                "ligand_name": ligand_name,
                "ligand_index": idx,
                "binding_affinity": None,
                "modes": [],
                "error": str(e)
            })
        except Exception as e:
            logger.error(f"Unexpected error docking {ligand_name} for job {job_id}: {str(e)}")
            all_results.append({
                "ligand_name": ligand_name,
                "ligand_index": idx,
                "binding_affinity": None,
                "modes": [],
                "error": f"Unexpected error: {str(e)}"
            })
    
    if not all_results or all(all_results[i].get("binding_affinity") is None for i in range(len(all_results))):
        raise DockingError("All ligands failed to dock. Check logs for details.")
    
    # Sort by binding affinity (best score first), filtering out failed results
    valid_results = [r for r in all_results if r.get("binding_affinity") is not None]
    valid_results.sort(key=lambda x: x["binding_affinity"])
    
    docking_summary = {
        "total_ligands": len(ligand_files),
        "successful_ligands": len(valid_results),
        "failed_ligands": len(all_results) - len(valid_results),
        "results": all_results,
        "best_score": valid_results[0]["binding_affinity"] if valid_results else None,
        "best_ligand": valid_results[0]["ligand_name"] if valid_results else None
    }
    
    logger.info(f"Docking completed for job {job_id}, best score: {docking_summary['best_score']}")
    
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

async def run_vina_docking(
    protein_pdbqt: Path,
    ligand_pdbqt: Path,
    parameters: Dict[str, Any],
    output_dir: Path,
    ligand_name: str
) -> Dict[str, Any]:
    """Run AutoDock Vina docking simulation"""
    
    if not protein_pdbqt.exists():
        raise VinaExecutionError(f"Protein PDBQT file does not exist: {protein_pdbqt}")
    
    if not ligand_pdbqt.exists():
        raise VinaExecutionError(f"Ligand PDBQT file does not exist: {ligand_pdbqt}")
    
    # Validate Vina executable
    if not os.path.exists(VINA_PATH):
        raise VinaExecutionError(f"AutoDock Vina executable not found at: {VINA_PATH}")
    
    # Get docking parameters with defaults and validate
    center_x = float(parameters.get("center_x", 0.0))
    center_y = float(parameters.get("center_y", 0.0))
    center_z = float(parameters.get("center_z", 0.0))
    size_x = float(parameters.get("size_x", 20.0))
    size_y = float(parameters.get("size_y", 20.0))
    size_z = float(parameters.get("size_z", 20.0))
    exhaustiveness = int(parameters.get("exhaustiveness", 8))
    num_modes = int(parameters.get("num_modes", 9))
    
    if exhaustiveness < 1 or exhaustiveness > 32:
        raise ValueError(f"Exhaustiveness must be between 1 and 32, got {exhaustiveness}")
    
    if num_modes < 1 or num_modes > 20:
        raise ValueError(f"Number of modes must be between 1 and 20, got {num_modes}")
    
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
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Timeout based on exhaustiveness (more exhaustive = longer time)
            timeout_seconds = min(600, exhaustiveness * 60)  # Max 10 minutes
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
            result = await parse_vina_log(log_file)
            result["output_pdbqt"] = str(output_pdbqt)
            return result
        except DockingParseError as e:
            logger.error(f"Failed to parse Vina log for {ligand_name}: {str(e)}")
            raise
    except VinaExecutionError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error running Vina for {ligand_name}: {str(e)}")
        raise VinaExecutionError(f"Unexpected error during Vina execution: {str(e)}") from e

async def parse_vina_log(log_file: Path) -> Dict[str, Any]:
    """Parse AutoDock Vina log file to extract binding scores"""
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
    
    parsing_results = False
    for line in lines:
        if "mode |   affinity" in line:
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
                    break
    
    if not modes:
        raise DockingParseError("No valid docking modes found in log file")
    
    return {
        "binding_affinity": modes[0]["affinity"],
        "modes": modes
    }

import asyncio
