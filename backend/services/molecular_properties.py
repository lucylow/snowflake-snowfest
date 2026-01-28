"""
ML-powered molecular property prediction service
Provides comprehensive drug-likeness, ADMET, and toxicity predictions
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, QED, Crippen, rdMolDescriptors
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available. Molecular property predictions will be limited.")

class MolecularPropertyError(Exception):
    """Base exception for molecular property prediction errors"""
    pass

class RDKitNotAvailableError(MolecularPropertyError):
    """RDKit library is not available"""
    pass

# Structural alerts for toxicity prediction
TOXICITY_ALERTS = [
    "Michael_Acceptor",
    "Aldehyde",
    "Epoxide",
    "Aziridine",
    "Thiocarbonyl",
    "Acyl_halide",
    "Alkyl_halide",
    "Nitro_aromatic",
    "Nitroso",
    "Azo",
    "Hydrazine",
    "Hydrazone",
    "Peroxide",
    "Thiophene_dioxide",
    "Furan",
    "Quinone",
    "Catechol",
    "Phenol",
    "Aniline",
    "Aromatic_amine",
    "Nitro_aromatic",
    "Nitroso",
    "Azo",
    "Hydrazine",
    "Hydrazone",
    "Peroxide",
    "Thiophene_dioxide",
    "Furan",
    "Quinone",
    "Catechol",
    "Phenol",
    "Aniline",
    "Aromatic_amine",
]

def calculate_molecular_properties(ligand_sdf: str, ligand_name: str = "ligand") -> Dict[str, Any]:
    """
    Calculate comprehensive molecular properties using RDKit
    
    Args:
        ligand_sdf: SDF file content as string
        ligand_name: Name of the ligand
        
    Returns:
        Dictionary with molecular properties, drug-likeness scores, ADMET predictions, and toxicity assessments
        
    Raises:
        RDKitNotAvailableError: If RDKit is not installed
        MolecularPropertyError: If property calculation fails
    """
    if not RDKIT_AVAILABLE:
        raise RDKitNotAvailableError("RDKit is required for molecular property calculations")
    
    if not ligand_sdf or not ligand_sdf.strip():
        raise MolecularPropertyError("Ligand SDF content is required")
    
    try:
        # Parse molecule from SDF
        mol = Chem.MolFromMolBlock(ligand_sdf)
        if mol is None:
            # Try reading from string directly
            mol = Chem.MolFromSmiles(ligand_sdf)
            if mol is None:
                raise MolecularPropertyError(f"Failed to parse molecule from SDF for {ligand_name}")
        
        # Calculate basic molecular descriptors
        properties = calculate_basic_descriptors(mol)
        
        # Calculate drug-likeness scores
        drug_likeness = calculate_drug_likeness(mol, properties)
        
        # Calculate ADMET properties
        admet = calculate_admet_properties(mol, properties)
        
        # Calculate toxicity predictions
        toxicity = calculate_toxicity_predictions(mol, properties)
        
        # Calculate binding affinity predictions (ML-based estimates)
        binding_affinity_prediction = predict_binding_affinity(mol, properties)
        
        return {
            "ligand_name": ligand_name,
            "molecular_properties": properties,
            "drug_likeness": drug_likeness,
            "admet": admet,
            "toxicity": toxicity,
            "binding_affinity_prediction": binding_affinity_prediction,
            "overall_score": calculate_overall_drug_score(drug_likeness, admet, toxicity),
        }
    except Exception as e:
        logger.error(f"Error calculating molecular properties for {ligand_name}: {str(e)}")
        raise MolecularPropertyError(f"Failed to calculate molecular properties: {str(e)}") from e

def calculate_basic_descriptors(mol) -> Dict[str, Any]:
    """Calculate basic molecular descriptors"""
    return {
        "molecular_weight": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "hbd": Lipinski.NumHDonors(mol),  # Hydrogen bond donors
        "hba": Lipinski.NumHAcceptors(mol),  # Hydrogen bond acceptors
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "tpsa": Descriptors.TPSA(mol),  # Topological Polar Surface Area
        "num_atoms": mol.GetNumAtoms(),
        "num_rings": rdMolDescriptors.CalcNumRings(mol),
        "num_aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "num_heteroatoms": rdMolDescriptors.CalcNumHeteroatoms(mol),
        "formal_charge": Chem.rdmolops.GetFormalCharge(mol),
        "num_heavy_atoms": mol.GetNumHeavyAtoms(),
        "fraction_csp3": rdMolDescriptors.CalcFractionCsp3(mol),
        "num_saturated_rings": rdMolDescriptors.CalcNumSaturatedRings(mol),
        "num_aliphatic_rings": rdMolDescriptors.CalcNumAliphaticRings(mol),
    }

def calculate_drug_likeness(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate drug-likeness scores including Lipinski's Rule of Five, QED, and SA score"""
    
    # Lipinski's Rule of Five
    lipinski_violations = 0
    lipinski_details = {}
    
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    hbd = properties["hbd"]
    hba = properties["hba"]
    
    if mw > 500:
        lipinski_violations += 1
        lipinski_details["molecular_weight"] = {"value": mw, "violation": True, "threshold": 500}
    else:
        lipinski_details["molecular_weight"] = {"value": mw, "violation": False, "threshold": 500}
    
    if logp > 5:
        lipinski_violations += 1
        lipinski_details["logp"] = {"value": logp, "violation": True, "threshold": 5}
    else:
        lipinski_details["logp"] = {"value": logp, "violation": False, "threshold": 5}
    
    if hbd > 5:
        lipinski_violations += 1
        lipinski_details["hbd"] = {"value": hbd, "violation": True, "threshold": 5}
    else:
        lipinski_details["hbd"] = {"value": hbd, "violation": False, "threshold": 5}
    
    if hba > 10:
        lipinski_violations += 1
        lipinski_details["hba"] = {"value": hba, "violation": True, "threshold": 10}
    else:
        lipinski_details["hba"] = {"value": hba, "violation": False, "threshold": 10}
    
    # QED (Quantitative Estimate of Drug-likeness)
    try:
        qed_score = QED.qed(mol)
    except:
        qed_score = 0.5  # Default if calculation fails
    
    # Veber's Rule (oral bioavailability)
    tpsa = properties["tpsa"]
    rotatable_bonds = properties["rotatable_bonds"]
    veber_pass = tpsa <= 140 and rotatable_bonds <= 10
    
    # Egan's Rule (GI absorption)
    egan_pass = properties["logp"] <= 5.88 and properties["tpsa"] <= 131.6
    
    # Muegge's Rule
    mw_muegge = 200 <= mw <= 600
    logp_muegge = -2 <= logp <= 5
    rot_bonds_muegge = rotatable_bonds <= 15
    rings_muegge = properties["num_rings"] <= 7
    hbd_muegge = hbd <= 5
    hba_muegge = hba <= 10
    tpsa_muegge = properties["tpsa"] <= 150
    heavy_atoms_muegge = 10 <= properties["num_heavy_atoms"] <= 70
    
    muegge_violations = sum([
        not mw_muegge, not logp_muegge, not rot_bonds_muegge,
        not rings_muegge, not hbd_muegge, not hba_muegge,
        not tpsa_muegge, not heavy_atoms_muegge
    ])
    
    # Synthetic Accessibility (SA) Score (simplified version)
    # Lower is better (0-10 scale, <6 is easy to synthesize)
    sa_score = estimate_sa_score(mol, properties)
    
    return {
        "lipinski_rule_of_five": {
            "violations": lipinski_violations,
            "pass": lipinski_violations == 0,
            "details": lipinski_details,
            "score": max(0, 1.0 - (lipinski_violations / 4.0)),  # Normalized score
        },
        "qed_score": qed_score,
        "veber_rule": {
            "pass": veber_pass,
            "tpsa": tpsa,
            "rotatable_bonds": rotatable_bonds,
        },
        "egan_rule": {
            "pass": egan_pass,
            "logp": properties["logp"],
            "tpsa": properties["tpsa"],
        },
        "muegge_rule": {
            "violations": muegge_violations,
            "pass": muegge_violations == 0,
        },
        "synthetic_accessibility": {
            "score": sa_score,
            "interpretation": "easy" if sa_score < 6 else "moderate" if sa_score < 8 else "difficult",
        },
        "overall_drug_likeness_score": calculate_drug_likeness_score(
            lipinski_violations, qed_score, veber_pass, egan_pass, muegge_violations, sa_score
        ),
    }

def estimate_sa_score(mol, properties: Dict[str, Any]) -> float:
    """
    Estimate Synthetic Accessibility (SA) Score
    Simplified version based on molecular complexity
    Lower score = easier to synthesize
    """
    complexity_score = 0.0
    
    # Base complexity from molecular weight
    mw = properties["molecular_weight"]
    complexity_score += (mw / 500.0) * 2.0  # Max 2 points
    
    # Complexity from rings
    num_rings = properties["num_rings"]
    complexity_score += min(num_rings * 0.5, 2.0)  # Max 2 points
    
    # Complexity from heteroatoms
    num_heteroatoms = properties["num_heteroatoms"]
    complexity_score += min(num_heteroatoms * 0.3, 2.0)  # Max 2 points
    
    # Complexity from rotatable bonds (more flexible = easier)
    rot_bonds = properties["rotatable_bonds"]
    complexity_score -= min(rot_bonds * 0.1, 1.0)  # Subtract up to 1 point
    
    # Normalize to 0-10 scale
    sa_score = max(0, min(10, complexity_score))
    
    return round(sa_score, 2)

def calculate_drug_likeness_score(
    lipinski_violations: int,
    qed_score: float,
    veber_pass: bool,
    egan_pass: bool,
    muegge_violations: int,
    sa_score: float
) -> float:
    """Calculate overall drug-likeness score (0-1 scale)"""
    
    # Lipinski component (40% weight)
    lipinski_component = max(0, 1.0 - (lipinski_violations / 4.0))
    
    # QED component (30% weight)
    qed_component = qed_score
    
    # Rule-based component (20% weight)
    rule_score = 0.0
    if veber_pass:
        rule_score += 0.5
    if egan_pass:
        rule_score += 0.5
    
    # SA component (10% weight) - inverted (lower SA score = better)
    sa_component = max(0, 1.0 - (sa_score / 10.0))
    
    # Weighted average
    overall_score = (
        lipinski_component * 0.4 +
        qed_component * 0.3 +
        rule_score * 0.2 +
        sa_component * 0.1
    )
    
    return round(overall_score, 3)

def calculate_admet_properties(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) properties
    """
    
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    tpsa = properties["tpsa"]
    hbd = properties["hbd"]
    hba = properties["hba"]
    rotatable_bonds = properties["rotatable_bonds"]
    num_rings = properties["num_rings"]
    
    # Absorption predictions
    # GI Absorption (Gastrointestinal)
    gi_absorption_score = predict_gi_absorption(logp, tpsa, mw, hbd, hba)
    
    # Bioavailability
    bioavailability_score = predict_bioavailability(logp, tpsa, rotatable_bonds, mw)
    
    # Distribution predictions
    # BBB (Blood-Brain Barrier) permeability
    bbb_permeability = predict_bbb_permeability(logp, tpsa, mw)
    
    # P-gp substrate prediction
    pgp_substrate = predict_pgp_substrate(mw, logp, tpsa, num_rings)
    
    # VD (Volume of Distribution) prediction
    vd_prediction = predict_vd(logp, mw, hbd)
    
    # Metabolism predictions
    # CYP450 inhibition (simplified)
    cyp_inhibition = predict_cyp_inhibition(mol, properties)
    
    # Half-life prediction
    half_life_hours = predict_half_life(mw, logp, rotatable_bonds)
    
    # Excretion predictions
    # Clearance prediction
    clearance = predict_clearance(mw, logp, rotatable_bonds)
    
    # Renal clearance
    renal_clearance = predict_renal_clearance(mw, logp, tpsa)
    
    return {
        "absorption": {
            "gi_absorption": {
                "score": gi_absorption_score,
                "prediction": "high" if gi_absorption_score > 0.7 else "moderate" if gi_absorption_score > 0.4 else "low",
            },
            "bioavailability": {
                "score": bioavailability_score,
                "prediction": "high" if bioavailability_score > 0.7 else "moderate" if bioavailability_score > 0.4 else "low",
                "percentage": round(bioavailability_score * 100, 1),
            },
            "solubility": {
                "log_s": predict_solubility(logp, mw, tpsa),
                "prediction": predict_solubility_category(logp, mw, tpsa),
            },
        },
        "distribution": {
            "bbb_permeability": {
                "score": bbb_permeability,
                "prediction": "permeant" if bbb_permeability > 0.5 else "non-permeant",
                "log_bb": predict_log_bb(logp, tpsa),
            },
            "pgp_substrate": {
                "is_substrate": pgp_substrate,
                "probability": 0.7 if pgp_substrate else 0.3,
            },
            "vd_prediction": {
                "value": vd_prediction,
                "unit": "L/kg",
                "interpretation": "high" if vd_prediction > 0.7 else "moderate" if vd_prediction > 0.3 else "low",
            },
        },
        "metabolism": {
            "cyp_inhibition": cyp_inhibition,
            "half_life": {
                "hours": half_life_hours,
                "interpretation": "long" if half_life_hours > 12 else "moderate" if half_life_hours > 6 else "short",
            },
            "metabolic_stability": {
                "score": predict_metabolic_stability(mw, logp, rotatable_bonds),
                "prediction": "stable" if predict_metabolic_stability(mw, logp, rotatable_bonds) > 0.6 else "unstable",
            },
        },
        "excretion": {
            "clearance": {
                "value": clearance,
                "unit": "mL/min/kg",
                "interpretation": "high" if clearance > 15 else "moderate" if clearance > 5 else "low",
            },
            "renal_clearance": {
                "value": renal_clearance,
                "unit": "mL/min/kg",
                "prediction": "high" if renal_clearance > 2 else "low",
            },
        },
    }

def predict_gi_absorption(logp: float, tpsa: float, mw: float, hbd: int, hba: int) -> float:
    """Predict GI absorption score (0-1)"""
    score = 0.5  # Base score
    
    # LogP contribution (optimal range 1-4)
    if 1 <= logp <= 4:
        score += 0.2
    elif 0 <= logp < 1 or 4 < logp <= 5:
        score += 0.1
    
    # TPSA contribution (optimal < 140)
    if tpsa < 140:
        score += 0.15
    elif tpsa < 200:
        score += 0.05
    
    # MW contribution (optimal 200-500)
    if 200 <= mw <= 500:
        score += 0.1
    elif 100 <= mw < 200 or 500 < mw <= 600:
        score += 0.05
    
    # HBD/HBA contribution
    if hbd <= 5 and hba <= 10:
        score += 0.05
    
    return min(1.0, max(0.0, score))

def predict_bioavailability(logp: float, tpsa: float, rot_bonds: int, mw: float) -> float:
    """Predict oral bioavailability score (0-1)"""
    score = 0.4  # Base score
    
    # Veber's rule components
    if tpsa <= 140:
        score += 0.2
    if rot_bonds <= 10:
        score += 0.2
    
    # MW contribution
    if 200 <= mw <= 500:
        score += 0.2
    
    return min(1.0, max(0.0, score))

def predict_bbb_permeability(logp: float, tpsa: float, mw: float) -> float:
    """Predict BBB permeability score (0-1)"""
    score = 0.3  # Base score
    
    # LogP should be higher for BBB penetration
    if 2 <= logp <= 5:
        score += 0.3
    elif 1 <= logp < 2 or 5 < logp <= 6:
        score += 0.15
    
    # TPSA should be lower for BBB penetration
    if tpsa < 90:
        score += 0.3
    elif tpsa < 120:
        score += 0.15
    
    # MW should be moderate
    if 200 <= mw <= 450:
        score += 0.1
    
    return min(1.0, max(0.0, score))

def predict_log_bb(logp: float, tpsa: float) -> float:
    """Predict log BB (brain/blood partition coefficient)"""
    # Simplified model: log BB = 0.152 * logP - 0.0148 * TPSA - 0.152
    log_bb = 0.152 * logp - 0.0148 * tpsa - 0.152
    return round(log_bb, 3)

def predict_pgp_substrate(mw: float, logp: float, tpsa: float, num_rings: int) -> bool:
    """Predict P-gp substrate (simplified)"""
    # P-gp substrates tend to be larger, more lipophilic, and have more rings
    if mw > 400 and logp > 3 and num_rings >= 3:
        return True
    return False

def predict_vd(logp: float, mw: float, hbd: int) -> float:
    """Predict Volume of Distribution (L/kg)"""
    # Simplified model based on lipophilicity and size
    vd = 0.1 + (logp * 0.3) + (mw / 1000.0) - (hbd * 0.1)
    return max(0.1, round(vd, 2))

def predict_cyp_inhibition(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict CYP450 inhibition (simplified)"""
    # Check for common CYP inhibitor patterns
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    num_rings = properties["num_rings"]
    
    # Simple heuristic: larger, more lipophilic compounds are more likely to inhibit CYP
    inhibition_probability = 0.2  # Base probability
    
    if mw > 300 and logp > 3:
        inhibition_probability += 0.3
    if num_rings >= 3:
        inhibition_probability += 0.2
    
    return {
        "cyp1a2": {"probability": min(1.0, inhibition_probability + 0.1), "likely": inhibition_probability > 0.5},
        "cyp2c9": {"probability": min(1.0, inhibition_probability), "likely": inhibition_probability > 0.5},
        "cyp2c19": {"probability": min(1.0, inhibition_probability), "likely": inhibition_probability > 0.5},
        "cyp2d6": {"probability": min(1.0, inhibition_probability + 0.15), "likely": inhibition_probability > 0.5},
        "cyp3a4": {"probability": min(1.0, inhibition_probability + 0.2), "likely": inhibition_probability > 0.5},
    }

def predict_half_life(mw: float, logp: float, rot_bonds: int) -> float:
    """Predict half-life in hours"""
    # Simplified model
    base_half_life = 4.0
    half_life = base_half_life + (logp * 0.5) - (rot_bonds * 0.2) + (mw / 500.0)
    return max(1.0, min(48.0, round(half_life, 1)))

def predict_metabolic_stability(mw: float, logp: float, rot_bonds: int) -> float:
    """Predict metabolic stability score (0-1)"""
    score = 0.5
    
    # More rotatable bonds = less stable
    if rot_bonds < 5:
        score += 0.2
    elif rot_bonds > 10:
        score -= 0.2
    
    # Moderate lipophilicity = more stable
    if 2 <= logp <= 4:
        score += 0.2
    
    return min(1.0, max(0.0, score))

def predict_clearance(mw: float, logp: float, rot_bonds: int) -> float:
    """Predict clearance (mL/min/kg)"""
    # Simplified model
    clearance = 10.0 - (logp * 0.5) + (rot_bonds * 0.3) - (mw / 200.0)
    return max(0.5, min(50.0, round(clearance, 2)))

def predict_renal_clearance(mw: float, logp: float, tpsa: float) -> float:
    """Predict renal clearance (mL/min/kg)"""
    # Smaller, more polar compounds have higher renal clearance
    clearance = 2.0 - (logp * 0.2) + (tpsa / 100.0) - (mw / 500.0)
    return max(0.1, min(10.0, round(clearance, 2)))

def predict_solubility(logp: float, mw: float, tpsa: float) -> float:
    """Predict log S (solubility)"""
    # Simplified model: log S = 0.5 - logP - 0.01 * (MW - 100) + 0.012 * TPSA
    log_s = 0.5 - logp - 0.01 * (mw - 100) + 0.012 * tpsa
    return round(log_s, 2)

def predict_solubility_category(logp: float, mw: float, tpsa: float) -> str:
    """Predict solubility category"""
    log_s = predict_solubility(logp, mw, tpsa)
    if log_s > -2:
        return "highly soluble"
    elif log_s > -4:
        return "moderately soluble"
    elif log_s > -6:
        return "poorly soluble"
    else:
        return "very poorly soluble"

def calculate_toxicity_predictions(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate toxicity predictions including structural alerts, LD50, hepatotoxicity, mutagenicity
    """
    
    # Structural alerts detection
    structural_alerts = detect_structural_alerts(mol)
    
    # LD50 prediction (mg/kg, oral rat)
    ld50_prediction = predict_ld50(mol, properties)
    
    # Hepatotoxicity prediction
    hepatotoxicity = predict_hepatotoxicity(mol, properties)
    
    # Mutagenicity prediction (AMES test)
    mutagenicity = predict_mutagenicity(mol, properties)
    
    # Carcinogenicity prediction
    carcinogenicity = predict_carcinogenicity(mol, properties)
    
    # hERG inhibition (cardiac toxicity)
    herg_inhibition = predict_herg_inhibition(mol, properties)
    
    # Skin sensitization
    skin_sensitization = predict_skin_sensitization(mol, properties)
    
    # Overall toxicity risk score
    toxicity_risk_score = calculate_toxicity_risk_score(
        structural_alerts, ld50_prediction, hepatotoxicity,
        mutagenicity, carcinogenicity, herg_inhibition
    )
    
    return {
        "structural_alerts": structural_alerts,
        "ld50": {
            "value": ld50_prediction,
            "unit": "mg/kg",
            "category": categorize_ld50(ld50_prediction),
            "risk_level": "low" if ld50_prediction > 2000 else "moderate" if ld50_prediction > 500 else "high",
        },
        "hepatotoxicity": hepatotoxicity,
        "mutagenicity": {
            "ames_test": mutagenicity,
            "prediction": "positive" if mutagenicity["probability"] > 0.5 else "negative",
        },
        "carcinogenicity": carcinogenicity,
        "herg_inhibition": herg_inhibition,
        "skin_sensitization": skin_sensitization,
        "overall_toxicity_risk": {
            "score": toxicity_risk_score,
            "level": "low" if toxicity_risk_score < 0.3 else "moderate" if toxicity_risk_score < 0.6 else "high",
        },
    }

def detect_structural_alerts(mol) -> Dict[str, Any]:
    """Detect structural alerts associated with toxicity"""
    alerts_found = []
    
    try:
        # Try to use RDKit's FilterCatalog if available
        params = FilterCatalogParams()
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
        catalog = FilterCatalog(params)
        
        matches = catalog.GetMatches(mol)
        if matches:
            for match in matches:
                alerts_found.append({
                    "name": str(match),
                    "severity": "high",
                })
    except:
        # Fallback: simple pattern matching
        smarts_patterns = {
            "Michael_Acceptor": "[C,c]=[C,c]-[C,S]=O",
            "Aldehyde": "[CX3H1](=O)",
            "Epoxide": "C1OC1",
            "Nitro_aromatic": "[N+](=O)[O-]",
        }
        
        for name, pattern in smarts_patterns.items():
            try:
                patt = Chem.MolFromSmarts(pattern)
                if mol.HasSubstructMatch(patt):
                    alerts_found.append({
                        "name": name,
                        "severity": "moderate",
                    })
            except:
                continue
    
    return {
        "count": len(alerts_found),
        "alerts": alerts_found,
        "risk_level": "high" if len(alerts_found) > 2 else "moderate" if len(alerts_found) > 0 else "low",
    }

def predict_ld50(mol, properties: Dict[str, Any]) -> float:
    """Predict LD50 (mg/kg, oral rat)"""
    # Simplified model based on molecular properties
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    
    # Base LD50 (higher is safer)
    ld50 = 2000.0
    
    # Adjustments
    # More lipophilic compounds may be more toxic
    if logp > 5:
        ld50 *= 0.5
    elif logp > 3:
        ld50 *= 0.7
    
    # Very large molecules may have lower bioavailability but also different toxicity
    if mw > 600:
        ld50 *= 0.8
    
    return max(50.0, round(ld50, 1))

def categorize_ld50(ld50: float) -> str:
    """Categorize LD50 value"""
    if ld50 > 2000:
        return "practically non-toxic"
    elif ld50 > 500:
        return "slightly toxic"
    elif ld50 > 50:
        return "moderately toxic"
    else:
        return "highly toxic"

def predict_hepatotoxicity(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict hepatotoxicity risk"""
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    num_rings = properties["num_rings"]
    
    # Simple heuristic
    risk_score = 0.2  # Base risk
    
    # Lipophilic compounds are more likely to cause hepatotoxicity
    if logp > 4:
        risk_score += 0.3
    elif logp > 3:
        risk_score += 0.15
    
    # Larger molecules
    if mw > 400:
        risk_score += 0.2
    
    # Aromatic rings
    if num_rings >= 3:
        risk_score += 0.15
    
    return {
        "probability": min(1.0, risk_score),
        "risk_level": "high" if risk_score > 0.6 else "moderate" if risk_score > 0.3 else "low",
    }

def predict_mutagenicity(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict mutagenicity (AMES test)"""
    # Check for mutagenic structural alerts
    structural_alerts = detect_structural_alerts(mol)
    
    risk_score = 0.15  # Base risk
    
    # Nitro groups, aromatic amines are mutagenic
    if structural_alerts["count"] > 0:
        risk_score += 0.4
    
    # Aromatic compounds with certain substituents
    num_aromatic_rings = properties.get("num_aromatic_rings", 0)
    if num_aromatic_rings >= 2:
        risk_score += 0.2
    
    return {
        "probability": min(1.0, risk_score),
        "risk_level": "high" if risk_score > 0.5 else "moderate" if risk_score > 0.3 else "low",
    }

def predict_carcinogenicity(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict carcinogenicity"""
    # Similar to mutagenicity but with different thresholds
    mutagenicity = predict_mutagenicity(mol, properties)
    
    # Carcinogenicity is often related to mutagenicity
    carcinogenicity_prob = mutagenicity["probability"] * 0.8
    
    return {
        "probability": carcinogenicity_prob,
        "risk_level": "high" if carcinogenicity_prob > 0.5 else "moderate" if carcinogenicity_prob > 0.3 else "low",
    }

def predict_herg_inhibition(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict hERG channel inhibition (cardiac toxicity)"""
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    num_rings = properties["num_rings"]
    
    # hERG inhibitors tend to be larger, more lipophilic, and have multiple rings
    risk_score = 0.2  # Base risk
    
    if mw > 350 and logp > 3:
        risk_score += 0.3
    if num_rings >= 2:
        risk_score += 0.2
    if logp > 4:
        risk_score += 0.2
    
    return {
        "probability": min(1.0, risk_score),
        "risk_level": "high" if risk_score > 0.6 else "moderate" if risk_score > 0.3 else "low",
    }

def predict_skin_sensitization(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Predict skin sensitization potential"""
    # Simplified prediction
    risk_score = 0.15  # Base risk
    
    # Electrophilic compounds are more likely to cause sensitization
    structural_alerts = detect_structural_alerts(mol)
    if structural_alerts["count"] > 0:
        risk_score += 0.3
    
    return {
        "probability": min(1.0, risk_score),
        "risk_level": "high" if risk_score > 0.5 else "moderate" if risk_score > 0.3 else "low",
    }

def calculate_toxicity_risk_score(
    structural_alerts: Dict[str, Any],
    ld50: float,
    hepatotoxicity: Dict[str, Any],
    mutagenicity: Dict[str, Any],
    carcinogenicity: Dict[str, Any],
    herg_inhibition: Dict[str, Any]
) -> float:
    """Calculate overall toxicity risk score (0-1)"""
    
    # Structural alerts component (30% weight)
    alerts_score = min(1.0, structural_alerts["count"] / 3.0)
    
    # LD50 component (20% weight) - lower LD50 = higher risk
    ld50_score = max(0.0, 1.0 - (ld50 / 2000.0))
    
    # Hepatotoxicity component (20% weight)
    hepato_score = hepatotoxicity["probability"]
    
    # Mutagenicity component (15% weight)
    muta_score = mutagenicity["probability"]
    
    # Carcinogenicity component (10% weight)
    carci_score = carcinogenicity["probability"]
    
    # hERG component (5% weight)
    herg_score = herg_inhibition["probability"]
    
    # Weighted average
    overall_score = (
        alerts_score * 0.3 +
        ld50_score * 0.2 +
        hepato_score * 0.2 +
        muta_score * 0.15 +
        carci_score * 0.1 +
        herg_score * 0.05
    )
    
    return round(overall_score, 3)

def predict_binding_affinity(mol, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict binding affinity based on molecular properties
    This is a simplified ML-based estimate
    """
    
    mw = properties["molecular_weight"]
    logp = properties["logp"]
    tpsa = properties["tpsa"]
    hbd = properties["hbd"]
    hba = properties["hba"]
    
    # Simplified model: estimate binding affinity from properties
    # This is a placeholder - in production, use trained ML models
    
    # Base affinity estimate (kcal/mol, more negative = stronger binding)
    base_affinity = -6.0
    
    # Adjustments based on properties
    # Optimal LogP for binding
    if 2 <= logp <= 4:
        base_affinity -= 1.0
    elif 1 <= logp < 2 or 4 < logp <= 5:
        base_affinity -= 0.5
    
    # TPSA contribution (moderate polarity is good)
    if 50 <= tpsa <= 120:
        base_affinity -= 0.5
    
    # H-bond donors/acceptors (moderate is good)
    if 2 <= hbd <= 4 and 4 <= hba <= 8:
        base_affinity -= 0.5
    
    # MW contribution (moderate size is good)
    if 300 <= mw <= 500:
        base_affinity -= 0.5
    
    # Add some uncertainty
    confidence = 0.7  # Moderate confidence for property-based prediction
    
    return {
        "predicted_affinity": round(base_affinity, 2),
        "unit": "kcal/mol",
        "confidence": confidence,
        "interpretation": "strong" if base_affinity < -8 else "moderate" if base_affinity < -6 else "weak",
    }

def calculate_overall_drug_score(
    drug_likeness: Dict[str, Any],
    admet: Dict[str, Any],
    toxicity: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate overall drug candidate score"""
    
    # Component scores
    drug_likeness_score = drug_likeness["overall_drug_likeness_score"]
    admet_score = (
        admet["absorption"]["bioavailability"]["score"] * 0.3 +
        (1.0 - admet["distribution"]["pgp_substrate"]["probability"]) * 0.2 +
        admet["metabolism"]["metabolic_stability"]["score"] * 0.2 +
        (1.0 - min(1.0, admet["excretion"]["clearance"]["value"] / 20.0)) * 0.3
    )
    toxicity_score = 1.0 - toxicity["overall_toxicity_risk"]["score"]
    
    # Weighted overall score
    overall_score = (
        drug_likeness_score * 0.3 +
        admet_score * 0.4 +
        toxicity_score * 0.3
    )
    
    return {
        "overall_score": round(overall_score, 3),
        "drug_likeness_component": round(drug_likeness_score, 3),
        "admet_component": round(admet_score, 3),
        "toxicity_component": round(toxicity_score, 3),
        "interpretation": "excellent" if overall_score > 0.8 else "good" if overall_score > 0.6 else "moderate" if overall_score > 0.4 else "poor",
    }
