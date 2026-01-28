"""
External API routes.
Provides endpoints for proxying requests to external APIs.
"""
from fastapi import APIRouter, HTTPException, Query, Body, Header
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.services.external_api import (
    proxy_external_api,
    ExternalAPIError,
    ExternalAPITimeoutError,
    ExternalAPIRateLimitError,
    ExternalAPIAuthError,
    get_pubchem_client,
    get_chembl_client,
    get_uniprot_client,
    get_pdb_client,
)
from backend.exceptions import ServiceError

router = APIRouter()


class ExternalAPIRequest(BaseModel):
    """Request model for external API proxy"""
    api_name: str = Field(..., description="Name/identifier of the external API")
    endpoint: str = Field(..., description="API endpoint path (relative to base URL)")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE)")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    json_data: Optional[Dict[str, Any]] = Field(default=None, description="JSON body data")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")
    api_key: Optional[str] = Field(default=None, description="API key (optional, can use config)")
    base_url: Optional[str] = Field(default=None, description="Base URL (optional, can use config)")


@router.post("/external/proxy")
async def proxy_api(request: ExternalAPIRequest):
    """
    Proxy request to external API.
    
    This endpoint allows you to make requests to external APIs through the backend,
    which handles authentication, rate limiting, and error handling.
    """
    try:
        result = await proxy_external_api(
            api_name=request.api_name,
            endpoint=request.endpoint,
            method=request.method,
            params=request.params,
            json_data=request.json_data,
            headers=request.headers,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return {
            "success": True,
            "data": result,
        }
    except ExternalAPIAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ExternalAPIRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ExternalAPITimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/external/pubchem/{endpoint:path}")
async def pubchem_proxy(
    endpoint: str,
    params: Optional[Dict[str, Any]] = Query(None),
):
    """
    Proxy request to PubChem API.
    
    Example: /api/external/pubchem/compound/name/aspirin/property/MolecularWeight,CanonicalSMILES/JSON
    """
    try:
        client = get_pubchem_client()
        if not client:
            raise HTTPException(status_code=503, detail="PubChem API client not available")
        
        result = await client.get(endpoint, params=params)
        return {
            "success": True,
            "data": result,
        }
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/external/chembl/{endpoint:path}")
async def chembl_proxy(
    endpoint: str,
    params: Optional[Dict[str, Any]] = Query(None),
):
    """
    Proxy request to ChEMBL API.
    
    Example: /api/external/chembl/molecule/CHEMBL25
    """
    try:
        client = get_chembl_client()
        if not client:
            raise HTTPException(status_code=503, detail="ChEMBL API client not available")
        
        result = await client.get(endpoint, params=params)
        return {
            "success": True,
            "data": result,
        }
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/external/uniprot/{endpoint:path}")
async def uniprot_proxy(
    endpoint: str,
    params: Optional[Dict[str, Any]] = Query(None),
):
    """
    Proxy request to UniProt API.
    
    Example: /api/external/uniprot/uniprotkb/P04637
    """
    try:
        client = get_uniprot_client()
        if not client:
            raise HTTPException(status_code=503, detail="UniProt API client not available")
        
        result = await client.get(endpoint, params=params)
        return {
            "success": True,
            "data": result,
        }
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/external/pdb/{endpoint:path}")
async def pdb_proxy(
    endpoint: str,
    params: Optional[Dict[str, Any]] = Query(None),
):
    """
    Proxy request to PDB API.
    
    Example: /api/external/pdb/core/entry/1ABC
    """
    try:
        client = get_pdb_client()
        if not client:
            raise HTTPException(status_code=503, detail="PDB API client not available")
        
        result = await client.get(endpoint, params=params)
        return {
            "success": True,
            "data": result,
        }
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/external/apis")
async def list_available_apis():
    """
    List available external API integrations.
    """
    return {
        "available_apis": [
            {
                "name": "pubchem",
                "description": "PubChem - Chemical compound database",
                "base_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
                "endpoints": [
                    "/compound/name/{name}/property/{properties}/JSON",
                    "/compound/cid/{cid}/property/{properties}/JSON",
                    "/compound/smiles/{smiles}/property/{properties}/JSON",
                ],
            },
            {
                "name": "chembl",
                "description": "ChEMBL - Bioactive molecule database",
                "base_url": "https://www.ebi.ac.uk/chembl/api/data",
                "endpoints": [
                    "/molecule/{chembl_id}",
                    "/molecule?pref_name__icontains={name}",
                    "/activity?molecule_chembl_id={chembl_id}",
                ],
            },
            {
                "name": "uniprot",
                "description": "UniProt - Protein sequence and function database",
                "base_url": "https://rest.uniprot.org",
                "endpoints": [
                    "/uniprotkb/{accession}",
                    "/uniprotkb/search?query={query}",
                    "/uniparc/{upi}",
                ],
            },
            {
                "name": "pdb",
                "description": "Protein Data Bank - 3D structure database",
                "base_url": "https://data.rcsb.org/rest/v1",
                "endpoints": [
                    "/core/entry/{pdb_id}",
                    "/core/entry/{pdb_id}/polymer_entities",
                    "/core/entry/{pdb_id}/nonpolymer_entities",
                ],
            },
        ],
    }
