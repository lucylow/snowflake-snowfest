# External API Integration Guide

This document describes how to integrate and use external APIs in the SNOWFLAKE application.

## Overview

The external API integration system provides a unified interface for calling external APIs through the backend. This approach offers several benefits:

- **Security**: API keys are stored server-side, not exposed to the frontend
- **Rate Limiting**: Centralized rate limiting and retry logic
- **Error Handling**: Consistent error handling across all external APIs
- **Caching**: Potential for caching responses (future enhancement)
- **Logging**: Centralized logging of all external API calls

## Architecture

### Backend Components

1. **`backend/services/external_api.py`**: Core service for external API calls
   - `ExternalAPIClient`: Generic HTTP client with retry logic, rate limiting, and error handling
   - Pre-configured clients for common APIs (PubChem, ChEMBL, UniProt, PDB)
   - `proxy_external_api()`: Generic proxy function

2. **`backend/routes/external_api.py`**: API routes for external API access
   - `/api/external/proxy`: Generic proxy endpoint
   - `/api/external/pubchem/*`: PubChem-specific endpoints
   - `/api/external/chembl/*`: ChEMBL-specific endpoints
   - `/api/external/uniprot/*`: UniProt-specific endpoints
   - `/api/external/pdb/*`: PDB-specific endpoints
   - `/api/external/apis`: List available APIs

3. **`backend/config.py`**: Configuration for external APIs
   - API keys and base URLs
   - Timeout and retry settings

### Frontend Components

**`lib/api-client.ts`**: Frontend API client with methods for external APIs
- `proxyExternalAPI()`: Generic proxy method
- `getPubChemData()`: PubChem-specific method
- `getChEMBLData()`: ChEMBL-specific method
- `getUniProtData()`: UniProt-specific method
- `getPDBData()`: PDB-specific method
- `listAvailableAPIs()`: List available APIs

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# External API Settings
EXTERNAL_API_TIMEOUT=30.0
EXTERNAL_API_MAX_RETRIES=3
EXTERNAL_API_RETRY_DELAY=1.0

# PubChem (usually no API key needed)
PUBCHEM_BASE_URL=https://pubchem.ncbi.nlm.nih.gov/rest/pug
PUBCHEM_API_KEY=

# ChEMBL (usually no API key needed)
CHEMBL_BASE_URL=https://www.ebi.ac.uk/chembl/api/data
CHEMBL_API_KEY=

# UniProt (usually no API key needed)
UNIPROT_BASE_URL=https://rest.uniprot.org
UNIPROT_API_KEY=

# PDB (usually no API key needed)
PDB_BASE_URL=https://data.rcsb.org/rest/v1
PDB_API_KEY=
```

## Usage Examples

### Backend Usage

#### Using the ExternalAPIClient directly

```python
from backend.services.external_api import ExternalAPIClient

# Create a custom client
client = ExternalAPIClient(
    base_url="https://api.example.com",
    api_key="your-api-key",
    api_key_header="X-API-Key",
    timeout=30.0,
)

# Make a GET request
result = await client.get("endpoint/path", params={"param": "value"})

# Make a POST request
result = await client.post(
    "endpoint/path",
    json_data={"key": "value"},
    params={"param": "value"},
)
```

#### Using pre-configured clients

```python
from backend.services.external_api import get_pubchem_client

client = get_pubchem_client()
result = await client.get(
    "compound/name/aspirin/property/MolecularWeight,CanonicalSMILES/JSON"
)
```

#### Using the proxy function

```python
from backend.services.external_api import proxy_external_api

result = await proxy_external_api(
    api_name="custom_api",
    endpoint="data/endpoint",
    method="GET",
    params={"query": "value"},
    api_key="your-key",
    base_url="https://api.example.com",
)
```

### Frontend Usage

#### Using the generic proxy method

```typescript
import { apiClient } from "@/lib/api-client"

// Proxy any external API
const result = await apiClient.proxyExternalAPI(
  "custom_api",
  "data/endpoint",
  "GET",
  { query: "value" },
  undefined, // jsonData
  undefined, // headers
  "your-api-key", // optional
  "https://api.example.com" // optional
)
```

#### Using PubChem API

```typescript
import { apiClient } from "@/lib/api-client"

// Get compound properties by name
const aspirin = await apiClient.getPubChemData(
  "compound/name/aspirin/property/MolecularWeight,CanonicalSMILES/JSON"
)

// Get compound by CID
const compound = await apiClient.getPubChemData(
  "compound/cid/2244/property/MolecularWeight/JSON"
)

// Search by SMILES
const smiles = await apiClient.getPubChemData(
  "compound/smiles/CCO/property/MolecularWeight/JSON"
)
```

#### Using ChEMBL API

```typescript
import { apiClient } from "@/lib/api-client"

// Get molecule by ChEMBL ID
const molecule = await apiClient.getChEMBLData("molecule/CHEMBL25")

// Search molecules by name
const results = await apiClient.getChEMBLData("molecule", {
  pref_name__icontains: "aspirin",
  limit: 10,
})

// Get activities for a molecule
const activities = await apiClient.getChEMBLData("activity", {
  molecule_chembl_id: "CHEMBL25",
})
```

#### Using UniProt API

```typescript
import { apiClient } from "@/lib/api-client"

// Get protein by accession
const protein = await apiClient.getUniProtData("uniprotkb/P04637")

// Search proteins
const results = await apiClient.getUniProtData("uniprotkb/search", {
  query: "p53",
  format: "json",
})
```

#### Using PDB API

```typescript
import { apiClient } from "@/lib/api-client"

// Get entry by PDB ID
const entry = await apiClient.getPDBData("core/entry/1ABC")

// Get polymer entities
const entities = await apiClient.getPDBData("core/entry/1ABC/polymer_entities")
```

#### Listing available APIs

```typescript
import { apiClient } from "@/lib/api-client"

const apis = await apiClient.listAvailableAPIs()
console.log(apis.available_apis)
```

## Common External APIs for Drug Discovery

### PubChem

**Base URL**: `https://pubchem.ncbi.nlm.nih.gov/rest/pug`

**Common Endpoints**:
- `compound/name/{name}/property/{properties}/JSON` - Get properties by compound name
- `compound/cid/{cid}/property/{properties}/JSON` - Get properties by CID
- `compound/smiles/{smiles}/property/{properties}/JSON` - Get properties by SMILES
- `compound/substructure/{smiles}/JSON` - Substructure search

**Example**:
```typescript
const result = await apiClient.getPubChemData(
  "compound/name/aspirin/property/MolecularWeight,CanonicalSMILES,IsomericSMILES/JSON"
)
```

### ChEMBL

**Base URL**: `https://www.ebi.ac.uk/chembl/api/data`

**Common Endpoints**:
- `molecule/{chembl_id}` - Get molecule by ChEMBL ID
- `molecule?pref_name__icontains={name}` - Search by name
- `activity?molecule_chembl_id={chembl_id}` - Get activities
- `target?pref_name__icontains={name}` - Search targets

**Example**:
```typescript
const molecule = await apiClient.getChEMBLData("molecule/CHEMBL25")
```

### UniProt

**Base URL**: `https://rest.uniprot.org`

**Common Endpoints**:
- `uniprotkb/{accession}` - Get protein by accession
- `uniprotkb/search?query={query}` - Search proteins
- `uniparc/{upi}` - Get UniParc entry

**Example**:
```typescript
const protein = await apiClient.getUniProtData("uniprotkb/P04637")
```

### PDB (Protein Data Bank)

**Base URL**: `https://data.rcsb.org/rest/v1`

**Common Endpoints**:
- `core/entry/{pdb_id}` - Get entry by PDB ID
- `core/entry/{pdb_id}/polymer_entities` - Get polymer entities
- `core/entry/{pdb_id}/nonpolymer_entities` - Get non-polymer entities

**Example**:
```typescript
const entry = await apiClient.getPDBData("core/entry/1ABC")
```

## Error Handling

The external API client handles various error scenarios:

- **401 Unauthorized**: `ExternalAPIAuthError` - Invalid API key
- **429 Too Many Requests**: `ExternalAPIRateLimitError` - Rate limit exceeded
- **504 Gateway Timeout**: `ExternalAPITimeoutError` - Request timed out
- **500+ Server Errors**: Automatic retry with exponential backoff
- **Network Errors**: Automatic retry with exponential backoff

### Frontend Error Handling

```typescript
import { apiClient, APIError } from "@/lib/api-client"

try {
  const result = await apiClient.getPubChemData("compound/name/aspirin/...")
} catch (error) {
  if (error instanceof APIError) {
    if (error.status === 401) {
      console.error("Authentication failed")
    } else if (error.status === 429) {
      console.error("Rate limit exceeded")
    } else if (error.status === 504) {
      console.error("Request timed out")
    } else {
      console.error("API error:", error.message)
    }
  } else {
    console.error("Unexpected error:", error)
  }
}
```

## Adding New External APIs

### Step 1: Add Configuration

Add settings to `backend/config.py`:

```python
# External APIs - Your API
YOUR_API_BASE_URL: str = Field(
    default="https://api.example.com",
    env="YOUR_API_BASE_URL"
)
YOUR_API_KEY: Optional[str] = Field(default=None, env="YOUR_API_KEY")
```

### Step 2: Create Client Function (Optional)

Add to `backend/services/external_api.py`:

```python
def get_your_api_client() -> Optional[ExternalAPIClient]:
    """Get Your API client"""
    return ExternalAPIClient(
        base_url=settings.YOUR_API_BASE_URL,
        api_key=settings.YOUR_API_KEY,
        timeout=30.0,
    )
```

### Step 3: Add Route (Optional)

Add to `backend/routes/external_api.py`:

```python
@router.get("/external/your-api/{endpoint:path}")
async def your_api_proxy(
    endpoint: str,
    params: Optional[Dict[str, Any]] = Query(None),
):
    """Proxy request to Your API"""
    try:
        client = get_your_api_client()
        if not client:
            raise HTTPException(status_code=503, detail="Your API client not available")
        
        result = await client.get(endpoint, params=params)
        return {"success": True, "data": result}
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

### Step 4: Add Frontend Method (Optional)

Add to `lib/api-client.ts`:

```typescript
async getYourAPIData(
  endpoint: string,
  params?: Record<string, any>,
): Promise<any> {
  try {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : ""
    const response = await fetchWithTimeout(
      `${this.baseUrl}/api/external/your-api/${endpoint}${queryString}`,
    )
    return this.handleResponse(response, "Your API")
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError("Your API request failed", 0, "NETWORK_ERROR")
  }
}
```

## Best Practices

1. **Always use the backend proxy** - Never call external APIs directly from the frontend
2. **Store API keys securely** - Use environment variables, never commit keys to git
3. **Handle errors gracefully** - Always wrap API calls in try-catch blocks
4. **Use appropriate timeouts** - Adjust timeout based on expected response time
5. **Implement caching** - Cache frequently accessed data (future enhancement)
6. **Monitor rate limits** - Be aware of API rate limits and implement backoff
7. **Log API calls** - Use logging to track API usage and debug issues

## Security Considerations

- API keys are stored server-side only
- CORS is configured to restrict frontend origins
- Rate limiting can be enabled to prevent abuse
- All requests are logged for audit purposes
- Input validation prevents injection attacks

## Future Enhancements

- [ ] Response caching with Redis
- [ ] Request/response transformation middleware
- [ ] API usage analytics and monitoring
- [ ] Webhook support for async operations
- [ ] GraphQL proxy support
- [ ] Batch request support
