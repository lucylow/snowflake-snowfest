import os
import logging
from typing import Dict, Any, Optional
import httpx

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
    
    ## Docking Results
    - Total Ligands Tested: {docking_results.get('total_ligands', 0)}
    - Best Binding Affinity: {docking_results.get('best_score', 'N/A')} kcal/mol
    - Best Ligand: {docking_results.get('best_ligand', 'N/A')}
    
    ### Top 3 Binding Poses:
    """
        
        results = docking_results.get('results', [])
        for idx, result in enumerate(results[:3], 1):
            binding_affinity = result.get('binding_affinity', 'N/A')
            ligand_name = result.get('ligand_name', f'Ligand {idx}')
            modes = result.get('modes', [])
            context += f"""
    {idx}. {ligand_name}
       - Binding Affinity: {binding_affinity} kcal/mol
       - Number of Poses: {len(modes)}
    """
        
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
    
    system_prompt = f"""You are an expert computational chemist and drug discovery scientist.
    Analyze the following protein-ligand docking results and provide a comprehensive report 
    tailored for a {stakeholder}.
    
    Include:
    1. Executive Summary
    2. Structural Quality Assessment (if AlphaFold was used)
    3. Binding Affinity Analysis
    4. Drug-likeness Considerations
    5. Recommendations for Next Steps
    
    Use clear, professional language and cite relevant metrics."""
    
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
    
    system_prompt = f"""You are an expert computational chemist and drug discovery scientist.
    Analyze the following protein-ligand docking results and provide a comprehensive report 
    tailored for a {stakeholder}."""
    
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
