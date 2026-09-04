from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PipelineState(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    ASSET_PREPARATION = "asset_preparation"
    SCENE_PRODUCTION = "scene_production"
    SCENE_VALIDATION = "scene_validation"
    AUDIO_PRODUCTION = "audio_production"
    RENDERING = "rendering"
    FINAL_VALIDATION = "final_validation"
    NEEDS_APPROVAL = "needs_approval"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class Metric(ApiModel):
    label: str
    value: str
    detail: str
    tone: str


class PipelineEvent(ApiModel):
    id: str
    time: str
    title: str
    detail: str
    status: str


class EpisodeSummary(ApiModel):
    id: str
    title: str
    objective: str
    format: str
    state: PipelineState
    progress: int = Field(ge=0, le=100)
    scene_progress: str
    cost: str
    scheduled_for: str


class LibrarySummary(ApiModel):
    sources: int = Field(ge=0)
    reusable_assets: int = Field(ge=0)
    stale_sources: int = Field(ge=0)
    missing_rights: int = Field(ge=0)
    storage: str


class DashboardSnapshot(ApiModel):
    generated_at: datetime
    mode: str
    metrics: list[Metric]
    active_episode: EpisodeSummary
    upcoming_episodes: list[EpisodeSummary]
    events: list[PipelineEvent]
    library: LibrarySummary


class HealthResponse(ApiModel):
    status: str
    service: str
    version: str
    environment: str
