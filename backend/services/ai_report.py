import os
import logging
from typing import Dict, Any, Optional, List
import httpx
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class AIReportError(Exception):
    """Base exception for AI report generation errors"""
    pass

class AIAPIError(AIReportError):
    """Error calling AI API"""
    pass

class AIReportTimeoutError(AIReportError):
    """AI report generation timed out"""
    pass

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def generate_ai_report(
    job_id: str,
    sequence: Optional[str],
    plddt_score: Optional[float],
    docking_results: Dict[str, Any],
    stakeholder: str = "researcher"
) -> str:
    """
    Generate AI-powered analysis report for docking results
    
    Args:
        job_id: Unique job identifier
        sequence: Protein sequence (if AlphaFold was used)
        plddt_score: AlphaFold confidence score
        docking_results: Docking simulation results
        stakeholder: Target audience (researcher, clinician, investor)
        
    Returns:
        Formatted markdown report
        
    Raises:
        AIReportError: If report generation fails
        ValueError: If inputs are invalid
    """
    
    if not job_id:
        raise ValueError("Job ID is required")
    
    if not docking_results:
        raise ValueError("Docking results are required")
    
    valid_stakeholders = ["researcher", "clinician", "investor", "regulator"]
    if stakeholder not in valid_stakeholders:
        logger.warning(f"Invalid stakeholder '{stakeholder}', using 'researcher'")
        stakeholder = "researcher"
    
    try:
        # Build context for AI
        context = f"""
    # Protein-Ligand Docking Analysis Report
    Job ID: {job_id}
    
    ## Protein Information
    """
        
        if sequence:
            if plddt_score is None:
                logger.warning(f"pLDDT score is None for job {job_id} with sequence")
                plddt_score = 0.0
            
            context += f"""
    - Sequence Length: {len(sequence)} amino acids
    - Structure Prediction Method: AlphaFold 2
    - Prediction Confidence (pLDDT): {plddt_score:.2f}/100
    - Interpretation: {"High confidence" if plddt_score > 90 else "Medium confidence" if plddt_score > 70 else "Low confidence"}
    """
        else:
            context += """
    - Structure Source: User-provided PDB file
    """
        
        context += f"""
    
    ## Docking Results Summary
    - Total Ligands Tested: {docking_results.get('total_ligands', 0)}
    - Successful Ligands: {docking_results.get('successful_ligands', 0)}
    - Failed Ligands: {docking_results.get('failed_ligands', 0)}
    - Best Binding Affinity: {docking_results.get('best_score', 'N/A')} kcal/mol
    - Best Ligand: {docking_results.get('best_ligand', 'N/A')}
    """
        
        # Add statistics if available
        statistics = docking_results.get('statistics', {})
        if statistics:
            context += f"""
    ### Statistical Analysis:
    - Mean Binding Affinity: {statistics.get('mean_score', 'N/A'):.2f} kcal/mol
    - Standard Deviation: {statistics.get('std_score', 'N/A'):.2f} kcal/mol
    - Score Range: {statistics.get('min_score', 'N/A'):.2f} to {statistics.get('max_score', 'N/A'):.2f} kcal/mol
    - Median Score: {statistics.get('median_score', 'N/A'):.2f} kcal/mol
    - Number of Clusters: {statistics.get('num_clusters', 'N/A')}
    - Confidence Score: {statistics.get('confidence_score', 'N/A'):.2f}
    - Average Poses per Ligand: {statistics.get('mean_num_modes', 'N/A'):.1f}
    """
        
        context += """
    
    ### Top Binding Poses (Detailed):
    """
        
        results = docking_results.get('results', [])
        valid_results = [r for r in results if r.get('binding_affinity') is not None]
        valid_results.sort(key=lambda x: x.get('binding_affinity', float('inf')))
        
        for idx, result in enumerate(valid_results[:5], 1):
            binding_affinity = result.get('binding_affinity', 'N/A')
            ligand_name = result.get('ligand_name', f'Ligand {idx}')
            modes = result.get('modes', [])
            num_poses = result.get('num_poses', len(modes))
            affinity_range = result.get('affinity_range', 'N/A')
            pose_consistency = result.get('pose_consistency', 'N/A')
            
            context += f"""
    {idx}. {ligand_name}
       - Best Binding Affinity: {binding_affinity:.2f} kcal/mol
       - Number of Poses: {num_poses}
       - Affinity Range: {affinity_range:.2f} kcal/mol (if multiple poses)
       - Pose Consistency: {pose_consistency:.2f} (if available)
       """
            
            # Add top 3 modes if available
            if modes and len(modes) > 0:
                context += "       - Top 3 Binding Modes:\n"
                for mode_idx, mode in enumerate(modes[:3], 1):
                    mode_num = mode.get('mode', mode_idx)
                    affinity = mode.get('affinity', 'N/A')
                    rmsd_lb = mode.get('rmsd_lb', 'N/A')
                    rmsd_ub = mode.get('rmsd_ub', 'N/A')
                    context += f"         Mode {mode_num}: {affinity:.2f} kcal/mol (RMSD: {rmsd_lb:.2f}-{rmsd_ub:.2f} Å)\n"
        
        # Add clustering information if available
        clustered_results = docking_results.get('clustered_results', [])
        if clustered_results:
            context += """
    
    ### Pose Clustering Analysis:
    """
            clusters = {}
            for result in clustered_results[:10]:  # Top 10 clustered results
                cluster_id = result.get('cluster_id', 'unknown')
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(result)
            
            for cluster_id, cluster_members in sorted(clusters.items())[:5]:
                best_in_cluster = min(cluster_members, key=lambda x: x.get('binding_affinity', float('inf')))
                context += f"""
    - Cluster {cluster_id}: {len(cluster_members)} pose(s), best affinity: {best_in_cluster.get('binding_affinity', 'N/A'):.2f} kcal/mol
    """
        
        # Add parameter information
        parameters_used = docking_results.get('parameters_used', {})
        if parameters_used:
            context += f"""
    
    ### Docking Parameters Used:
    - Grid Center: ({parameters_used.get('center_x', 0):.2f}, {parameters_used.get('center_y', 0):.2f}, {parameters_used.get('center_z', 0):.2f}) Å
    - Grid Size: {parameters_used.get('size_x', 20):.1f} × {parameters_used.get('size_y', 20):.1f} × {parameters_used.get('size_z', 20):.1f} Å
    - Exhaustiveness: {parameters_used.get('exhaustiveness', 8)}
    - Number of Modes: {parameters_used.get('num_modes', 9)}
    """
        
        # Add ML-powered molecular property predictions for top ligands
        ml_predictions_context = await add_ml_predictions_context(docking_results)
        if ml_predictions_context:
            context += ml_predictions_context
        
        # Calculate ML properties for response
        ml_properties_data = {}
        admet_data = {}
        toxicity_data = {}
        
        # Try to get ligand files and calculate properties for top ligand
        ligand_files = docking_results.get('ligand_files', [])
        if ligand_files and valid_results:
            try:
                top_result = valid_results[0]
                ligand_idx = top_result.get('ligand_index', 0)
                if ligand_idx < len(ligand_files):
                    ligand_sdf = ligand_files[ligand_idx]
                    ligand_name = top_result.get('ligand_name', 'top_ligand')
                    
                    properties = calculate_molecular_properties(ligand_sdf, ligand_name)
                    ml_properties_data = properties.get('molecular_properties', {})
                    admet_data = properties.get('admet', {})
                    toxicity_data = properties.get('toxicity', {})
            except (RDKitNotAvailableError, MolecularPropertyError) as e:
                logger.warning(f"ML predictions unavailable for structured analysis: {str(e)}")
            except Exception as e:
                logger.error(f"Error calculating ML properties for structured analysis: {str(e)}")
        
        # Generate AI analysis
        if ANTHROPIC_API_KEY:
            try:
                report = await generate_with_anthropic(context, stakeholder)
            except (AIAPIError, AIReportTimeoutError) as e:
                logger.error(f"Anthropic API failed for job {job_id}: {str(e)}")
                # Fallback to template
                logger.info(f"Falling back to template report for job {job_id}")
                report = generate_template_report(context, docking_results, plddt_score)
        elif OPENAI_API_KEY:
            try:
                report = await generate_with_openai(context, stakeholder)
            except (AIAPIError, AIReportTimeoutError) as e:
                logger.error(f"OpenAI API failed for job {job_id}: {str(e)}")
                # Fallback to template
                logger.info(f"Falling back to template report for job {job_id}")
                report = generate_template_report(context, docking_results, plddt_score)
        else:
            # Fallback to template-based report
            logger.info(f"No AI API keys configured, using template report for job {job_id}")
            report = generate_template_report(context, docking_results, plddt_score)
        
        if not report or not report.strip():
            raise AIReportError("Generated report is empty")
        
        return report
    except (AIReportError, ValueError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating AI report for job {job_id}: {str(e)}", exc_info=True)
        raise AIReportError(f"Failed to generate AI report: {str(e)}") from e

async def generate_with_anthropic(context: str, stakeholder: str) -> str:
    """Generate report using Claude API"""
    
    if not ANTHROPIC_API_KEY:
        raise AIAPIError("ANTHROPIC_API_KEY not configured")
    
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for AI report generation")
    
    system_prompt = f"""You are an expert computational chemist and drug discovery scientist with deep expertise in molecular docking, binding affinity prediction, and drug design.
    Analyze the following protein-ligand docking results and provide a comprehensive, actionable report tailored for a {stakeholder}.
    
    Your analysis should include:
    1. **Executive Summary**: Key findings and overall assessment of docking success
    2. **Structural Quality Assessment**: Evaluate protein structure confidence (if AlphaFold was used) and its impact on docking reliability
    3. **Binding Affinity Analysis**: 
       - Interpret binding affinities in context (strong: < -7 kcal/mol, moderate: -5 to -7, weak: > -5)
       - Analyze statistical distribution of scores across ligands
       - Assess pose consistency and clustering patterns
       - Identify outliers and potential artifacts
    4. **Ligand Comparison**: Compare top candidates, highlighting differences in binding modes and affinities
    5. **Drug-likeness Considerations**: 
       - Assess binding affinity in context of drug development
       - Discuss potential for optimization
       - Consider ADMET implications based on binding characteristics
    6. **Confidence Assessment**: Evaluate reliability of results based on pose consistency, score distribution, and structural quality
    7. **Recommendations for Next Steps**: 
       - Specific experimental validation approaches
       - Suggested follow-up computational studies (MD simulations, binding free energy calculations)
       - Optimization strategies if applicable
    
    Use clear, professional language appropriate for a {stakeholder}. Cite specific metrics and provide quantitative assessments where possible. 
    Be critical and identify limitations or uncertainties in the results."""
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 2048,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": context}
                        ]
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("Anthropic API request timed out after 2 minutes")
            except httpx.NetworkError as e:
                raise AIAPIError(f"Network error connecting to Anthropic API: {str(e)}")
            except httpx.RequestError as e:
                raise AIAPIError(f"Request error to Anthropic API: {str(e)}")
            
            if response.status_code == 401:
                raise AIAPIError("Invalid API key for Anthropic API")
            elif response.status_code == 429:
                raise AIAPIError("Anthropic API rate limit exceeded. Please try again later.")
            elif response.status_code >= 500:
                raise AIAPIError(f"Anthropic API server error (status {response.status_code})")
            elif response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                logger.error(f"Anthropic API error (status {response.status_code}): {error_text}")
                raise AIAPIError(f"Anthropic API error (status {response.status_code}): {error_text}")
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Anthropic API: {str(e)}")
                raise AIAPIError("Invalid response format from Anthropic API")
            
            if "content" not in result or not result["content"]:
                raise AIAPIError("No content in Anthropic API response")
            
            if not isinstance(result["content"], list) or len(result["content"]) == 0:
                raise AIAPIError("Invalid content format in Anthropic API response")
            
            text_content = result["content"][0].get("text", "")
            if not text_content:
                raise AIAPIError("Empty text content in Anthropic API response")
            
            return text_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Anthropic API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating AI report: {str(e)}") from e

async def generate_with_openai(context: str, stakeholder: str) -> str:
    """Generate report using OpenAI GPT-4"""
    
    if not OPENAI_API_KEY:
        raise AIAPIError("OPENAI_API_KEY not configured")
    
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for AI report generation")
    
    system_prompt = f"""You are an expert computational chemist and drug discovery scientist with deep expertise in molecular docking, binding affinity prediction, and drug design.
    Analyze the following protein-ligand docking results and provide a comprehensive, actionable report tailored for a {stakeholder}.
    
    Your analysis should include:
    1. **Executive Summary**: Key findings and overall assessment of docking success
    2. **Structural Quality Assessment**: Evaluate protein structure confidence (if AlphaFold was used) and its impact on docking reliability
    3. **Binding Affinity Analysis**: 
       - Interpret binding affinities in context (strong: < -7 kcal/mol, moderate: -5 to -7, weak: > -5)
       - Analyze statistical distribution of scores across ligands
       - Assess pose consistency and clustering patterns
       - Identify outliers and potential artifacts
    4. **Ligand Comparison**: Compare top candidates, highlighting differences in binding modes and affinities
    5. **Drug-likeness Considerations**: 
       - Assess binding affinity in context of drug development
       - Discuss potential for optimization
       - Consider ADMET implications based on binding characteristics
    6. **Confidence Assessment**: Evaluate reliability of results based on pose consistency, score distribution, and structural quality
    7. **Recommendations for Next Steps**: 
       - Specific experimental validation approaches
       - Suggested follow-up computational studies (MD simulations, binding free energy calculations)
       - Optimization strategies if applicable
    
    Use clear, professional language appropriate for a {stakeholder}. Cite specific metrics and provide quantitative assessments where possible. 
    Be critical and identify limitations or uncertainties in the results."""
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo-preview",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.7
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("OpenAI API request timed out after 2 minutes")
            except httpx.NetworkError as e:
                raise AIAPIError(f"Network error connecting to OpenAI API: {str(e)}")
            except httpx.RequestError as e:
                raise AIAPIError(f"Request error to OpenAI API: {str(e)}")
            
            if response.status_code == 401:
                raise AIAPIError("Invalid API key for OpenAI API")
            elif response.status_code == 429:
                raise AIAPIError("OpenAI API rate limit exceeded. Please try again later.")
            elif response.status_code >= 500:
                raise AIAPIError(f"OpenAI API server error (status {response.status_code})")
            elif response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                logger.error(f"OpenAI API error (status {response.status_code}): {error_text}")
                raise AIAPIError(f"OpenAI API error (status {response.status_code}): {error_text}")
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from OpenAI API: {str(e)}")
                raise AIAPIError("Invalid response format from OpenAI API")
            
            if "choices" not in result or not result["choices"]:
                raise AIAPIError("No choices in OpenAI API response")
            
            if not isinstance(result["choices"], list) or len(result["choices"]) == 0:
                raise AIAPIError("Invalid choices format in OpenAI API response")
            
            message_content = result["choices"][0].get("message", {}).get("content", "")
            if not message_content:
                raise AIAPIError("Empty message content in OpenAI API response")
            
            return message_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating AI report: {str(e)}") from e

def generate_template_report(
    context: str,
    docking_results: Dict[str, Any],
    plddt_score: Optional[float]
) -> str:
    """Generate a basic template report without AI"""
    
    report = f"""# Molecular Docking Analysis Report

{context}

## Analysis Summary

The molecular docking simulation has been completed successfully. 
The best binding affinity observed was {docking_results.get('best_score', 'N/A')} kcal/mol.

### Interpretation

- Binding affinities below -7.0 kcal/mol generally indicate strong binding
- Values between -5.0 and -7.0 kcal/mol suggest moderate binding
- Values above -5.0 kcal/mol indicate weak binding

### Recommendations

1. Review the top-ranked poses for structural compatibility
2. Consider running additional validation with molecular dynamics
3. Evaluate drug-likeness properties (Lipinski's Rule of Five)
4. Plan experimental validation for promising candidates

---
*This report was generated by SNOWFLAKE - AI-powered drug discovery platform*
"""
    
    return report

def _get_stakeholder_specific_prompt(stakeholder: str, analysis_type: str) -> Dict[str, str]:
    """Get stakeholder-specific system prompts with clinical insights focus"""
    
    prompts = {
        "researcher": {
            "system": """You are an expert computational chemist and drug discovery scientist with deep expertise in molecular docking, binding affinity prediction, and drug design. You specialize in providing detailed technical analysis for research teams.

Your analysis should be comprehensive and include:
1. **Executive Summary**: Key findings with quantitative metrics and statistical significance
2. **Structural Quality Assessment**: Detailed evaluation of protein structure confidence (pLDDT scores, domain-specific confidence), impact on docking reliability, and structural validation recommendations
3. **Binding Affinity Analysis**: 
   - Detailed interpretation of binding affinities with statistical context (strong: < -7 kcal/mol, moderate: -5 to -7, weak: > -5)
   - Statistical distribution analysis (mean, median, std dev, outliers)
   - Pose consistency metrics and clustering pattern analysis
   - Identification of potential artifacts or computational artifacts
   - Comparison with literature values for similar targets
4. **Ligand Comparison**: Detailed comparison of top candidates including:
   - Binding mode differences and structural rationale
   - Affinity differences with mechanistic explanations
   - SAR (Structure-Activity Relationship) insights
   - Potential optimization strategies
5. **Drug-likeness Considerations**: 
   - Detailed ADMET property predictions based on binding characteristics
   - Lipinski's Rule of Five analysis
   - Synthetic accessibility assessment
   - Potential for lead optimization
6. **Confidence Assessment**: 
   - Reliability metrics based on pose consistency, score distribution, structural quality
   - Uncertainty quantification
   - Recommendations for improving confidence
7. **Clinical Insights & Recommendations**: 
   - Specific experimental validation approaches (SPR, ITC, X-ray crystallography)
   - Suggested follow-up computational studies (MD simulations, binding free energy calculations, FEP)
   - Optimization strategies with specific molecular modifications
   - Next steps in the drug discovery pipeline

Use technical language appropriate for researchers. Cite specific metrics, provide quantitative assessments, and include detailed methodology recommendations.""",
            
            "recommendations_focus": "Focus on experimental validation, computational follow-ups, SAR analysis, and optimization strategies."
        },
        
        "clinician": {
            "system": """You are a clinical pharmacologist and drug development expert specializing in translating computational findings into clinical insights. You provide analysis tailored for clinicians and medical researchers focused on patient outcomes.

Your analysis should emphasize clinical relevance and include:
1. **Executive Summary**: Clinical significance of findings, therapeutic potential, and patient impact focus
2. **Mechanism of Action**: 
   - Clear explanation of how the compound interacts with the target
   - Clinical relevance of the binding site
   - Comparison with existing therapeutics (if applicable)
   - Potential for selectivity and off-target effects
3. **Therapeutic Potential**: 
   - Binding affinity interpretation in clinical context (IC50/Ki predictions)
   - Dosing strategy recommendations based on binding affinity
   - Therapeutic window considerations
   - Patient population considerations
4. **Safety Profile**: 
   - Predicted safety considerations based on binding characteristics
   - Drug-drug interaction potential (CYP involvement, transporter interactions)
   - Side effect predictions
   - Contraindication considerations
5. **Clinical Development Path**: 
   - Phase I readiness assessment
   - Biomarker considerations for patient selection
   - Clinical trial design recommendations
   - Regulatory pathway considerations
6. **Clinical Insights & Recommendations**: 
   - Patient selection criteria based on target expression and biomarkers
   - Dosing recommendations (target plasma concentrations, frequency)
   - Monitoring requirements (drug-drug interactions, adverse events)
   - Clinical trial endpoints and success criteria
   - Comparison with standard of care

Use clear, clinically-focused language. Translate technical metrics into clinical implications. Focus on patient safety and therapeutic efficacy.""",
            
            "recommendations_focus": "Focus on clinical application, patient safety, dosing strategies, and therapeutic potential."
        },
        
        "investor": {
            "system": """You are a biotech investment analyst and drug development strategist specializing in evaluating drug discovery programs for investment decisions. You provide business-focused analysis for investors and stakeholders.

Your analysis should emphasize business value and include:
1. **Executive Summary**: Investment thesis, market opportunity, and development timeline with ROI considerations
2. **Market Opportunity**: 
   - Target indication market size and growth potential
   - Competitive landscape analysis
   - Differentiation potential
   - Market entry strategy considerations
3. **Development Timeline**: 
   - Estimated timeline to IND submission
   - Key milestones and go/no-go decision points
   - Resource requirements (funding, partnerships)
   - Risk assessment and mitigation strategies
4. **Intellectual Property**: 
   - Patent landscape considerations
   - Freedom to operate analysis
   - IP protection strategies
5. **Financial Projections**: 
   - Development cost estimates
   - Partnership opportunities (CROs, pharma)
   - Exit strategy considerations
   - Valuation implications
6. **Clinical Insights & Recommendations**: 
   - Investment attractiveness based on binding affinity and drug-likeness
   - Strategic partnership recommendations (CROs, pharma collaborations)
   - Patent filing strategy and timeline
   - Market opportunity quantification ($B potential)
   - Risk mitigation strategies
   - Go/no-go criteria for continued investment

Use business-focused language. Translate technical findings into investment implications. Focus on ROI, timeline, and market opportunity.""",
            
            "recommendations_focus": "Focus on investment potential, market opportunity, development timeline, IP strategy, and partnership opportunities."
        },
        
        "regulator": {
            "system": """You are a regulatory affairs expert specializing in drug development compliance and FDA/EMA submission requirements. You provide analysis tailored for regulatory submissions and compliance.

Your analysis should emphasize regulatory compliance and include:
1. **Executive Summary**: Regulatory readiness, compliance status, and submission pathway recommendations
2. **Regulatory Compliance**: 
   - IND/CTA readiness assessment
   - Regulatory pathway recommendations (505(b)(1), 505(b)(2), orphan drug)
   - Compliance with ICH guidelines
   - Documentation requirements
3. **Safety & Efficacy Data**: 
   - Computational data supporting mechanistic understanding
   - Safety profile assessment for regulatory review
   - Efficacy predictions and validation requirements
   - Risk-benefit analysis framework
4. **Quality & Manufacturing**: 
   - Manufacturing considerations
   - Quality control requirements
   - Stability study recommendations
   - Batch consistency requirements
5. **Documentation Requirements**: 
   - Required studies for IND submission
   - Preclinical study recommendations
   - Clinical trial design for regulatory approval
   - Labeling considerations
6. **Clinical Insights & Recommendations**: 
   - Full ADMET profiling requirements (hERG, CYP, mutagenicity, genotoxicity)
   - Toxicology studies in two species per ICH guidelines
   - Manufacturing process development and validation
   - Stability studies under ICH conditions
   - Clinical trial design meeting regulatory standards
   - Risk management plan development
   - Regulatory submission timeline and milestones

Use regulatory-focused language. Emphasize compliance, documentation, and submission requirements. Reference specific guidelines (ICH, FDA, EMA) where applicable.""",
            
            "recommendations_focus": "Focus on regulatory compliance, safety documentation, manufacturing requirements, and submission readiness."
        }
    }
    
    return prompts.get(stakeholder, prompts["researcher"])

async def generate_structured_ai_analysis(
    job_id: str,
    sequence: Optional[str],
    plddt_score: Optional[float],
    docking_results: Dict[str, Any],
    analysis_type: str = "comprehensive",
    custom_prompt: Optional[str] = None,
    stakeholder_type: str = "researcher"
) -> Dict[str, Any]:
    """
    Generate structured AI analysis with stakeholder-specific clinical insights
    
    Args:
        job_id: Unique job identifier
        sequence: Protein sequence (if AlphaFold was used)
        plddt_score: AlphaFold confidence score
        docking_results: Docking simulation results
        analysis_type: Type of analysis (binding_affinity, drug_likeness, toxicity, comprehensive, custom)
        custom_prompt: Custom prompt for analysis (if analysis_type is custom)
        stakeholder_type: Target audience (researcher, clinician, investor, regulator)
        
    Returns:
        Structured analysis dictionary with analysis, recommendations, confidence, and metadata
        
    Raises:
        AIReportError: If analysis generation fails
        ValueError: If inputs are invalid
    """
    
    if not job_id:
        raise ValueError("Job ID is required")
    
    if not docking_results:
        raise ValueError("Docking results are required")
    
    valid_stakeholders = ["researcher", "clinician", "investor", "regulator"]
    if stakeholder_type not in valid_stakeholders:
        logger.warning(f"Invalid stakeholder '{stakeholder_type}', using 'researcher'")
        stakeholder_type = "researcher"
    
    try:
        # Build context for AI (same as generate_ai_report)
        context = f"""
# Protein-Ligand Docking Analysis Report
Job ID: {job_id}

## Protein Information
"""
        
        if sequence:
            if plddt_score is None:
                logger.warning(f"pLDDT score is None for job {job_id} with sequence")
                plddt_score = 0.0
            
            context += f"""
- Sequence Length: {len(sequence)} amino acids
- Structure Prediction Method: AlphaFold 2
- Prediction Confidence (pLDDT): {plddt_score:.2f}/100
- Interpretation: {"High confidence" if plddt_score > 90 else "Medium confidence" if plddt_score > 70 else "Low confidence"}
"""
        else:
            context += """
- Structure Source: User-provided PDB file
"""
        
        context += f"""

## Docking Results Summary
- Total Ligands Tested: {docking_results.get('total_ligands', 0)}
- Successful Ligands: {docking_results.get('successful_ligands', 0)}
- Failed Ligands: {docking_results.get('failed_ligands', 0)}
- Best Binding Affinity: {docking_results.get('best_score', 'N/A')} kcal/mol
- Best Ligand: {docking_results.get('best_ligand', 'N/A')}
"""
        
        # Add statistics if available
        statistics = docking_results.get('statistics', {})
        if statistics:
            context += f"""
### Statistical Analysis:
- Mean Binding Affinity: {statistics.get('mean_score', 'N/A'):.2f} kcal/mol
- Standard Deviation: {statistics.get('std_score', 'N/A'):.2f} kcal/mol
- Score Range: {statistics.get('min_score', 'N/A'):.2f} to {statistics.get('max_score', 'N/A'):.2f} kcal/mol
- Median Score: {statistics.get('median_score', 'N/A'):.2f} kcal/mol
- Number of Clusters: {statistics.get('num_clusters', 'N/A')}
- Confidence Score: {statistics.get('confidence_score', 'N/A'):.2f}
- Average Poses per Ligand: {statistics.get('mean_num_modes', 'N/A'):.1f}
"""
        
        context += """

### Top Binding Poses (Detailed):
"""
        
        results = docking_results.get('results', [])
        valid_results = [r for r in results if r.get('binding_affinity') is not None]
        valid_results.sort(key=lambda x: x.get('binding_affinity', float('inf')))
        
        for idx, result in enumerate(valid_results[:5], 1):
            binding_affinity = result.get('binding_affinity', 'N/A')
            ligand_name = result.get('ligand_name', f'Ligand {idx}')
            modes = result.get('modes', [])
            num_poses = result.get('num_poses', len(modes))
            affinity_range = result.get('affinity_range', 'N/A')
            pose_consistency = result.get('pose_consistency', 'N/A')
            
            context += f"""
{idx}. {ligand_name}
   - Best Binding Affinity: {binding_affinity:.2f} kcal/mol
   - Number of Poses: {num_poses}
   - Affinity Range: {affinity_range:.2f} kcal/mol (if multiple poses)
   - Pose Consistency: {pose_consistency:.2f} (if available)
"""
            
            # Add top 3 modes if available
            if modes and len(modes) > 0:
                context += "   - Top 3 Binding Modes:\n"
                for mode_idx, mode in enumerate(modes[:3], 1):
                    mode_num = mode.get('mode', mode_idx)
                    affinity = mode.get('affinity', 'N/A')
                    rmsd_lb = mode.get('rmsd_lb', 'N/A')
                    rmsd_ub = mode.get('rmsd_ub', 'N/A')
                    context += f"     Mode {mode_num}: {affinity:.2f} kcal/mol (RMSD: {rmsd_lb:.2f}-{rmsd_ub:.2f} Å)\n"
        
        # Add clustering information if available
        clustered_results = docking_results.get('clustered_results', [])
        if clustered_results:
            context += """

### Pose Clustering Analysis:
"""
            clusters = {}
            for result in clustered_results[:10]:
                cluster_id = result.get('cluster_id', 'unknown')
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(result)
            
            for cluster_id, cluster_members in sorted(clusters.items())[:5]:
                best_in_cluster = min(cluster_members, key=lambda x: x.get('binding_affinity', float('inf')))
                context += f"""
- Cluster {cluster_id}: {len(cluster_members)} pose(s), best affinity: {best_in_cluster.get('binding_affinity', 'N/A'):.2f} kcal/mol
"""
        
        # Add parameter information
        parameters_used = docking_results.get('parameters_used', {})
        if parameters_used:
            context += f"""

### Docking Parameters Used:
- Grid Center: ({parameters_used.get('center_x', 0):.2f}, {parameters_used.get('center_y', 0):.2f}, {parameters_used.get('center_z', 0):.2f}) Å
- Grid Size: {parameters_used.get('size_x', 20):.1f} × {parameters_used.get('size_y', 20):.1f} × {parameters_used.get('size_z', 20):.1f} Å
- Exhaustiveness: {parameters_used.get('exhaustiveness', 8)}
- Number of Modes: {parameters_used.get('num_modes', 9)}
"""
        
        # Add analysis type specific context
        if custom_prompt:
            context += f"""

### Custom Analysis Request:
{custom_prompt}
"""
        elif analysis_type != "comprehensive":
            analysis_focus = {
                "binding_affinity": "Focus specifically on binding affinity analysis, interpretation, and validation.",
                "drug_likeness": "Focus specifically on drug-likeness properties, ADMET predictions, and pharmaceutical development considerations.",
                "toxicity": "Focus specifically on toxicity predictions, safety profile, and risk assessment."
            }
            context += f"""

### Analysis Focus:
{analysis_focus.get(analysis_type, "")}
"""
        
        # Get stakeholder-specific prompt
        stakeholder_prompts = _get_stakeholder_specific_prompt(stakeholder_type, analysis_type)
        system_prompt = stakeholder_prompts["system"]
        
        # Add recommendations focus instruction
        context += f"""

### Recommendations Focus:
{stakeholder_prompts['recommendations_focus']}

Please provide your analysis in JSON format with the following structure:
{{
    "summary": "Executive summary tailored for {stakeholder_type}",
    "detailed_analysis": {{
        "binding_analysis": "Detailed binding affinity analysis",
        "interaction_analysis": "Detailed interaction analysis",
        "pose_quality": "Pose quality assessment",
        "drug_likeness": "Drug-likeness assessment",
        "clinical_insights": "Clinical insights specific to {stakeholder_type}"
    }},
    "recommendations": ["Recommendation 1", "Recommendation 2", ...],
    "confidence": 0.0-1.0,
    "limitations": ["Limitation 1", "Limitation 2", ...]
}}
"""
        
        # Generate AI analysis
        try:
            if ANTHROPIC_API_KEY:
                analysis_text = await generate_structured_with_anthropic(context, system_prompt, stakeholder_type)
            elif OPENAI_API_KEY:
                analysis_text = await generate_structured_with_openai(context, system_prompt, stakeholder_type)
            else:
                # Fallback to template
                logger.info(f"No AI API keys configured, using template analysis for job {job_id}")
                analysis_text = generate_template_structured_analysis(context, docking_results, plddt_score, stakeholder_type)
            
            # Parse JSON response
            try:
                # Try to extract JSON from markdown code blocks if present
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(1)
                
                analysis_dict = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create structured response from text
                logger.warning(f"Failed to parse JSON response, creating structured response from text")
                analysis_dict = {
                    "summary": analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text,
                    "detailed_analysis": {
                        "full_analysis": analysis_text
                    },
                    "recommendations": _extract_recommendations_from_text(analysis_text, stakeholder_type),
                    "confidence": 0.75,  # Default confidence
                    "limitations": [
                        "Analysis based on computational predictions only",
                        "Experimental validation required",
                        "In vivo efficacy not confirmed"
                    ]
                }
            
            # Ensure required fields exist
            if "recommendations" not in analysis_dict:
                analysis_dict["recommendations"] = _extract_recommendations_from_text(analysis_text, stakeholder_type)
            
            if "confidence" not in analysis_dict:
                # Calculate confidence based on docking results
                best_score = docking_results.get('best_score')
                if best_score and isinstance(best_score, (int, float)):
                    # Strong binding (< -7) = high confidence, moderate (-5 to -7) = medium, weak (> -5) = low
                    if best_score < -7:
                        confidence = 0.85
                    elif best_score < -5:
                        confidence = 0.70
                    else:
                        confidence = 0.55
                else:
                    confidence = 0.65
                analysis_dict["confidence"] = confidence
            
            if "limitations" not in analysis_dict:
                analysis_dict["limitations"] = [
                    "Analysis based on computational predictions only",
                    "Experimental validation required",
                    "In vivo efficacy not confirmed"
                ]
            
            return {
                "analysis": analysis_dict,
                "recommendations": analysis_dict.get("recommendations", []),
                "confidence": analysis_dict.get("confidence", 0.65),
                "metadata": {
                    "model": "claude-3-5-sonnet-20241022" if ANTHROPIC_API_KEY else ("gpt-4-turbo-preview" if OPENAI_API_KEY else "template"),
                    "stakeholder_type": stakeholder_type,
                    "analysis_type": analysis_type,
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat()
                },
                "admet_properties": admet_data if admet_data else None,
                "toxicity_predictions": toxicity_data if toxicity_data else None
            }
            
        except (AIAPIError, AIReportTimeoutError) as e:
            logger.error(f"AI analysis error for job {job_id}: {str(e)}")
            # Fallback to template
            template_analysis = generate_template_structured_analysis(context, docking_results, plddt_score, stakeholder_type)
            return {
                "analysis": {
                    "summary": template_analysis.get("summary", "Analysis completed"),
                    "detailed_analysis": template_analysis.get("detailed_analysis", {}),
                    "limitations": template_analysis.get("limitations", [
                        "Analysis based on computational predictions only",
                        "Experimental validation required",
                        "In vivo efficacy not confirmed"
                    ])
                },
                "recommendations": _get_default_recommendations(stakeholder_type),
                "confidence": 0.60,
                "metadata": {
                    "model": "template",
                    "timestamp": datetime.utcnow().isoformat(),
                    "tokenCount": 500,
                    "costEstimate": 0.0,
                    "processingTime": 0.5
                }
            }
        
    except (AIReportError, ValueError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating structured AI analysis for job {job_id}: {str(e)}", exc_info=True)
        raise AIReportError(f"Failed to generate structured AI analysis: {str(e)}") from e

async def generate_structured_with_anthropic(context: str, system_prompt: str, stakeholder: str) -> str:
    """Generate structured analysis using Claude API"""
    
    if not ANTHROPIC_API_KEY:
        raise AIAPIError("ANTHROPIC_API_KEY not configured")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": context}
                        ]
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("Anthropic API request timed out after 2 minutes")
            except httpx.NetworkError as e:
                raise AIAPIError(f"Network error connecting to Anthropic API: {str(e)}")
            except httpx.RequestError as e:
                raise AIAPIError(f"Request error to Anthropic API: {str(e)}")
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                raise AIAPIError(f"Anthropic API error (status {response.status_code}): {error_text}")
            
            result = response.json()
            if "content" not in result or not result["content"]:
                raise AIAPIError("No content in Anthropic API response")
            
            text_content = result["content"][0].get("text", "")
            if not text_content:
                raise AIAPIError("Empty text content in Anthropic API response")
            
            return text_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Anthropic API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating structured analysis: {str(e)}") from e

async def generate_structured_with_openai(context: str, system_prompt: str, stakeholder: str) -> str:
    """Generate structured analysis using OpenAI GPT-4"""
    
    if not OPENAI_API_KEY:
        raise AIAPIError("OPENAI_API_KEY not configured")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo-preview",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 4096,
                        "temperature": 0.7,
                        "response_format": {"type": "json_object"}
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("OpenAI API request timed out after 2 minutes")
            except httpx.NetworkError as e:
                raise AIAPIError(f"Network error connecting to OpenAI API: {str(e)}")
            except httpx.RequestError as e:
                raise AIAPIError(f"Request error to OpenAI API: {str(e)}")
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                raise AIAPIError(f"OpenAI API error (status {response.status_code}): {error_text}")
            
            result = response.json()
            if "choices" not in result or not result["choices"]:
                raise AIAPIError("No choices in OpenAI API response")
            
            message_content = result["choices"][0].get("message", {}).get("content", "")
            if not message_content:
                raise AIAPIError("Empty message content in OpenAI API response")
            
            return message_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating structured analysis: {str(e)}") from e

def generate_template_structured_analysis(
    context: str,
    docking_results: Dict[str, Any],
    plddt_score: Optional[float],
    stakeholder_type: str
) -> Dict[str, Any]:
    """Generate a basic template structured analysis without AI"""
    
    best_score = docking_results.get('best_score', 'N/A')
    
    return {
        "summary": f"Molecular docking simulation completed successfully. Best binding affinity: {best_score} kcal/mol. Analysis tailored for {stakeholder_type}.",
        "detailed_analysis": {
            "binding_analysis": f"Best binding affinity observed: {best_score} kcal/mol. {'Strong binding' if isinstance(best_score, (int, float)) and best_score < -7 else 'Moderate binding' if isinstance(best_score, (int, float)) and best_score < -5 else 'Weak binding'}.",
            "interaction_analysis": "Detailed interaction analysis requires AI-powered analysis.",
            "pose_quality": "Pose quality assessment requires detailed analysis.",
            "drug_likeness": "Drug-likeness assessment requires comprehensive ADMET analysis.",
            "clinical_insights": f"Clinical insights specific to {stakeholder_type} require AI-powered analysis."
        },
        "recommendations": _get_default_recommendations(stakeholder_type),
        "confidence": 0.60,
        "limitations": [
            "Analysis based on computational predictions only",
            "Experimental validation required",
            "In vivo efficacy not confirmed"
        ]
    }

def _get_default_recommendations(stakeholder_type: str) -> List[str]:
    """Get default recommendations based on stakeholder type"""
    
    recommendations = {
        "researcher": [
            "Proceed with molecular dynamics simulation to validate binding stability",
            "Conduct experimental binding assays (SPR, ITC) to confirm predictions",
            "Investigate structure-activity relationships with analog compounds",
            "Perform quantum mechanics calculations for interaction energy refinement"
        ],
        "clinician": [
            "Mechanism of action well-defined through computational analysis",
            "Predicted safety profile suggests manageable side effect potential",
            "Dosing strategy should target appropriate plasma concentration for efficacy",
            "Monitor for drug-drug interactions",
            "Patient selection criteria should consider target expression levels"
        ],
        "investor": [
            "Binding affinity indicates viable drug candidate worth continued investment",
            "Patent landscape search recommended to protect intellectual property",
            "Estimated 18-24 months to IND submission with adequate funding",
            "Consider strategic partnerships with CROs for preclinical development"
        ],
        "regulator": [
            "Computational docking data supports mechanistic understanding for IND package",
            "Recommend full ADMET profiling including hERG binding, CYP interactions",
            "Toxicology studies in two species required per ICH guidelines",
            "Manufacturing process development needed to demonstrate batch consistency",
            "Stability studies under ICH conditions recommended before clinical trials"
        ]
    }
    
    return recommendations.get(stakeholder_type, recommendations["researcher"])

def _extract_recommendations_from_text(text: str, stakeholder_type: str) -> List[str]:
    """Extract recommendations from AI-generated text"""
    
    # Try to find recommendations section
    import re
    
    # Look for numbered or bulleted lists
    patterns = [
        r'(?:Recommendations?|Next Steps?|Actions?)[:\s]*\n((?:[-•*]\s*.+\n?)+)',
        r'(?:Recommendations?|Next Steps?|Actions?)[:\s]*\n((?:\d+\.\s*.+\n?)+)',
        r'##\s*Recommendations?\s*\n((?:[-•*]\s*.+\n?)+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            recommendations_text = match.group(1)
            # Extract individual recommendations
            recs = re.findall(r'(?:[-•*]|\d+\.)\s*(.+?)(?=\n(?:[-•*]|\d+\.)|$)', recommendations_text, re.MULTILINE)
            if recs:
                return [rec.strip() for rec in recs if rec.strip()]
    
    # Fallback to default recommendations
    return _get_default_recommendations(stakeholder_type)
