import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from cartoon_studio.config import get_settings
from cartoon_studio.domain.api_models import DashboardSnapshot, HealthResponse
from cartoon_studio.workflows.demo import demo_studio

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("api_started", environment=settings.environment, version=settings.api_version)
    yield
    logger.info("api_stopped")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type", "Idempotency-Key"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="cartoon-studio-api",
        version=settings.api_version,
        environment=settings.environment,
    )


@app.get("/api/v1/dashboard", response_model=DashboardSnapshot)
async def dashboard() -> DashboardSnapshot:
    return demo_studio.snapshot()


@app.post("/api/v1/demo/advance", response_model=DashboardSnapshot)
async def advance_demo() -> DashboardSnapshot:
    return demo_studio.advance()


async def event_stream() -> AsyncIterator[str]:
    last_event_id = ""
    while True:
        snapshot = demo_studio.snapshot()
        newest = snapshot.events[0] if snapshot.events else None
        if newest and newest.id != last_event_id:
            last_event_id = newest.id
            payload = json.dumps(newest.model_dump(by_alias=True))
            yield f"id: {newest.id}\nevent: pipeline\ndata: {payload}\n\n"
        else:
            yield ": heartbeat\n\n"
        await asyncio.sleep(settings.event_heartbeat_seconds)


@app.get("/api/v1/events/stream", response_class=StreamingResponse)
async def events() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream")
