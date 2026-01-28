"""Adapt backend docking_results JSON to frontend DockingResult format."""

from typing import Dict, Any, List


def adapt_docking_results_for_frontend(
    job_id: str,
    docking_results: Dict[str, Any],
    protein_structure: str = "",
    ligand_structure: str = "",
) -> Dict[str, Any]:
    """
    Transform backend docking_results into the frontend DockingResult shape.

    Frontend expects: job_id, protein_structure, ligand_structure, poses[], best_pose,
    metrics{ mean_score, std_score, min_score, max_score, num_clusters, success_rate,
    confidence_score }, output_directory, raw_results_path, analysis_plots, ai_analysis.
    """
    if not docking_results:
        return _empty_result(job_id, protein_structure, ligand_structure)

    results = docking_results.get("results") or []
    valid = [r for r in results if r.get("binding_affinity") is not None]
    valid.sort(key=lambda x: x["binding_affinity"])

    if not valid:
        return _empty_result(job_id, protein_structure, ligand_structure)

    best = valid[0]
    modes = best.get("modes") or []

    num_clusters = max(1, (docking_results.get("statistics") or {}).get("num_clusters", 1))
    poses: List[Dict[str, Any]] = []
    for i, m in enumerate(modes):
        affinity = m.get("affinity", 0.0)
        rmsd = m.get("rmsd_lb")
        if rmsd is None:
            rmsd = m.get("rmsd_ub", 0.0)
        if rmsd is None:
            rmsd = 0.0
        cluster_id = int((i % num_clusters) + 1)
        poses.append({
            "pose_id": i,
            "score": affinity,
            "binding_energy": affinity,
            "rmsd": float(rmsd),
            "cluster_id": cluster_id,
            "pose_file": "",  # Optional: serve via separate endpoint later
            "interactions": m.get("interactions") or {},
        })

    best_pose = poses[0] if poses else {
        "pose_id": 0,
        "score": 0.0,
        "binding_energy": 0.0,
        "rmsd": 0.0,
        "cluster_id": 1,
        "pose_file": "",
        "interactions": {},
    }
    stats = docking_results.get("statistics") or {}
    metrics = {
        "mean_score": stats.get("mean_score", 0.0),
        "std_score": stats.get("std_score", 0.0),
        "min_score": stats.get("min_score", 0.0),
        "max_score": stats.get("max_score", 0.0),
        "num_clusters": stats.get("num_clusters", 1),
        "success_rate": stats.get("success_rate", 1.0),
        "confidence_score": stats.get("confidence_score", 0.5),
    }

    return {
        "job_id": job_id,
        "protein_structure": protein_structure,
        "ligand_structure": ligand_structure,
        "poses": poses,
        "best_pose": best_pose,
        "metrics": metrics,
        "output_directory": docking_results.get("output_directory") or "",
        "raw_results_path": docking_results.get("raw_results_path") or "",
        "analysis_plots": docking_results.get("analysis_plots") or {},
        "ai_analysis": docking_results.get("ai_analysis"),
    }


def _empty_result(
    job_id: str,
    protein_structure: str = "",
    ligand_structure: str = "",
) -> Dict[str, Any]:
    empty_pose: Dict[str, Any] = {
        "pose_id": 0,
        "score": 0.0,
        "binding_energy": 0.0,
        "rmsd": 0.0,
        "cluster_id": 1,
        "pose_file": "",
        "interactions": {},
    }
    return {
        "job_id": job_id,
        "protein_structure": protein_structure,
        "ligand_structure": ligand_structure,
        "poses": [],
        "best_pose": empty_pose,
        "metrics": {
            "mean_score": 0.0,
            "std_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "num_clusters": 0,
            "success_rate": 0.0,
            "confidence_score": 0.0,
        },
        "output_directory": "",
        "raw_results_path": "",
        "analysis_plots": {},
        "ai_analysis": None,
    }
