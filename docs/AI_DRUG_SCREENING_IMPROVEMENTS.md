# AI Drug Screening Improvements

## Overview
Enhanced the AI Drug Screening feature with ML-powered analysis of binding affinity, drug-likeness, ADMET properties, and toxicity predictions for every candidate.

## Key Improvements

### 1. ML-Powered Molecular Property Prediction Service
**File**: `backend/services/molecular_properties.py`

- **RDKit Integration**: Comprehensive molecular descriptor calculation using RDKit
- **Basic Descriptors**: Molecular weight, LogP, H-bond donors/acceptors, TPSA, rotatable bonds, ring counts, etc.
- **Drug-Likeness Scoring**:
  - Lipinski's Rule of Five (with violation tracking)
  - QED (Quantitative Estimate of Drug-likeness) score
  - Veber's Rule (oral bioavailability)
  - Egan's Rule (GI absorption)
  - Muegge's Rule (comprehensive drug-likeness)
  - Synthetic Accessibility (SA) score estimation
  - Overall drug-likeness score (weighted combination)

### 2. ADMET Property Predictions
**Comprehensive ADMET Analysis**:

- **Absorption**:
  - GI absorption prediction
  - Bioavailability estimation (percentage)
  - Solubility prediction (log S)
  
- **Distribution**:
  - BBB (Blood-Brain Barrier) permeability
  - log BB (brain/blood partition coefficient)
  - P-gp substrate prediction
  - Volume of Distribution (VD) prediction
  
- **Metabolism**:
  - CYP450 inhibition predictions (CYP1A2, CYP2C9, CYP2C19, CYP2D6, CYP3A4)
  - Half-life prediction (hours)
  - Metabolic stability assessment
  
- **Excretion**:
  - Clearance prediction (mL/min/kg)
  - Renal clearance prediction

### 3. Toxicity Predictions
**Comprehensive Toxicity Assessment**:

- **Structural Alerts**: Detection of toxicophoric groups and structural alerts
- **LD50 Prediction**: Predicted lethal dose (mg/kg, oral rat) with categorization
- **Hepatotoxicity**: Liver toxicity risk assessment
- **Mutagenicity**: AMES test prediction
- **Carcinogenicity**: Cancer risk assessment
- **hERG Inhibition**: Cardiac toxicity prediction
- **Skin Sensitization**: Dermal sensitization potential
- **Overall Toxicity Risk Score**: Weighted combination of all toxicity factors

### 4. Binding Affinity Predictions
- ML-based binding affinity estimation from molecular properties
- Confidence scoring for predictions
- Integration with docking results for validation

### 5. Enhanced AI Report Service
**File**: `backend/services/ai_report.py`

- Integrated ML predictions into AI-generated reports
- Enhanced prompts to include ADMET and toxicity analysis
- Contextual analysis combining docking results with ML predictions
- Stakeholder-specific insights incorporating molecular properties

### 6. Backend Schema Updates
**File**: `backend/schemas.py`

- Added `MolecularPropertiesResponse` schema
- Added `DrugLikenessScores` schema
- Added `ADMETProperties` schema
- Added `ToxicityPredictions` schema
- Enhanced `AIAnalysisResponse` to include ADMET and toxicity data

### 7. Frontend Components
**New Components**:

- **`admet-properties-panel.tsx`**: Comprehensive ADMET visualization panel
  - Absorption metrics with progress bars
  - Distribution properties (BBB, P-gp, VD)
  - Metabolism indicators (CYP inhibition, half-life, stability)
  - Excretion metrics (clearance, renal clearance)

- **`toxicity-predictions-panel.tsx`**: Detailed toxicity assessment panel
  - Overall toxicity risk score
  - Structural alerts display
  - LD50 prediction
  - Specific toxicity predictions (hepatotoxicity, mutagenicity, carcinogenicity, hERG)

**Enhanced Components**:

- **`drug-likeness-radar.tsx`**: Updated to use real ADMET data from ML predictions
- **`ai-analysis-panel.tsx`**: Integrated ADMET and toxicity panels

### 8. Updated Dependencies
**File**: `backend/requirements.txt`

- Added `rdkit-pypi==2023.9.1` for molecular property calculations
- Added `numpy==1.26.3` for numerical computations

## Usage

### Backend API
The ML predictions are automatically integrated into the AI analysis endpoint:

```python
POST /jobs/{job_id}/analyze
{
  "analysis_type": "comprehensive",
  "stakeholder_type": "researcher",
  "include_visualizations": true
}
```

Response includes:
- `admet_properties`: Complete ADMET predictions
- `toxicity_predictions`: Comprehensive toxicity assessment
- `analysis`: AI-generated analysis incorporating ML predictions

### Frontend
The AI Analysis Panel automatically displays:
- ADMET Properties Panel with all absorption, distribution, metabolism, and excretion metrics
- Toxicity Predictions Panel with risk assessments
- Drug-Likeness Radar Chart updated with real ML prediction data

## Technical Details

### ML Models Used
- **RDKit**: For molecular descriptor calculation and basic property prediction
- **Rule-Based Models**: For drug-likeness rules (Lipinski, Veber, Egan, Muegge)
- **Heuristic Models**: For ADMET property predictions based on molecular descriptors
- **Statistical Models**: For toxicity risk assessment

### Prediction Confidence
- All predictions include confidence scores
- Uncertainty quantification for critical predictions
- Integration with docking confidence for holistic assessment

### Performance Considerations
- ML predictions calculated for top ligands only (top 3 by default)
- Caching opportunities for repeated ligand analysis
- Graceful fallback when RDKit is unavailable

## Future Enhancements

1. **Advanced ML Models**: Integration of trained neural networks for more accurate predictions
2. **External API Integration**: Connect to specialized ADMET prediction services
3. **Batch Processing**: Optimize for analyzing large ligand libraries
4. **Model Retraining**: Ability to fine-tune models on proprietary data
5. **Uncertainty Quantification**: Enhanced confidence intervals for predictions
6. **Visualization Enhancements**: Interactive charts and molecular property overlays

## Notes

- RDKit is required for ML predictions. If not available, the system gracefully falls back to template-based analysis
- Predictions are based on computational models and should be validated experimentally
- All toxicity predictions are estimates and should not replace experimental safety testing
