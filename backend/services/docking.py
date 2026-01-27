import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any
import aiofiles
import logging
import json

logger = logging.getLogger(__name__)

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
    """
    output_dir = Path(f"/workspace/predictions/{job_id}/docking")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting docking for job {job_id}")
    
    # Prepare protein (convert to PDBQT)
    protein_pdbqt = await prepare_protein(protein_pdb_path, output_dir)
    
    # Process each ligand
    all_results = []
    for idx, ligand_content in enumerate(ligand_files):
        ligand_name = f"ligand_{idx}"
        logger.info(f"Processing {ligand_name} for job {job_id}")
        
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
    
    # Sort by binding affinity (best score first)
    all_results.sort(key=lambda x: x["binding_affinity"])
    
    docking_summary = {
        "total_ligands": len(ligand_files),
        "results": all_results,
        "best_score": all_results[0]["binding_affinity"] if all_results else None,
        "best_ligand": all_results[0]["ligand_name"] if all_results else None
    }
    
    logger.info(f"Docking completed for job {job_id}, best score: {docking_summary['best_score']}")
    
    return docking_summary

async def prepare_protein(pdb_path: Path, output_dir: Path) -> Path:
    """Convert PDB to PDBQT format for docking"""
    pdbqt_path = output_dir / "protein.pdbqt"
    
    # Use Open Babel or MGLTools for conversion
    cmd = [
        "obabel",
        str(pdb_path),
        "-O", str(pdbqt_path),
        "-xr"  # Add hydrogens and charges
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Protein preparation failed: {stderr.decode()}")
    
    return pdbqt_path

async def prepare_ligand(ligand_content: str, ligand_name: str, output_dir: Path) -> Path:
    """Convert ligand SDF to PDBQT format"""
    sdf_path = output_dir / f"{ligand_name}.sdf"
    pdbqt_path = output_dir / f"{ligand_name}.pdbqt"
    
    # Save SDF content
    async with aiofiles.open(sdf_path, 'w') as f:
        await f.write(ligand_content)
    
    # Convert to PDBQT
    cmd = [
        "obabel",
        str(sdf_path),
        "-O", str(pdbqt_path),
        "-h",  # Add hydrogens
        "--partialcharge", "gasteiger"  # Add charges
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Ligand preparation failed: {stderr.decode()}")
    
    return pdbqt_path

async def run_vina_docking(
    protein_pdbqt: Path,
    ligand_pdbqt: Path,
    parameters: Dict[str, Any],
    output_dir: Path,
    ligand_name: str
) -> Dict[str, Any]:
    """Run AutoDock Vina docking simulation"""
    
    # Get docking parameters with defaults
    center_x = parameters.get("center_x", 0.0)
    center_y = parameters.get("center_y", 0.0)
    center_z = parameters.get("center_z", 0.0)
    size_x = parameters.get("size_x", 20.0)
    size_y = parameters.get("size_y", 20.0)
    size_z = parameters.get("size_z", 20.0)
    exhaustiveness = parameters.get("exhaustiveness", 8)
    num_modes = parameters.get("num_modes", 9)
    
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
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Vina docking failed: {stderr.decode()}")
    
    # Parse results from log file
    result = await parse_vina_log(log_file)
    result["output_pdbqt"] = str(output_pdbqt)
    
    return result

async def parse_vina_log(log_file: Path) -> Dict[str, Any]:
    """Parse AutoDock Vina log file to extract binding scores"""
    modes = []
    
    async with aiofiles.open(log_file, 'r') as f:
        content = await f.read()
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
                    except ValueError:
                        break
    
    if not modes:
        return {"binding_affinity": 0.0, "modes": []}
    
    return {
        "binding_affinity": modes[0]["affinity"],
        "modes": modes
    }

import asyncio
