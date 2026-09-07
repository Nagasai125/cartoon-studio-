from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self, cast

from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from cartoon_studio.domain.api_models import ApiModel, DashboardSnapshot, PipelineState, to_camel

WORKFLOW_STAGE_ORDER = (
    PipelineState.PLANNING,
    PipelineState.RESEARCHING,
    PipelineState.SCRIPTING,
    PipelineState.SCRIPT_VALIDATION,
    PipelineState.STORYBOARDING,
    PipelineState.ASSET_PREPARATION,
    PipelineState.SCENE_PRODUCTION,
    PipelineState.SCENE_VALIDATION,
    PipelineState.AUDIO_PRODUCTION,
    PipelineState.RENDERING,
    PipelineState.FINAL_VALIDATION,
)


class WorkflowModel(ApiModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class StageStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class EpisodeBrief(WorkflowModel):
    schema_version: Literal[1] = 1
    episode_id: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=500)
    format: str = Field(min_length=1, max_length=80)
    scheduled_for: datetime
    target_duration_seconds: int = Field(ge=60, le=1200)
    scene_count: int = Field(ge=1, le=24)

    @field_validator("scheduled_for")
    @classmethod
    def require_scheduled_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)

    @field_serializer("scheduled_for")
    def serialize_scheduled_for(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class StagePolicy(WorkflowModel):
    state: PipelineState
    attempt_limit: int = Field(ge=1, le=5)
    deadline_minutes: int = Field(ge=1, le=360)
    simulated_cost_micros: int = Field(ge=0)
    output_items: int = Field(ge=1, le=100)
    output_duration_seconds: int = Field(ge=0, le=3600)
    validator_count: int = Field(ge=0, le=100)


class WorkflowPolicy(WorkflowModel):
    schema_version: Literal[1] = 1
    definition_version: str = Field(min_length=1, max_length=40)
    currency: Literal["USD"] = "USD"
    maximum_budget_micros: int = Field(gt=0)
    publishing_enabled: Literal[False] = False
    stages: list[StagePolicy]

    @model_validator(mode="after")
    def validate_stages(self) -> Self:
        states = tuple(stage.state for stage in self.stages)
        if states != WORKFLOW_STAGE_ORDER:
            raise ValueError("policy stages must match the workflow definition")
        if sum(stage.simulated_cost_micros for stage in self.stages) > self.maximum_budget_micros:
            raise ValueError("policy stage costs exceed the maximum episode budget")
        return self


class StageOutput(WorkflowModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    item_count: int = Field(ge=1, le=100)
    duration_seconds: int = Field(ge=0, le=3600)
    validator_count: int = Field(ge=0, le=100)


class StageRecord(WorkflowModel):
    state: PipelineState
    status: StageStatus = StageStatus.PENDING
    idempotency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    attempt_count: int = Field(default=0, ge=0, le=5)
    attempt_limit: int = Field(ge=1, le=5)
    deadline_minutes: int = Field(ge=1, le=360)
    cost_micros: int = Field(default=0, ge=0)
    output: StageOutput | None = None

    @model_validator(mode="after")
    def validate_completion(self) -> Self:
        if self.status == StageStatus.COMPLETED and (
            self.output is None or self.input_sha256 is None
        ):
            raise ValueError("completed stages require input and output metadata")
        if self.status == StageStatus.COMPLETED and self.attempt_count == 0:
            raise ValueError("completed stages require at least one attempt")
        if self.status == StageStatus.PENDING and (
            self.output is not None or self.input_sha256 is not None
        ):
            raise ValueError("pending stages cannot have input or output metadata")
        if self.attempt_count > self.attempt_limit:
            raise ValueError("stage attempt limit exceeded")
        return self


class CostLedger(WorkflowModel):
    currency: Literal["USD"] = "USD"
    simulated: Literal[True] = True
    budget_micros: int = Field(gt=0)
    reserved_micros: int = Field(default=0, ge=0)
    spent_micros: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_budget(self) -> Self:
        if self.reserved_micros + self.spent_micros > self.budget_micros:
            raise ValueError("reserved and spent cost exceeds the episode budget")
        return self


class WorkflowEvent(WorkflowModel):
    sequence: int = Field(ge=1)
    occurred_at: datetime
    state: PipelineState
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=240)
    status: Literal["complete", "waiting", "warning"]

    @field_validator("occurred_at")
    @classmethod
    def require_event_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)

    @field_serializer("occurred_at")
    def serialize_occurred_at(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class QAReport(WorkflowModel):
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checks_total: int = Field(gt=0)
    checks_passed: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    passed: bool

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        all_checks_pass = self.checks_passed == self.checks_total and self.finding_count == 0
        if self.passed != all_checks_pass:
            raise ValueError("QA result does not match its check totals")
        return self


class WorkflowCheckpoint(WorkflowModel):
    schema_version: Literal[1] = 1
    definition_version: str = Field(min_length=1, max_length=40)
    workflow_run_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")
    parent_checkpoint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    episode: EpisodeBrief
    state: PipelineState
    stages: list[StageRecord]
    cost: CostLedger
    events: list[WorkflowEvent] = Field(
        default_factory=lambda: list[WorkflowEvent](), max_length=100
    )
    qa_report: QAReport | None = None
    final_render_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    publishing_enabled: Literal[False] = False
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_checkpoint_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)

    @field_serializer("created_at", "updated_at")
    def serialize_timestamps(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @model_validator(mode="after")
    def validate_progress(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("checkpoint update cannot predate creation")
        states = tuple(stage.state for stage in self.stages)
        if states != WORKFLOW_STAGE_ORDER:
            raise ValueError("checkpoint stages must match the workflow definition")

        completed = 0
        pending_seen = False
        for stage in self.stages:
            if stage.status == StageStatus.PENDING:
                pending_seen = True
            elif pending_seen:
                raise ValueError("completed workflow stages must be contiguous")
            else:
                completed += 1

        expected_state = (
            PipelineState.NEEDS_APPROVAL
            if completed == len(WORKFLOW_STAGE_ORDER)
            else WORKFLOW_STAGE_ORDER[completed]
        )
        if self.state != expected_state:
            raise ValueError("checkpoint state does not match completed stages")

        if self.state == PipelineState.NEEDS_APPROVAL:
            if self.qa_report is None or not self.qa_report.passed:
                raise ValueError("owner approval requires a passing QA report")
            if self.final_render_sha256 is None:
                raise ValueError("owner approval requires a final render hash")
        elif self.qa_report is not None or self.final_render_sha256 is not None:
            raise ValueError("final evidence is only valid after workflow completion")
        return self


SENSITIVE_KEY_FRAGMENTS = (
    "apikey",
    "authorization",
    "credential",
    "localpath",
    "oauth",
    "password",
    "payload",
    "prompt",
    "secret",
    "refreshtoken",
    "signedurl",
    "sourcetext",
    "token",
)
PRIVATE_VALUE_MARKERS = (
    "/users/",
    "/home/runner/",
    "begin private key",
    "authorization: bearer ",
    "aiza",
    "akia",
    "bearer gh",
    "c:\\",
    "github_pat_",
    "ghp_",
    "http://",
    "https://",
    "sk-",
    "xoxb-",
)


def assert_public_safe(value: object) -> None:
    if not isinstance(value, (WorkflowCheckpoint, DashboardSnapshot)):
        raise ValueError("public output must use an approved model")
    _assert_public_safe_value(cast(object, value.model_dump(mode="json", by_alias=True)))


def _assert_public_safe_value(value: object) -> None:
    if isinstance(value, ApiModel):
        _assert_public_safe_value(cast(object, value.model_dump(mode="json", by_alias=True)))
        return

    if isinstance(value, dict):
        for key, child in cast(dict[object, object], value).items():
            normalized_key = str(key).lower().replace("_", "").replace("-", "")
            if any(fragment in normalized_key for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"public output contains forbidden key: {key}")
            _assert_public_safe_value(child)
    elif isinstance(value, list):
        for child in cast(list[object], value):
            _assert_public_safe_value(child)
    elif isinstance(value, str):
        normalized_value = value.lower()
        if any(marker in normalized_value for marker in PRIVATE_VALUE_MARKERS):
            raise ValueError("public output contains a private value marker")


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("workflow timestamps must include a timezone")
    return value
