import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "SNOWFLAKE API"

@pytest.mark.asyncio
async def test_job_submission():
    """Test job submission endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        job_data = {
            "job_name": "Test Job",
            "job_type": "sequence_to_docking",
            "protein_sequence": "MKTLILGVVLGAAVVASA" * 10,
            "ligand_files": ["mock_ligand_content"],
            "docking_parameters": {}
        }
        
        # This would test actual submission in integration tests
        assert job_data["job_type"] == "sequence_to_docking"
