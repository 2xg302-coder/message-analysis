import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_storyline_crud(client):
    # Create
    storyline_data = {
        "date": "2023-10-27",
        "title": "Test Storyline",
        "keywords": ["test", "keyword"],
        "description": "This is a test storyline",
        "importance": 5,
        "status": "active"
    }
    response = await client.post("/api/storylines/", json=storyline_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Storyline"
    storyline_id = data["id"]

    # Get Active
    response = await client.get("/api/storylines/active")
    assert response.status_code == 200
    active_list = response.json()
    assert any(s["id"] == storyline_id for s in active_list)

    # Archive
    response = await client.put(f"/api/storylines/{storyline_id}/archive")
    assert response.status_code == 200

    # Verify Archived
    response = await client.get("/api/storylines/active")
    active_list = response.json()
    assert not any(s["id"] == storyline_id for s in active_list)

    response = await client.get("/api/storylines/history")
    assert response.status_code == 200
    history_list = response.json()
    assert any(s["id"] == storyline_id for s in history_list)
