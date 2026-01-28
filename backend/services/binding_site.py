"""
Binding site analysis service for protein structures
Identifies potential drug binding sites using geometric and energetic analysis
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import subprocess
import asyncio

logger = logging.getLogger(__name__)

class BindingSiteError(Exception):
    """Base exception for binding site analysis errors"""
    pass

class FPocketNotAvailableError(BindingSiteError):
    """FPocket tool is not available"""
    pass

FPOCKET_PATH = "fpocket"  # Default fpocket command

async def analyze_binding_sites(
    pdb_path: Path,
    job_id: str,
    min_pocket_size: int = 20,
    max_pocket_size: int = 200
) -> Dict[str, Any]:
    """
    Analyze protein structure to identify potential binding sites/pockets.
    
    Args:
        pdb_path: Path to protein PDB file
        job_id: Unique job identifier
        min_pocket_size: Minimum pocket size (number of atoms)
        max_pocket_size: Maximum pocket size (number of atoms)
        
    Returns:
        Dictionary with binding site analysis results including:
        - pockets: List of identified pockets with properties
        - best_pocket: Most druggable pocket
        - druggability_score: Overall druggability assessment
        - binding_site_coordinates: Coordinates for docking grid center
        
    Raises:
        BindingSiteError: If analysis fails
    """
    if not pdb_path or not pdb_path.exists():
        raise BindingSiteError(f"PDB file does not exist: {pdb_path}")
    
    output_dir = Path(f"/workspace/predictions/{job_id}/binding_sites")
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create binding site output directory for job {job_id}: {str(e)}")
        raise BindingSiteError(f"Cannot create output directory: {str(e)}") from e
    
    logger.info(f"Analyzing binding sites for job {job_id}")
    
    # Try FPocket first (if available), otherwise use geometric analysis
    try:
        if await _fpocket_available():
            return await _analyze_with_fpocket(pdb_path, output_dir, job_id, min_pocket_size, max_pocket_size)
        else:
            logger.info(f"FPocket not available, using geometric analysis for job {job_id}")
            return await _analyze_geometric(pdb_path, output_dir, job_id)
    except Exception as e:
        logger.warning(f"Binding site analysis failed, using fallback method: {str(e)}")
        return await _analyze_geometric(pdb_path, output_dir, job_id)

async def _fpocket_available() -> bool:
    """Check if FPocket is available"""
    try:
        process = await asyncio.create_subprocess_exec(
            FPOCKET_PATH, "-h",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=5)
        return process.returncode == 0
    except (FileNotFoundError, asyncio.TimeoutError):
        return False

async def _analyze_with_fpocket(
    pdb_path: Path,
    output_dir: Path,
    job_id: str,
    min_pocket_size: int,
    max_pocket_size: int
) -> Dict[str, Any]:
    """Analyze binding sites using FPocket"""
    
    cmd = [
        FPOCKET_PATH,
        "-f", str(pdb_path),
        "-m", str(min_pocket_size),
        "-M", str(max_pocket_size),
        "-i", "1",  # Include all pockets
        "-D", str(output_dir)
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
            logger.warning(f"FPocket failed for job {job_id}: {error_msg}")
            raise FPocketNotAvailableError(f"FPocket analysis failed: {error_msg}")
        
        # Parse FPocket output
        return await _parse_fpocket_output(output_dir, job_id)
    except asyncio.TimeoutError:
        raise BindingSiteError("FPocket analysis timed out")
    except Exception as e:
        logger.error(f"Error running FPocket for job {job_id}: {str(e)}")
        raise BindingSiteError(f"FPocket analysis failed: {str(e)}") from e

async def _parse_fpocket_output(output_dir: Path, job_id: str) -> Dict[str, Any]:
    """Parse FPocket output files"""
    
    # Look for FPocket output files
    pdb_base = output_dir.parent.parent.name if output_dir.parent.parent else "protein"
    pockets_file = output_dir / f"{pdb_base}_out" / "pockets" / "pockets.pqr"
    info_file = output_dir / f"{pdb_base}_out" / "pockets" / "pockets_info.txt"
    
    pockets = []
    
    # Try to parse info file if available
    if info_file.exists():
        try:
            async with aiofiles.open(info_file, 'r') as f:
                content = await f.read()
                # Parse FPocket info format
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('Pocket') and 'Score' in line:
                        # Parse pocket information
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                pocket_num = int(parts[1])
                                score = float(parts[-1])
                                pockets.append({
                                    "pocket_id": pocket_num,
                                    "druggability_score": score,
                                    "volume": None,  # Would need additional parsing
                                    "surface_area": None
                                })
                            except (ValueError, IndexError):
                                continue
        except Exception as e:
            logger.warning(f"Failed to parse FPocket info file: {str(e)}")
    
    # If no pockets found, use geometric analysis as fallback
    if not pockets:
        logger.info(f"No pockets found in FPocket output, using geometric analysis")
        return await _analyze_geometric(output_dir.parent.parent / "protein.pdb", output_dir, job_id)
    
    # Sort by druggability score (higher is better)
    pockets.sort(key=lambda x: x.get("druggability_score", 0), reverse=True)
    
    best_pocket = pockets[0] if pockets else None
    
    return {
        "method": "fpocket",
        "pockets": pockets,
        "num_pockets": len(pockets),
        "best_pocket": best_pocket,
        "druggability_score": best_pocket.get("druggability_score", 0.0) if best_pocket else 0.0,
        "binding_site_coordinates": _estimate_pocket_center(pockets[0] if pockets else None, output_dir)
    }

async def _analyze_geometric(
    pdb_path: Path,
    output_dir: Path,
    job_id: str
) -> Dict[str, Any]:
    """
    Geometric binding site analysis using PDB structure.
    Identifies cavities and surface clefts.
    """
    
    if not pdb_path.exists():
        raise BindingSiteError(f"PDB file does not exist: {pdb_path}")
    
    try:
        # Read PDB file and analyze structure
        residues = []
        atoms = []
        
        async with aiofiles.open(pdb_path, 'r') as f:
            async for line in f:
                if line.startswith("ATOM"):
                    try:
                        # Parse ATOM record
                        atom_name = line[12:16].strip()
                        residue_name = line[17:20].strip()
                        residue_num = int(line[22:26].strip())
                        x = float(line[30:38].strip())
                        y = float(line[38:46].strip())
                        z = float(line[46:54].strip())
                        
                        atoms.append({
                            "name": atom_name,
                            "residue": residue_name,
                            "residue_num": residue_num,
                            "x": x,
                            "y": y,
                            "z": z
                        })
                        
                        if residue_num not in [r["num"] for r in residues]:
                            residues.append({
                                "name": residue_name,
                                "num": residue_num,
                                "atoms": []
                            })
                    except (ValueError, IndexError):
                        continue
        
        if not atoms:
            raise BindingSiteError("No atoms found in PDB file")
        
        # Calculate geometric properties
        # Find potential binding sites based on:
        # 1. Surface accessibility (exposed residues)
        # 2. Cavity detection (regions with low atom density)
        # 3. Hydrophobic patches (potential binding sites)
        
        # Simple cavity detection: find regions with low atom density
        pockets = _detect_cavities_geometric(atoms)
        
        # Calculate druggability scores
        for pocket in pockets:
            pocket["druggability_score"] = _calculate_druggability_score(pocket, atoms)
        
        # Sort by druggability score
        pockets.sort(key=lambda x: x.get("druggability_score", 0), reverse=True)
        
        best_pocket = pockets[0] if pockets else None
        
        # Estimate binding site center (for docking grid)
        binding_site_coords = None
        if best_pocket:
            binding_site_coords = {
                "center_x": best_pocket.get("center_x", 0.0),
                "center_y": best_pocket.get("center_y", 0.0),
                "center_z": best_pocket.get("center_z", 0.0),
                "estimated_size": best_pocket.get("size", 20.0)
            }
        
        result = {
            "method": "geometric",
            "pockets": pockets[:10],  # Top 10 pockets
            "num_pockets": len(pockets),
            "best_pocket": best_pocket,
            "druggability_score": best_pocket.get("druggability_score", 0.0) if best_pocket else 0.0,
            "binding_site_coordinates": binding_site_coords,
            "protein_info": {
                "num_atoms": len(atoms),
                "num_residues": len(residues),
                "bounds": _calculate_bounds(atoms)
            }
        }
        
        # Save results
        results_file = output_dir / "binding_sites.json"
        async with aiofiles.open(results_file, 'w') as f:
            await f.write(json.dumps(result, indent=2))
        
        logger.info(f"Geometric binding site analysis completed for job {job_id}: {len(pockets)} pockets found")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in geometric binding site analysis for job {job_id}: {str(e)}", exc_info=True)
        raise BindingSiteError(f"Geometric analysis failed: {str(e)}") from e

def _detect_cavities_geometric(atoms: List[Dict[str, Any]], grid_size: float = 5.0) -> List[Dict[str, Any]]:
    """
    Detect cavities using geometric analysis.
    Simple grid-based approach to find low-density regions.
    """
    if not atoms:
        return []
    
    # Calculate bounding box
    x_coords = [a["x"] for a in atoms]
    y_coords = [a["y"] for a in atoms]
    z_coords = [a["z"] for a in atoms]
    
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    min_z, max_z = min(z_coords), max(z_coords)
    
    # Create grid
    grid = {}
    for atom in atoms:
        grid_x = int(atom["x"] / grid_size)
        grid_y = int(atom["y"] / grid_size)
        grid_z = int(atom["z"] / grid_size)
        key = (grid_x, grid_y, grid_z)
        if key not in grid:
            grid[key] = []
        grid[key].append(atom)
    
    # Find low-density regions (potential cavities)
    cavities = []
    visited = set()
    
    for (gx, gy, gz), grid_atoms in grid.items():
        if len(grid_atoms) < 3:  # Low density region
            # Check if this is part of a larger cavity
            cavity_key = (gx, gy, gz)
            if cavity_key not in visited:
                cavity = _expand_cavity(grid, (gx, gy, gz), visited, grid_size)
                if cavity and len(cavity["cells"]) >= 3:  # Minimum cavity size
                    # Calculate cavity center
                    cell_coords = [(gx * grid_size, gy * grid_size, gz * grid_size) 
                                  for gx, gy, gz in cavity["cells"]]
                    center_x = sum(c[0] for c in cell_coords) / len(cell_coords)
                    center_y = sum(c[1] for c in cell_coords) / len(cell_coords)
                    center_z = sum(c[2] for c in cell_coords) / len(cell_coords)
                    
                    cavities.append({
                        "center_x": center_x,
                        "center_y": center_y,
                        "center_z": center_z,
                        "size": len(cavity["cells"]) * (grid_size ** 3),
                        "num_cells": len(cavity["cells"]),
                        "cells": cavity["cells"]
                    })
    
    return cavities

def _expand_cavity(grid: Dict, start: Tuple[int, int, int], visited: set, grid_size: float) -> Optional[Dict]:
    """Expand a cavity region using flood fill"""
    if start in visited:
        return None
    
    cavity_cells = []
    stack = [start]
    
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        
        visited.add(current)
        cavity_cells.append(current)
        
        # Check neighbors
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    neighbor = (current[0] + dx, current[1] + dy, current[2] + dz)
                    if neighbor in grid and len(grid[neighbor]) < 3 and neighbor not in visited:
                        stack.append(neighbor)
    
    if len(cavity_cells) >= 3:
        return {"cells": cavity_cells}
    return None

def _calculate_druggability_score(pocket: Dict[str, Any], atoms: List[Dict[str, Any]]) -> float:
    """
    Calculate druggability score for a pocket.
    Higher score = more druggable.
    """
    score = 0.0
    
    # Size factor (optimal size range)
    size = pocket.get("size", 0)
    if 100 <= size <= 500:  # Optimal pocket size
        score += 0.4
    elif 50 <= size < 100 or 500 < size <= 1000:
        score += 0.2
    
    # Depth factor (deeper pockets are better)
    # Simplified: assume cavities are reasonably deep
    score += 0.3
    
    # Accessibility (surface pockets are better)
    # Simplified: assume reasonable accessibility
    score += 0.3
    
    return min(1.0, score)

def _estimate_pocket_center(pocket: Optional[Dict[str, Any]], output_dir: Path) -> Optional[Dict[str, float]]:
    """Estimate pocket center coordinates"""
    if not pocket:
        return None
    
    return {
        "center_x": pocket.get("center_x", 0.0),
        "center_y": pocket.get("center_y", 0.0),
        "center_z": pocket.get("center_z", 0.0),
        "estimated_size": pocket.get("size", 20.0)
    }

def _calculate_bounds(atoms: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate protein bounding box"""
    if not atoms:
        return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}
    
    x_coords = [a["x"] for a in atoms]
    y_coords = [a["y"] for a in atoms]
    z_coords = [a["z"] for a in atoms]
    
    return {
        "min_x": min(x_coords),
        "max_x": max(x_coords),
        "min_y": min(y_coords),
        "max_y": max(y_coords),
        "min_z": min(z_coords),
        "max_z": max(z_coords)
    }
