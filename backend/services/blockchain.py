import os
import hashlib
import logging
import asyncio
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
        
    Raises:
        BlockchainError: If blockchain operation fails
    """
    from backend.exceptions import BlockchainError
    
    try:
        # Serialize data for on-chain storage
        memo_data = json.dumps(verification_data, separators=(',', ':'))
        
        if len(memo_data) > 1232:
            logger.warning(f"Memo data too long ({len(memo_data)} chars), truncating to 1232 chars")
            memo_data = memo_data[:1232]
        
        # Get recent blockhash with retry
        max_retries = 3
        recent_blockhash = None
        for attempt in range(max_retries):
            try:
                recent_blockhash = await get_recent_blockhash()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise BlockchainError(f"Failed to get recent blockhash after {max_retries} attempts: {str(e)}")
                logger.warning(f"Failed to get blockhash (attempt {attempt + 1}/{max_retries}): {str(e)}")
                await asyncio.sleep(1)
        
        # Create transaction payload
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                {
                    "memo": memo_data,
                    "recentBlockhash": recent_blockhash,
                    "feePayer": get_public_key_from_private(SOLANA_PRIVATE_KEY)
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    SOLANA_RPC_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            except httpx.TimeoutException:
                raise BlockchainError("Solana RPC request timed out after 30 seconds")
            except httpx.NetworkError as e:
                raise BlockchainError(f"Network error connecting to Solana RPC: {str(e)}")
            except httpx.RequestError as e:
                raise BlockchainError(f"Request error to Solana RPC: {str(e)}")
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                raise BlockchainError(f"Solana RPC error (status {response.status_code}): {error_text}")
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Solana RPC: {str(e)}")
                raise BlockchainError("Invalid response format from Solana RPC")
            
            if "error" in result:
                error_info = result["error"]
                error_msg = error_info.get("message", "Unknown error") if isinstance(error_info, dict) else str(error_info)
                raise BlockchainError(f"Solana transaction error: {error_msg}")
            
            if "result" not in result:
                raise BlockchainError("No result in Solana RPC response")
            
            return result["result"]
    except BlockchainError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error storing on Solana: {str(e)}", exc_info=True)
        raise BlockchainError(f"Unexpected error storing on blockchain: {str(e)}")

async def get_recent_blockhash() -> str:
    """Get recent blockhash from Solana"""
    from backend.exceptions import BlockchainError
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getRecentBlockhash",
        "params": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    SOLANA_RPC_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            except httpx.TimeoutException:
                raise BlockchainError("Solana RPC request timed out")
            except httpx.NetworkError as e:
                raise BlockchainError(f"Network error connecting to Solana RPC: {str(e)}")
            except httpx.RequestError as e:
                raise BlockchainError(f"Request error to Solana RPC: {str(e)}")
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                raise BlockchainError(f"Solana RPC error (status {response.status_code}): {error_text}")
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Solana RPC: {str(e)}")
                raise BlockchainError("Invalid response format from Solana RPC")
            
            if "error" in result:
                error_info = result["error"]
                error_msg = error_info.get("message", "Unknown error") if isinstance(error_info, dict) else str(error_info)
                raise BlockchainError(f"Solana RPC error: {error_msg}")
            
            if "result" not in result or "value" not in result["result"]:
                raise BlockchainError("Invalid response structure from Solana RPC")
            
            blockhash = result["result"]["value"].get("blockhash")
            if not blockhash:
                raise BlockchainError("No blockhash in Solana RPC response")
            
            return blockhash
    except BlockchainError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting blockhash: {str(e)}", exc_info=True)
        raise BlockchainError(f"Unexpected error getting blockhash: {str(e)}")

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
    from backend.exceptions import BlockchainError
    
    if not tx_hash or not tx_hash.strip():
        return {
            "verified": False,
            "message": "Transaction hash is required",
            "tx_hash": tx_hash or "None"
        }
    
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
            try:
                response = await client.post(
                    SOLANA_RPC_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            except httpx.TimeoutException:
                return {
                    "verified": False,
                    "message": "Verification request timed out",
                    "tx_hash": tx_hash
                }
            except httpx.NetworkError as e:
                logger.error(f"Network error verifying transaction {tx_hash}: {str(e)}")
                return {
                    "verified": False,
                    "message": f"Network error: {str(e)}",
                    "tx_hash": tx_hash
                }
            except httpx.RequestError as e:
                logger.error(f"Request error verifying transaction {tx_hash}: {str(e)}")
                return {
                    "verified": False,
                    "message": f"Request error: {str(e)}",
                    "tx_hash": tx_hash
                }
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "Unknown error"
                logger.error(f"Solana RPC error verifying transaction {tx_hash}: status {response.status_code}, {error_text}")
                return {
                    "verified": False,
                    "message": f"RPC error (status {response.status_code})",
                    "tx_hash": tx_hash
                }
            
            try:
                result = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response verifying transaction {tx_hash}: {str(e)}")
                return {
                    "verified": False,
                    "message": "Invalid response format",
                    "tx_hash": tx_hash
                }
            
            if "error" in result:
                error_info = result["error"]
                error_msg = error_info.get("message", "Transaction not found") if isinstance(error_info, dict) else str(error_info)
                return {
                    "verified": False,
                    "message": error_msg,
                    "tx_hash": tx_hash
                }
            
            if "result" not in result:
                return {
                    "verified": False,
                    "message": "No result in response",
                    "tx_hash": tx_hash
                }
            
            return {
                "verified": True,
                "transaction": result["result"],
                "tx_hash": tx_hash,
                "blockchain": "solana"
            }
            
    except Exception as e:
        logger.error(f"Failed to verify transaction {tx_hash}: {str(e)}", exc_info=True)
        return {
            "verified": False,
            "message": f"Verification error: {str(e)}",
            "tx_hash": tx_hash
        }
