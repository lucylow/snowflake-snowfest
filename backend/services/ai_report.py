import os
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

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
    """
    
    # Build context for AI
    context = f"""
    # Protein-Ligand Docking Analysis Report
    Job ID: {job_id}
    
    ## Protein Information
    """
    
    if sequence:
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
    
    for idx, result in enumerate(docking_results.get('results', [])[:3], 1):
        context += f"""
    {idx}. {result['ligand_name']}
       - Binding Affinity: {result['binding_affinity']} kcal/mol
       - Number of Poses: {len(result.get('modes', []))}
    """
    
    # Generate AI analysis
    if ANTHROPIC_API_KEY:
        report = await generate_with_anthropic(context, stakeholder)
    elif OPENAI_API_KEY:
        report = await generate_with_openai(context, stakeholder)
    else:
        # Fallback to template-based report
        report = generate_template_report(context, docking_results, plddt_score)
    
    return report

async def generate_with_anthropic(context: str, stakeholder: str) -> str:
    """Generate report using Claude API"""
    
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
    
    async with httpx.AsyncClient(timeout=60.0) as client:
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
        
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.text}")
            raise RuntimeError("Failed to generate AI report")
        
        result = response.json()
        return result["content"][0]["text"]

async def generate_with_openai(context: str, stakeholder: str) -> str:
    """Generate report using OpenAI GPT-4"""
    
    system_prompt = f"""You are an expert computational chemist and drug discovery scientist.
    Analyze the following protein-ligand docking results and provide a comprehensive report 
    tailored for a {stakeholder}."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
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
        
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.text}")
            raise RuntimeError("Failed to generate AI report")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

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
