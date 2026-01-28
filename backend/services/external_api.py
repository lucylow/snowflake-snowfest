"""
External API integration service.
Provides a unified interface for calling external APIs with proper error handling,
rate limiting, and caching.
"""
import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

import httpx
from backend.config import settings
from backend.exceptions import ServiceError

logger = logging.getLogger(__name__)


class ExternalAPIError(ServiceError):
    """Base exception for external API errors"""
    pass


class ExternalAPITimeoutError(ExternalAPIError):
    """External API request timed out"""
    pass


class ExternalAPIRateLimitError(ExternalAPIError):
    """External API rate limit exceeded"""
    pass


class ExternalAPIAuthError(ExternalAPIError):
    """External API authentication failed"""
    pass


class HTTPMethod(str, Enum):
    """HTTP methods supported"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ExternalAPIClient:
    """
    Generic client for calling external APIs.
    Handles authentication, rate limiting, retries, and error handling.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        api_key_header: str = "Authorization",
        api_key_prefix: str = "Bearer",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize external API client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            api_key_header: Header name for API key
            api_key_prefix: Prefix for API key (e.g., "Bearer", "ApiKey")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.api_key_prefix = api_key_prefix
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers for API request"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if custom_headers:
            headers.update(custom_headers)
        
        if self.api_key:
            if self.api_key_header.lower() == "authorization":
                headers[self.api_key_header] = f"{self.api_key_prefix} {self.api_key}"
            else:
                headers[self.api_key_header] = self.api_key
        
        return headers
    
    async def _make_request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to external API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            data: Raw body data
            headers: Custom headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response data as dictionary
            
        Raises:
            ExternalAPIError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self._get_headers(headers)
        request_timeout = timeout or self.timeout
        
        # Remove Content-Type for form data
        if data and not json_data:
            request_headers.pop("Content-Type", None)
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    request_kwargs = {
                        "url": url,
                        "headers": request_headers,
                        "params": params,
                    }
                    
                    if json_data:
                        request_kwargs["json"] = json_data
                    elif data:
                        request_kwargs["data"] = data
                    
                    response = await client.request(method.value, **request_kwargs)
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After", str(self.retry_delay))
                        try:
                            retry_after = float(retry_after)
                        except ValueError:
                            retry_after = self.retry_delay
                        
                        if attempt < self.max_retries:
                            logger.warning(
                                f"Rate limited, retrying after {retry_after}s "
                                f"(attempt {attempt + 1}/{self.max_retries + 1})"
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise ExternalAPIRateLimitError(
                                f"Rate limit exceeded after {self.max_retries + 1} attempts"
                            )
                    
                    # Handle authentication errors
                    if response.status_code == 401:
                        raise ExternalAPIAuthError("Authentication failed - invalid API key")
                    
                    # Handle server errors with retry
                    if response.status_code >= 500 and attempt < self.max_retries:
                        logger.warning(
                            f"Server error {response.status_code}, retrying "
                            f"(attempt {attempt + 1}/{self.max_retries + 1})"
                        )
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    
                    # Handle client errors
                    if response.status_code >= 400:
                        error_text = response.text[:500] if response.text else "Unknown error"
                        raise ExternalAPIError(
                            f"API request failed with status {response.status_code}: {error_text}"
                        )
                    
                    # Parse response
                    try:
                        return response.json()
                    except ValueError:
                        # Return text if not JSON
                        return {"text": response.text, "status_code": response.status_code}
                    
            except httpx.TimeoutException as e:
                last_error = ExternalAPITimeoutError(f"Request timed out after {request_timeout}s")
                if attempt < self.max_retries:
                    logger.warning(f"Request timeout, retrying (attempt {attempt + 1}/{self.max_retries + 1})")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
                
            except httpx.NetworkError as e:
                last_error = ExternalAPIError(f"Network error: {str(e)}")
                if attempt < self.max_retries:
                    logger.warning(f"Network error, retrying (attempt {attempt + 1}/{self.max_retries + 1})")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
                
            except (ExternalAPIError, ExternalAPIAuthError, ExternalAPIRateLimitError):
                raise
                
            except Exception as e:
                last_error = ExternalAPIError(f"Unexpected error: {str(e)}")
                if attempt < self.max_retries:
                    logger.warning(f"Unexpected error, retrying (attempt {attempt + 1}/{self.max_retries + 1})")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
        
        if last_error:
            raise last_error
        
        raise ExternalAPIError("Request failed after all retries")
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request(
            HTTPMethod.GET,
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request(
            HTTPMethod.POST,
            endpoint,
            json_data=json_data,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request(
            HTTPMethod.PUT,
            endpoint,
            json_data=json_data,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request(
            HTTPMethod.DELETE,
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )


# Pre-configured API clients for common services
def get_pubchem_client() -> Optional[ExternalAPIClient]:
    """Get PubChem API client"""
    return ExternalAPIClient(
        base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        timeout=30.0,
    )


def get_chembl_client() -> Optional[ExternalAPIClient]:
    """Get ChEMBL API client"""
    return ExternalAPIClient(
        base_url="https://www.ebi.ac.uk/chembl/api/data",
        timeout=30.0,
    )


def get_uniprot_client() -> Optional[ExternalAPIClient]:
    """Get UniProt API client"""
    return ExternalAPIClient(
        base_url="https://rest.uniprot.org",
        timeout=30.0,
    )


def get_pdb_client() -> Optional[ExternalAPIClient]:
    """Get PDB API client"""
    return ExternalAPIClient(
        base_url="https://data.rcsb.org/rest/v1",
        timeout=30.0,
    )


async def proxy_external_api(
    api_name: str,
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Proxy request to external API.
    
    Args:
        api_name: Name/identifier for the API
        endpoint: API endpoint path
        method: HTTP method
        params: Query parameters
        json_data: JSON body data
        headers: Custom headers
        api_key: API key (if not in config)
        base_url: Base URL (if not in config)
        
    Returns:
        Response data
        
    Raises:
        ExternalAPIError: If request fails
    """
    # Get API configuration from settings or use provided values
    if not base_url:
        # Try to get from config
        base_url = getattr(settings, f"{api_name.upper()}_BASE_URL", None)
        if not base_url:
            raise ExternalAPIError(f"Base URL not configured for API: {api_name}")
    
    if not api_key:
        api_key = getattr(settings, f"{api_name.upper()}_API_KEY", None)
    
    client = ExternalAPIClient(
        base_url=base_url,
        api_key=api_key,
    )
    
    http_method = HTTPMethod(method.upper())
    
    if http_method == HTTPMethod.GET:
        return await client.get(endpoint, params=params, headers=headers)
    elif http_method == HTTPMethod.POST:
        return await client.post(endpoint, json_data=json_data, params=params, headers=headers)
    elif http_method == HTTPMethod.PUT:
        return await client.put(endpoint, json_data=json_data, params=params, headers=headers)
    elif http_method == HTTPMethod.DELETE:
        return await client.delete(endpoint, params=params, headers=headers)
    else:
        raise ExternalAPIError(f"Unsupported HTTP method: {method}")
