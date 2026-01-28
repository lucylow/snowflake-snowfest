import os
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
import httpx
import json
from datetime import datetime
import hashlib
import asyncio
from functools import lru_cache

# Import molecular properties service
try:
    from backend.services.molecular_properties import (
        calculate_molecular_properties,
        RDKitNotAvailableError,
        MolecularPropertyError
    )
except ImportError:
    logger.warning("Molecular properties service not available")
    RDKitNotAvailableError = Exception
    MolecularPropertyError = Exception
    calculate_molecular_properties = None

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

# Cache for AI analysis results (in-memory, can be replaced with Redis in production)
_analysis_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0  # seconds

# Cost tracking (approximate costs per 1K tokens)
# Prices as of 2025 - update as needed
COST_PER_1K_TOKENS = {
    "openai": {
        "gpt-4o": {"input": 0.0025, "output": 0.010},  # $2.50/$10 per 1M tokens
    },
    "anthropic": {
        "claude-3-7-sonnet-20250219": {"input": 0.003, "output": 0.015},  # $3/$15 per 1M tokens
    }
}

# Track API usage
_api_usage_stats: Dict[str, Dict[str, Any]] = {}

# Conversation history storage (in-memory, can be replaced with Redis in production)
_conversation_history: Dict[str, List[Dict[str, str]]] = {}

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
        ml_predictions_context = await _add_ml_predictions_context(docking_results, valid_results)
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

def _get_cache_key(context: str, stakeholder: str, analysis_type: str = "report") -> str:
    """Generate cache key from context and parameters"""
    key_string = f"{analysis_type}:{stakeholder}:{context}"
    return hashlib.sha256(key_string.encode()).hexdigest()

def _get_cached_analysis(cache_key: str) -> Optional[str]:
    """Get cached analysis if available and not expired"""
    if cache_key not in _analysis_cache:
        return None
    
    cached_data = _analysis_cache[cache_key]
    timestamp = cached_data.get("timestamp", 0)
    age_seconds = (datetime.now().timestamp() - timestamp)
    
    if age_seconds > CACHE_TTL_SECONDS:
        del _analysis_cache[cache_key]
        return None
    
    return cached_data.get("result")

def _cache_analysis(cache_key: str, result: str):
    """Cache analysis result"""
    _analysis_cache[cache_key] = {
        "result": result,
        "timestamp": datetime.now().timestamp()
    }
    # Limit cache size (keep last 100 entries)
    if len(_analysis_cache) > 100:
        oldest_key = min(_analysis_cache.keys(), key=lambda k: _analysis_cache[k]["timestamp"])
        del _analysis_cache[oldest_key]

def _track_api_usage(provider: str, model: str, input_tokens: int, output_tokens: int):
    """Track API usage and calculate costs"""
    if provider not in _api_usage_stats:
        _api_usage_stats[provider] = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0
        }
    
    stats = _api_usage_stats[provider]
    stats["total_requests"] += 1
    stats["total_input_tokens"] += input_tokens
    stats["total_output_tokens"] += output_tokens
    
    # Calculate cost
    costs = COST_PER_1K_TOKENS.get(provider, {}).get(model, {})
    input_cost = (input_tokens / 1000) * costs.get("input", 0)
    output_cost = (output_tokens / 1000) * costs.get("output", 0)
    total_cost = input_cost + output_cost
    
    stats["total_cost"] += total_cost
    
    logger.info(
        f"API usage - Provider: {provider}, Model: {model}, "
        f"Input tokens: {input_tokens}, Output tokens: {output_tokens}, "
        f"Cost: ${total_cost:.4f}"
    )

def get_api_usage_stats() -> Dict[str, Dict[str, Any]]:
    """Get API usage statistics"""
    return _api_usage_stats.copy()

async def _retry_with_backoff(func, *args, **kwargs):
    """Retry function with exponential backoff"""
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except (AIAPIError, AIReportTimeoutError) as e:
            last_exception = e
            if attempt == MAX_RETRIES - 1:
                raise
            
            # Exponential backoff with jitter
            delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
            await asyncio.sleep(delay)
            logger.info(f"Retrying AI API call (attempt {attempt + 1}/{MAX_RETRIES}) after {delay}s delay")
        except Exception as e:
            # Don't retry on non-retryable errors
            raise
    
    if last_exception:
        raise last_exception

async def generate_with_anthropic(context: str, stakeholder: str) -> str:
    """Generate report using Claude API with retry logic and caching"""
    
    if not ANTHROPIC_API_KEY:
        raise AIAPIError("ANTHROPIC_API_KEY not configured")
    
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for AI report generation")
    
    # Check cache
    cache_key = _get_cache_key(context, stakeholder, "report")
    cached_result = _get_cached_analysis(cache_key)
    if cached_result:
        logger.info("Returning cached AI analysis result")
        return cached_result
    
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
    
    async def _make_request():
        async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout to 3 minutes
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-7-sonnet-20250219",  # Updated to latest Claude model
                        "max_tokens": 4096,  # Increased for more comprehensive analysis
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": context}
                        ],
                        "temperature": 0.3  # Lower temperature for more consistent, factual responses
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("Anthropic API request timed out after 3 minutes")
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
    
    try:
        text_content = await _retry_with_backoff(_make_request)
        # Cache the result
        _cache_analysis(cache_key, text_content)
        return text_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Anthropic API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating AI report: {str(e)}") from e

async def generate_with_openai(context: str, stakeholder: str) -> str:
    """Generate report using OpenAI GPT-4 with retry logic and caching"""
    
    if not OPENAI_API_KEY:
        raise AIAPIError("OPENAI_API_KEY not configured")
    
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for AI report generation")
    
    # Check cache
    cache_key = _get_cache_key(context, stakeholder, "report")
    cached_result = _get_cached_analysis(cache_key)
    if cached_result:
        logger.info("Returning cached AI analysis result")
        return cached_result
    
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
    
    async def _make_request():
        async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout to 3 minutes
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",  # Updated to latest GPT-4o model
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 4096,  # Increased for more comprehensive analysis
                        "temperature": 0.3  # Lower temperature for more consistent, factual responses
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("OpenAI API request timed out after 3 minutes")
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
    
    try:
        message_content = await _retry_with_backoff(_make_request)
        # Cache the result
        _cache_analysis(cache_key, message_content)
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

Use technical language appropriate for researchers. Cite specific metrics, provide quantitative assessments, and include detailed methodology recommendations.

**Example Analysis Format:**
{
    "summary": "The docking analysis reveals Ligand A (binding affinity: -8.7 kcal/mol) as the top candidate with strong binding interactions. Statistical analysis shows mean affinity of -7.2 ± 1.3 kcal/mol across 15 ligands, with 8 poses clustering within 1.2 Å RMSD, indicating high confidence.",
    "detailed_analysis": {
        "binding_analysis": "Ligand A demonstrates exceptional binding affinity (-8.7 kcal/mol), corresponding to predicted Ki ≈ 420 nM. The binding mode shows 6 hydrogen bonds with key residues (Asp123, Lys456, Ser789) and optimal shape complementarity (SAS = 0.92).",
        "interaction_analysis": "Critical interactions include: (1) π-π stacking with Phe234 (distance: 3.8 Å), (2) Salt bridge with Lys456 (distance: 2.9 Å), (3) Hydrophobic pocket occupancy (85% volume).",
        "pose_quality": "Pose clustering analysis reveals 8/10 poses within 1.2 Å RMSD, indicating high reproducibility. The binding mode is consistent across multiple docking runs.",
        "drug_likeness": "Ligand A satisfies Lipinski's Rule of Five (MW: 412 Da, LogP: 3.1, HBD: 2, HBA: 6). QED score: 0.68, suggesting good drug-likeness. Synthetic accessibility score: 4.2/10 (moderately accessible).",
        "clinical_insights": "The strong binding affinity suggests potential for nanomolar IC50 in cellular assays. Recommended next steps: (1) SPR binding assay to validate Ki prediction, (2) 100 ns MD simulation to assess binding stability, (3) Analog synthesis focusing on improving LogP while maintaining H-bond network."
    },
    "recommendations": [
        "Perform SPR binding assay to validate predicted Ki of 420 nM",
        "Run 100 ns molecular dynamics simulation to assess binding stability",
        "Synthesize 5-10 analogs with modified LogP (target: 2.5-3.5) while preserving key H-bonds",
        "Conduct FEP calculations for top 3 analogs to predict affinity improvements"
    ],
    "confidence": 0.87,
    "limitations": [
        "Docking scores are approximations; experimental validation required",
        "MD simulations needed to confirm binding stability",
        "ADMET predictions are computational estimates"
    ]
}""",
            
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

Use clear, clinically-focused language. Translate technical metrics into clinical implications. Focus on patient safety and therapeutic efficacy.

**Example Clinical Translation:**
Binding affinity of -8.7 kcal/mol translates to predicted IC50 ≈ 420 nM, suggesting therapeutic potential at achievable plasma concentrations. For a typical oral dosing regimen targeting 10-50 nM free plasma concentration, this compound would require BID or TID dosing. The predicted CYP3A4 inhibition risk (moderate) suggests monitoring for drug-drug interactions with statins, calcium channel blockers, and immunosuppressants.""",
            
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
                    "model": "claude-3-7-sonnet-20250219" if ANTHROPIC_API_KEY else ("gpt-4o" if OPENAI_API_KEY else "template"),
                    "stakeholder_type": stakeholder_type,
                    "analysis_type": analysis_type,
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat(),
                    "api_usage": _api_usage_stats.get("anthropic" if ANTHROPIC_API_KEY else ("openai" if OPENAI_API_KEY else None), {})
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
    """Generate structured analysis using Claude API with retry logic and caching"""
    
    if not ANTHROPIC_API_KEY:
        raise AIAPIError("ANTHROPIC_API_KEY not configured")
    
    # Check cache
    cache_key = _get_cache_key(context, stakeholder, "structured")
    cached_result = _get_cached_analysis(cache_key)
    if cached_result:
        logger.info("Returning cached structured AI analysis result")
        return cached_result
    
    async def _make_request():
        async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout to 3 minutes
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-7-sonnet-20250219",  # Updated to latest Claude model
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": context}
                        ],
                        "temperature": 0.3  # Lower temperature for more consistent, factual responses
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("Anthropic API request timed out after 3 minutes")
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
            
            # Track usage and cost
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            _track_api_usage("anthropic", "claude-3-7-sonnet-20250219", input_tokens, output_tokens)
            
            return text_content
    
    try:
        text_content = await _retry_with_backoff(_make_request)
        # Cache the result
        _cache_analysis(cache_key, text_content)
        return text_content
    except (AIAPIError, AIReportTimeoutError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Anthropic API: {str(e)}", exc_info=True)
        raise AIAPIError(f"Unexpected error generating structured analysis: {str(e)}") from e

async def generate_structured_with_openai(context: str, system_prompt: str, stakeholder: str) -> str:
    """Generate structured analysis using OpenAI GPT-4 with retry logic and caching"""
    
    if not OPENAI_API_KEY:
        raise AIAPIError("OPENAI_API_KEY not configured")
    
    # Check cache
    cache_key = _get_cache_key(context, stakeholder, "structured")
    cached_result = _get_cached_analysis(cache_key)
    if cached_result:
        logger.info("Returning cached structured AI analysis result")
        return cached_result
    
    async def _make_request():
        async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout to 3 minutes
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",  # Updated to latest GPT-4o model
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 4096,
                        "temperature": 0.3,  # Lower temperature for more consistent, factual responses
                        "response_format": {"type": "json_object"}
                    }
                )
            except httpx.TimeoutException:
                raise AIReportTimeoutError("OpenAI API request timed out after 3 minutes")
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
            
            # Track usage and cost
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            _track_api_usage("openai", "gpt-4o", prompt_tokens, completion_tokens)
            
            return message_content
    
    try:
        message_content = await _retry_with_backoff(_make_request)
        # Cache the result
        _cache_analysis(cache_key, message_content)
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

async def _add_ml_predictions_context(docking_results: Dict[str, Any], valid_results: List[Dict[str, Any]]) -> str:
    """
    Add ML-powered molecular property predictions context to the analysis prompt.
    
    Args:
        docking_results: Docking results dictionary
        valid_results: List of valid docking results
        
    Returns:
        Formatted context string with ML predictions
    """
    if not calculate_molecular_properties:
        return ""
    
    context = ""
    ligand_files = docking_results.get('ligand_files', [])
    
    if not ligand_files or not valid_results:
        return context
    
    # Analyze top 3 ligands
    top_ligands = valid_results[:3]
    ml_summaries = []
    
    for idx, result in enumerate(top_ligands):
        ligand_idx = result.get('ligand_index', idx)
        if ligand_idx >= len(ligand_files):
            continue
        
        try:
            ligand_sdf = ligand_files[ligand_idx]
            ligand_name = result.get('ligand_name', f'ligand_{ligand_idx}')
            
            properties = calculate_molecular_properties(ligand_sdf, ligand_name)
            
            # Extract key properties
            mol_props = properties.get('molecular_properties', {})
            admet = properties.get('admet', {})
            toxicity = properties.get('toxicity', {})
            
            summary = f"\n### ML Predictions for {ligand_name}:\n"
            
            # Drug-likeness
            drug_likeness = mol_props.get('drug_likeness_score', {})
            if drug_likeness:
                score = drug_likeness.get('overall_score', 0)
                summary += f"- Drug-likeness Score: {score:.2f}/1.0\n"
            
            # Key ADMET properties
            if admet.get('absorption'):
                gi_abs = admet['absorption'].get('gi_absorption', {})
                if gi_abs:
                    summary += f"- GI Absorption: {gi_abs.get('prediction', 'Unknown')}\n"
            
            if admet.get('distribution'):
                bbb = admet['distribution'].get('bbb_permeability', {})
                if bbb:
                    summary += f"- BBB Permeability: {bbb.get('prediction', 'Unknown')}\n"
            
            # Toxicity
            if toxicity.get('overall_toxicity_risk'):
                risk = toxicity['overall_toxicity_risk'].get('level', 'Unknown')
                summary += f"- Toxicity Risk: {risk}\n"
            
            ml_summaries.append(summary)
            
        except (RDKitNotAvailableError, MolecularPropertyError) as e:
            logger.debug(f"ML predictions unavailable for ligand {ligand_idx}: {str(e)}")
            continue
        except Exception as e:
            logger.warning(f"Error calculating ML properties for ligand {ligand_idx}: {str(e)}")
            continue
    
    if ml_summaries:
        context += "\n## ML-Powered Molecular Property Predictions:\n"
        context += "".join(ml_summaries)
    
    return context

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

# ============================================================================
# STREAMING SUPPORT
# ============================================================================

async def generate_ai_analysis_stream(
    job_id: str,
    sequence: Optional[str],
    plddt_score: Optional[float],
    docking_results: Dict[str, Any],
    analysis_type: str = "comprehensive",
    custom_prompt: Optional[str] = None,
    stakeholder_type: str = "researcher"
) -> AsyncGenerator[str, None]:
    """
    Generate AI analysis with streaming support for real-time updates
    
    Args:
        job_id: Unique job identifier
        sequence: Protein sequence (if AlphaFold was used)
        plddt_score: AlphaFold confidence score
        docking_results: Docking simulation results
        analysis_type: Type of analysis
        custom_prompt: Custom prompt for analysis
        stakeholder_type: Target audience
        
    Yields:
        Chunks of analysis text as they are generated
    """
    # Build context (same as generate_structured_ai_analysis)
    context = _build_analysis_context(job_id, sequence, plddt_score, docking_results, analysis_type, custom_prompt)
    
    # Get stakeholder-specific prompt
    stakeholder_prompts = _get_stakeholder_specific_prompt(stakeholder_type, analysis_type)
    system_prompt = stakeholder_prompts["system"]
    
    # Add JSON format instruction
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
    
    # Stream from preferred provider
    try:
        if ANTHROPIC_API_KEY:
            async for chunk in _stream_with_anthropic(context, system_prompt):
                yield chunk
        elif OPENAI_API_KEY:
            async for chunk in _stream_with_openai(context, system_prompt):
                yield chunk
        else:
            # Fallback to non-streaming
            template_result = generate_template_structured_analysis(
                context, docking_results, plddt_score, stakeholder_type
            )
            yield json.dumps(template_result)
    except Exception as e:
        logger.error(f"Error in streaming analysis: {str(e)}", exc_info=True)
        yield json.dumps({"error": f"Streaming failed: {str(e)}"})

async def _stream_with_anthropic(context: str, system_prompt: str) -> AsyncGenerator[str, None]:
    """Stream analysis using Anthropic Claude API"""
    if not ANTHROPIC_API_KEY:
        raise AIAPIError("ANTHROPIC_API_KEY not configured")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-7-sonnet-20250219",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": context}],
                    "temperature": 0.3,
                    "stream": True
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise AIAPIError(f"Anthropic API error (status {response.status_code}): {error_text.decode()[:500]}")
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data)
                            if "delta" in chunk_data and "text" in chunk_data["delta"]:
                                yield chunk_data["delta"]["text"]
                        except json.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            raise AIReportTimeoutError("Anthropic API request timed out")
        except Exception as e:
            raise AIAPIError(f"Error streaming from Anthropic: {str(e)}")

async def _stream_with_openai(context: str, system_prompt: str) -> AsyncGenerator[str, None]:
    """Stream analysis using OpenAI GPT-4 API"""
    if not OPENAI_API_KEY:
        raise AIAPIError("OPENAI_API_KEY not configured")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context}
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.3,
                    "stream": True,
                    "response_format": {"type": "json_object"}
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise AIAPIError(f"OpenAI API error (status {response.status_code}): {error_text.decode()[:500]}")
                
                async for line in response.aiter_lines():
                    if not line.strip() or not line.startswith("data: "):
                        continue
                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data)
                        if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise AIReportTimeoutError("OpenAI API request timed out")
        except Exception as e:
            raise AIAPIError(f"Error streaming from OpenAI: {str(e)}")

# ============================================================================
# CONVERSATION INTERFACE
# ============================================================================

def get_conversation_history(job_id: str) -> List[Dict[str, str]]:
    """Get conversation history for a job"""
    return _conversation_history.get(job_id, [])

def add_to_conversation_history(job_id: str, role: str, content: str):
    """Add a message to conversation history"""
    if job_id not in _conversation_history:
        _conversation_history[job_id] = []
    _conversation_history[job_id].append({"role": role, "content": content})
    # Limit history to last 20 messages
    if len(_conversation_history[job_id]) > 20:
        _conversation_history[job_id] = _conversation_history[job_id][-20:]

async def generate_followup_response(
    job_id: str,
    question: str,
    docking_results: Dict[str, Any],
    stakeholder_type: str = "researcher"
) -> Dict[str, Any]:
    """
    Generate a follow-up response to a question about the docking results
    
    Args:
        job_id: Unique job identifier
        question: User's follow-up question
        docking_results: Docking simulation results
        stakeholder_type: Target audience
        
    Returns:
        Response dictionary with answer and metadata
    """
    if not question or not question.strip():
        raise ValueError("Question is required")
    
    # Get conversation history
    history = get_conversation_history(job_id)
    
    # Build context with conversation history
    context = f"""
# Follow-up Question about Docking Results
Job ID: {job_id}

## Previous Context:
{json.dumps(docking_results.get('summary', {}), indent=2)}

## Conversation History:
"""
    for msg in history[-5:]:  # Last 5 messages for context
        context += f"\n{msg['role'].upper()}: {msg['content']}\n"
    
    context += f"""
## Current Question:
{question}

Please provide a detailed, context-aware answer to this question based on the docking results and previous conversation.
"""
    
    system_prompt = f"""You are an expert computational chemist helping a {stakeholder_type} understand molecular docking results.
Answer the follow-up question based on the provided context and conversation history. Be specific, cite metrics, and provide actionable insights."""
    
    try:
        if ANTHROPIC_API_KEY:
            answer = await generate_with_anthropic(context, stakeholder_type)
        elif OPENAI_API_KEY:
            answer = await generate_with_openai(context, stakeholder_type)
        else:
            answer = "Follow-up questions require AI API keys to be configured."
        
        # Add to conversation history
        add_to_conversation_history(job_id, "user", question)
        add_to_conversation_history(job_id, "assistant", answer)
        
        return {
            "answer": answer,
            "metadata": {
                "model": "claude-3-7-sonnet-20250219" if ANTHROPIC_API_KEY else ("gpt-4o" if OPENAI_API_KEY else "template"),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating follow-up response: {str(e)}", exc_info=True)
        raise AIReportError(f"Failed to generate follow-up response: {str(e)}")

# ============================================================================
# MULTI-MODEL ENSEMBLE
# ============================================================================

async def generate_ensemble_analysis(
    job_id: str,
    sequence: Optional[str],
    plddt_score: Optional[float],
    docking_results: Dict[str, Any],
    analysis_type: str = "comprehensive",
    stakeholder_type: str = "researcher"
) -> Dict[str, Any]:
    """
    Generate analysis using multiple AI models and combine insights
    
    Args:
        job_id: Unique job identifier
        sequence: Protein sequence
        plddt_score: AlphaFold confidence score
        docking_results: Docking simulation results
        analysis_type: Type of analysis
        stakeholder_type: Target audience
        
    Returns:
        Combined analysis with insights from multiple models
    """
    context = _build_analysis_context(job_id, sequence, plddt_score, docking_results, analysis_type, None)
    stakeholder_prompts = _get_stakeholder_specific_prompt(stakeholder_type, analysis_type)
    system_prompt = stakeholder_prompts["system"]
    
    results = []
    
    # Generate with Anthropic if available
    if ANTHROPIC_API_KEY:
        try:
            anthropic_result = await generate_structured_with_anthropic(context, system_prompt, stakeholder_type)
            results.append({
                "provider": "anthropic",
                "model": "claude-3-7-sonnet-20250219",
                "analysis": anthropic_result
            })
        except Exception as e:
            logger.warning(f"Anthropic ensemble analysis failed: {str(e)}")
    
    # Generate with OpenAI if available
    if OPENAI_API_KEY:
        try:
            openai_result = await generate_structured_with_openai(context, system_prompt, stakeholder_type)
            results.append({
                "provider": "openai",
                "model": "gpt-4o",
                "analysis": openai_result
            })
        except Exception as e:
            logger.warning(f"OpenAI ensemble analysis failed: {str(e)}")
    
    if not results:
        # Fallback to template
        template_result = generate_template_structured_analysis(context, docking_results, plddt_score, stakeholder_type)
        return {
            "analysis": template_result,
            "ensemble": False,
            "models_used": []
        }
    
    # Combine results
    combined_analysis = _combine_ensemble_results(results, stakeholder_type)
    
    return {
        "analysis": combined_analysis,
        "ensemble": len(results) > 1,
        "models_used": [r["provider"] for r in results],
        "individual_results": results
    }

def _combine_ensemble_results(results: List[Dict[str, Any]], stakeholder_type: str) -> Dict[str, Any]:
    """Combine results from multiple models"""
    if len(results) == 1:
        # Single result, parse and return
        try:
            analysis_text = results[0]["analysis"]
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', analysis_text, re.DOTALL)
            if json_match:
                analysis_text = json_match.group(1)
            return json.loads(analysis_text)
        except:
            return {"summary": analysis_text, "detailed_analysis": {}, "recommendations": []}
    
    # Multiple results - combine intelligently
    summaries = []
    all_recommendations = []
    detailed_analyses = []
    
    for result in results:
        try:
            analysis_text = result["analysis"]
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', analysis_text, re.DOTALL)
            if json_match:
                analysis_text = json_match.group(1)
            parsed = json.loads(analysis_text)
            summaries.append(parsed.get("summary", ""))
            all_recommendations.extend(parsed.get("recommendations", []))
            detailed_analyses.append(parsed.get("detailed_analysis", {}))
        except:
            summaries.append(analysis_text[:200] if isinstance(analysis_text, str) else "")
    
    # Combine summaries
    combined_summary = f"Ensemble analysis combining insights from {len(results)} AI models:\n\n"
    for i, summary in enumerate(summaries, 1):
        combined_summary += f"Model {i}: {summary[:300]}...\n\n"
    
    # Deduplicate and prioritize recommendations
    unique_recommendations = []
    seen = set()
    for rec in all_recommendations:
        rec_lower = rec.lower().strip()
        if rec_lower not in seen:
            seen.add(rec_lower)
            unique_recommendations.append(rec)
    
    # Average confidence if available
    confidences = []
    for result in results:
        try:
            analysis_text = result["analysis"]
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', analysis_text, re.DOTALL)
            if json_match:
                analysis_text = json_match.group(1)
            parsed = json.loads(analysis_text)
            if "confidence" in parsed:
                confidences.append(parsed["confidence"])
        except:
            pass
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.75
    
    return {
        "summary": combined_summary,
        "detailed_analysis": {
            "ensemble_insights": "This analysis combines insights from multiple AI models for enhanced reliability and comprehensive coverage.",
            "model_agreement": f"{len(results)} models analyzed the docking results",
            "consensus_recommendations": unique_recommendations[:10]  # Top 10 unique recommendations
        },
        "recommendations": unique_recommendations[:10],
        "confidence": avg_confidence,
        "limitations": [
            "Ensemble analysis combines multiple models but may have varying perspectives",
            "Analysis based on computational predictions only",
            "Experimental validation required"
        ]
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_analysis_context(
    job_id: str,
    sequence: Optional[str],
    plddt_score: Optional[float],
    docking_results: Dict[str, Any],
    analysis_type: str,
    custom_prompt: Optional[str]
) -> str:
    """Build analysis context string (extracted for reuse)"""
    context = f"""
# Protein-Ligand Docking Analysis Report
Job ID: {job_id}

## Protein Information
"""
    
    if sequence:
        if plddt_score is None:
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
    
    return context
