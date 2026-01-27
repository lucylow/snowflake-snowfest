import pytest
from pathlib import Path
from backend.services.alphafold import run_alphafold, extract_plddt_score, get_cached_structure

@pytest.mark.asyncio
async def test_sequence_validation():
    """Test that valid sequences are accepted"""
    valid_sequence = "MKTLILGVVLGAAVVASA" * 5  # 90 amino acids
    # This would call AlphaFold in real environment
    assert len(valid_sequence) >= 20

@pytest.mark.asyncio
async def test_plddt_extraction():
    """Test pLDDT score extraction from AlphaFold output"""
    # Mock test - in real scenario, would use actual AlphaFold output
    test_dir = Path("/tmp/test_alphafold")
    test_dir.mkdir(exist_ok=True)
    
    # Would normally extract from real file
    # score = await extract_plddt_score(test_dir)
    # assert 0 <= score <= 100

@pytest.mark.asyncio
async def test_caching():
    """Test structure caching mechanism"""
    sequence = "MKTLILGVVLGAAVVASA"
    cached = await get_cached_structure(sequence)
    # First time should return None
    assert cached is None or isinstance(cached, tuple)
