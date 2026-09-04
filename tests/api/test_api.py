import httpx
import pytest

from cartoon_studio.api.main import app
from cartoon_studio.domain.api_models import DashboardSnapshot, HealthResponse


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = HealthResponse.model_validate_json(response.content)
    assert body.status == "ok"


@pytest.mark.asyncio
async def test_dashboard_contract_uses_camel_case() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = DashboardSnapshot.model_validate_json(response.content)
    assert body.mode == "live"
    assert body.active_episode.state
    assert body.library.reusable_assets == 642


@pytest.mark.asyncio
async def test_demo_pipeline_advances() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        before_response = await client.get("/api/v1/dashboard")
        after_response = await client.post("/api/v1/demo/advance")

    before = DashboardSnapshot.model_validate_json(before_response.content)
    after = DashboardSnapshot.model_validate_json(after_response.content)

    assert after.active_episode.progress >= before.active_episode.progress
