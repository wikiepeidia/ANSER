import os
import sys
import asyncio
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Force LOCAL mock environment for testing
os.environ["ENV"] = "LOCAL"

# Add project root to sys.path using pathlib
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.api.main import app
from src.core.engine import TASK_REGISTRY

@pytest.mark.asyncio
async def test_chat_background_task():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Hit /chat endpoint
        response = await client.post("/chat", json={
            "user_id": 1,
            "store_id": 1,
            "message": "[USER REQUEST] Hello"
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "processing"
        
        task_id = data["task_id"]
        
        # Step 2: Poll /api/v1/task/{task_id}
        max_retries = 20
        completed = False
        
        for _ in range(max_retries):
            await asyncio.sleep(0.1)
            status_resp = await client.get(f"/api/v1/task/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            
            if status_data["status"] == "completed":
                assert "result" in status_data
                completed = True
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Task failed: {status_data.get('error')}")
                
        assert completed, "Task did not complete within the expected time"
