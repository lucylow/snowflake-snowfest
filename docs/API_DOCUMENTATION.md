# SNOWFLAKE API Documentation

## Overview

SNOWFLAKE is an AI-powered drug discovery platform that integrates AlphaFold structure prediction with molecular docking simulations.

## Base URL

```
Development: http://localhost:8000
Production: https://api.snowflake.ai
```

## Authentication

Currently, the API does not require authentication. Future versions will implement API key authentication.

## Endpoints

### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "SNOWFLAKE API",
  "version": "1.0.0"
}
```

### Submit Job

**POST** `/api/jobs`

Submit a new docking job (with or without AlphaFold prediction).

**Request Body:**
```json
{
  "job_name": "My Docking Job",
  "job_type": "sequence_to_docking",
  "protein_sequence": "MKTLILGVVLGAAVVASA...",
  "ligand_files": ["SDF content..."],
  "docking_parameters": {
    "center_x": 0.0,
    "center_y": 0.0,
    "center_z": 0.0,
    "size_x": 20.0,
    "size_y": 20.0,
    "size_z": 20.0,
    "exhaustiveness": 8,
    "num_modes": 9
  }
}
```

**Job Types:**
- `docking_only`: Use existing PDB file
- `sequence_to_docking`: Predict structure with AlphaFold, then dock

**Response:**
```json
{
  "id": "uuid-here",
  "status": "submitted",
  "job_type": "sequence_to_docking",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Job Status

**GET** `/api/jobs/{job_id}`

Retrieve job status and results.

**Response:**
```json
{
  "id": "uuid-here",
  "job_name": "My Docking Job",
  "job_type": "sequence_to_docking",
  "status": "completed",
  "protein_sequence": "MKTLIL...",
  "predicted_pdb_path": "/workspace/predictions/uuid/ranked_0.pdb",
  "plddt_score": 85.4,
  "top_binding_score": -8.2,
  "ai_report_content": "# Analysis Report\n...",
  "blockchain_tx_hash": "tx_hash_here",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:00Z"
}
```

**Status Values:**
- `submitted`: Job received
- `queued`: Waiting in queue
- `predicting_structure`: Running AlphaFold
- `structure_predicted`: Structure prediction complete
- `docking`: Running molecular docking
- `analyzing`: Generating AI report
- `completed`: Job finished successfully
- `failed`: Job failed with error

### List Jobs

**GET** `/api/jobs?skip=0&limit=20`

List all jobs with pagination.

**Query Parameters:**
- `skip`: Number of jobs to skip (default: 0)
- `limit`: Maximum jobs to return (default: 20)

**Response:**
```json
[
  {
    "id": "uuid-1",
    "status": "completed",
    ...
  },
  {
    "id": "uuid-2",
    "status": "running",
    ...
  }
]
```

### Verify Blockchain Transaction

**GET** `/api/blockchain/verify/{tx_hash}`

Verify a blockchain transaction.

**Response:**
```json
{
  "verified": true,
  "tx_hash": "abc123...",
  "blockchain": "solana",
  "transaction": {...}
}
```

### Get Job Blockchain Record

**GET** `/api/blockchain/job/{job_id}`

Get blockchain verification record for a job.

**Response:**
```json
{
  "job_id": "uuid-here",
  "has_blockchain_record": true,
  "tx_hash": "abc123...",
  "structure_hash": "sha256_hash",
  "report_hash": "sha256_hash",
  "verification": {...}
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `400`: Bad Request (validation error)
- `404`: Not Found
- `500`: Internal Server Error
- `503`: Service Unavailable

## Rate Limits

Current rate limits (subject to change):
- 100 requests per minute per IP
- 20 concurrent job submissions per IP

## WebSocket Support

Real-time job status updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/status/{job_id}')

ws.onmessage = (event) => {
  const status = JSON.parse(event.data)
  console.log('Job status:', status)
}
