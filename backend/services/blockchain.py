import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import json
import aiofiles

logger = logging.getLogger(__name__)

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY")

async def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(8192):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()

async def compute_string_hash(content: str) -> str:
    """Compute SHA-256 hash of a string"""
    return hashlib.sha256(content.encode()).hexdigest()

async def store_on_blockchain(
    job_id: str,
    predicted_pdb_path: Optional[Path],
    report_content: str
) -> Dict[str, Any]:
    """
    Store verification data on Solana blockchain
    
    Args:
        job_id: Unique job identifier
        predicted_pdb_path: Path to predicted structure PDB file
        report_content: AI-generated report content
        
    Returns:
        Dictionary with transaction hash and content hashes
    """
    
    try:
        # Compute hashes of the data
        structure_hash = None
        if predicted_pdb_path and predicted_pdb_path.exists():
            structure_hash = await compute_file_hash(predicted_pdb_path)
        
        report_hash = await compute_string_hash(report_content)
        
        # Create verification payload
        verification_data = {
            "job_id": job_id,
            "structure_hash": structure_hash,
            "report_hash": report_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        # Store on blockchain
        if SOLANA_PRIVATE_KEY:
            tx_hash = await store_on_solana(verification_data)
        else:
            logger.warning("No Solana private key configured, using mock storage")
            tx_hash = f"mock_tx_{hashlib.sha256(json.dumps(verification_data).encode()).hexdigest()[:16]}"
        
        logger.info(f"Stored verification for job {job_id} on blockchain: {tx_hash}")
        
        return {
            "tx_hash": tx_hash,
            "structure_hash": structure_hash,
            "report_hash": report_hash,
            "blockchain": "solana",
            "network": "devnet" if "devnet" in SOLANA_RPC_URL else "mainnet"
        }
        
    except Exception as e:
        logger.error(f"Failed to store on blockchain for job {job_id}: {str(e)}")
        # Return mock data on error to prevent workflow failure
        return {
            "tx_hash": f"error_mock_{job_id[:16]}",
            "structure_hash": structure_hash if predicted_pdb_path else None,
            "report_hash": report_hash,
            "blockchain": "solana",
            "network": "error",
            "error": str(e)
        }

async def store_on_solana(verification_data: Dict[str, Any]) -> str:
    """
    Store verification data on Solana blockchain using a simple memo transaction
    
    Args:
        verification_data: Data to store on-chain
        
    Returns:
        Transaction signature/hash
    """
    
    # Serialize data for on-chain storage
    memo_data = json.dumps(verification_data, separators=(',', ':'))
    
    # Create transaction payload
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sendTransaction",
        "params": [
            {
                "memo": memo_data[:1232],  # Solana memo limit
                "recentBlockhash": await get_recent_blockhash(),
                "feePayer": get_public_key_from_private(SOLANA_PRIVATE_KEY)
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SOLANA_RPC_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Solana RPC error: {response.text}")
        
        result = response.json()
        
        if "error" in result:
            raise RuntimeError(f"Solana transaction error: {result['error']}")
        
        return result["result"]

async def get_recent_blockhash() -> str:
    """Get recent blockhash from Solana"""
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getRecentBlockhash",
        "params": []
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            SOLANA_RPC_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        return result["result"]["value"]["blockhash"]

def get_public_key_from_private(private_key: str) -> str:
    """Extract public key from private key (simplified)"""
    # In production, use proper Solana key derivation
    # This is a simplified mock for demonstration
    return hashlib.sha256(private_key.encode()).hexdigest()[:44]

async def verify_blockchain_record(tx_hash: str) -> Dict[str, Any]:
    """
    Verify a blockchain record by transaction hash
    
    Args:
        tx_hash: Transaction hash to verify
        
    Returns:
        Verification data from blockchain
    """
    
    if tx_hash.startswith("mock_tx_") or tx_hash.startswith("error_mock_"):
        return {
            "verified": False,
            "message": "Mock transaction - not on real blockchain",
            "tx_hash": tx_hash
        }
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [tx_hash, {"encoding": "json"}]
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SOLANA_RPC_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            
            if "error" in result:
                return {
                    "verified": False,
                    "message": "Transaction not found on blockchain",
                    "tx_hash": tx_hash
                }
            
            return {
                "verified": True,
                "transaction": result["result"],
                "tx_hash": tx_hash,
                "blockchain": "solana"
            }
            
    except Exception as e:
        logger.error(f"Failed to verify transaction {tx_hash}: {str(e)}")
        return {
            "verified": False,
            "message": f"Verification error: {str(e)}",
            "tx_hash": tx_hash
        }
