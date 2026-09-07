import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from cartoon_studio.domain.api_models import (
    DashboardSnapshot,
    EpisodeSummary,
    LibrarySummary,
    Metric,
    PipelineEvent,
    PipelineState,
)
from cartoon_studio.domain.workflow_models import (
    WORKFLOW_STAGE_ORDER,
    CostLedger,
    EpisodeBrief,
    QAReport,
    StageOutput,
    StageRecord,
    StageStatus,
    WorkflowCheckpoint,
    WorkflowEvent,
    WorkflowPolicy,
)
from cartoon_studio.providers.contracts import StageProvider, TransientProviderError


class WorkflowExecutionError(RuntimeError):
    def __init__(self, message: str, checkpoint: WorkflowCheckpoint) -> None:
        super().__init__(message)
        self.checkpoint = checkpoint


class BudgetExceededError(WorkflowExecutionError):
    pass


class CheckpointMismatchError(RuntimeError):
    pass


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_brief(path: Path) -> EpisodeBrief:
    return EpisodeBrief.model_validate_json(path.read_text(encoding="utf-8"))


def load_policy(path: Path) -> WorkflowPolicy:
    return WorkflowPolicy.model_validate_json(path.read_text(encoding="utf-8"))


def create_checkpoint(
    *,
    brief: EpisodeBrief,
    policy: WorkflowPolicy,
    workflow_run_id: str,
    budget_micros: int,
) -> WorkflowCheckpoint:
    if budget_micros > policy.maximum_budget_micros:
        raise ValueError("episode budget cannot exceed the policy maximum")

    now = datetime.now(UTC)
    stages = [
        StageRecord(
            state=stage.state,
            idempotency_key=sha256_json(
                {
                    "definitionVersion": policy.definition_version,
                    "episodeId": brief.episode_id,
                    "state": stage.state.value,
                }
            ),
            attempt_limit=stage.attempt_limit,
            deadline_minutes=stage.deadline_minutes,
        )
        for stage in policy.stages
    ]
    return WorkflowCheckpoint(
        definition_version=policy.definition_version,
        workflow_run_id=workflow_run_id,
        episode=brief,
        state=WORKFLOW_STAGE_ORDER[0],
        stages=stages,
        cost=CostLedger(
            currency=policy.currency,
            budget_micros=budget_micros,
        ),
        created_at=now,
        updated_at=now,
    )


def validate_checkpoint(
    checkpoint: WorkflowCheckpoint, policy: WorkflowPolicy, provider: StageProvider
) -> None:
    if checkpoint.definition_version != policy.definition_version:
        raise CheckpointMismatchError("checkpoint workflow definition does not match policy")
    if checkpoint.cost.currency != policy.currency:
        raise CheckpointMismatchError("checkpoint currency does not match policy")
    if checkpoint.cost.budget_micros > policy.maximum_budget_micros:
        raise CheckpointMismatchError("checkpoint budget exceeds policy maximum")

    input_sha256 = sha256_json(checkpoint.episode.model_dump(mode="json", by_alias=True))
    expected_spent_micros = 0
    pending_seen = False
    for record, stage in zip(checkpoint.stages, policy.stages, strict=True):
        expected_idempotency_key = sha256_json(
            {
                "definitionVersion": policy.definition_version,
                "episodeId": checkpoint.episode.episode_id,
                "state": stage.state.value,
            }
        )
        if (
            record.state != stage.state
            or record.attempt_limit != stage.attempt_limit
            or record.deadline_minutes != stage.deadline_minutes
            or record.idempotency_key != expected_idempotency_key
        ):
            raise CheckpointMismatchError("checkpoint stage contract does not match policy")
        if record.status == StageStatus.PENDING:
            pending_seen = True
            if record.cost_micros != 0:
                raise CheckpointMismatchError("pending stage cannot record cost")
            continue
        if pending_seen:
            raise CheckpointMismatchError("completed checkpoint stages are not contiguous")
        if record.output is None or record.input_sha256 != input_sha256:
            raise CheckpointMismatchError("completed stage input digest does not match")
        if record.cost_micros != stage.simulated_cost_micros:
            raise CheckpointMismatchError("completed stage cost does not match policy")
        if not provider.verify(
            brief=checkpoint.episode,
            stage=stage,
            input_sha256=input_sha256,
            definition_version=policy.definition_version,
            output=record.output,
        ):
            raise CheckpointMismatchError("completed stage output does not match its input")
        expected_spent_micros += record.cost_micros
        input_sha256 = record.output.sha256

    if checkpoint.cost.reserved_micros != 0:
        raise CheckpointMismatchError("persisted dry-run checkpoint cannot retain reservations")
    if checkpoint.cost.spent_micros != expected_spent_micros:
        raise CheckpointMismatchError("checkpoint cost ledger does not reconcile")

    if checkpoint.state == PipelineState.NEEDS_APPROVAL:
        expected_render_sha256 = _completed_output(checkpoint, PipelineState.RENDERING).sha256
        expected_qa = _qa_report(checkpoint, policy.stages[-1].validator_count)
        if checkpoint.final_render_sha256 != expected_render_sha256:
            raise CheckpointMismatchError("final render hash does not match rendering output")
        if checkpoint.qa_report != expected_qa:
            raise CheckpointMismatchError("QA report does not reconcile with stage outputs")
    _validate_events(checkpoint)


def _validate_events(checkpoint: WorkflowCheckpoint) -> None:
    if [event.sequence for event in checkpoint.events] != list(
        range(1, len(checkpoint.events) + 1)
    ):
        raise CheckpointMismatchError("checkpoint event sequence is invalid")

    cursor = 0
    for record in checkpoint.stages:
        stage_title = record.state.value.replace("_", " ").title()
        retry_count = (
            record.attempt_count - 1
            if record.status == StageStatus.COMPLETED
            else record.attempt_count
        )
        for attempt in range(1, retry_count + 1):
            cursor = _expect_event(
                checkpoint,
                cursor,
                state=record.state,
                title=f"{stage_title} retry",
                detail=f"Transient dry-run failure on attempt {attempt}.",
                status="warning",
            )
        if record.status == StageStatus.COMPLETED:
            if record.output is None:
                raise CheckpointMismatchError("completed event is missing stage output")
            cursor = _expect_event(
                checkpoint,
                cursor,
                state=record.state,
                title=f"{stage_title} completed",
                detail=(
                    f"Accepted {record.output.item_count} metadata items; "
                    f"simulated cost {record.cost_micros} micros."
                ),
                status="complete",
            )
        elif cursor < len(checkpoint.events):
            event = checkpoint.events[cursor]
            if event.title == "Workflow blocked by budget":
                cursor = _expect_event(
                    checkpoint,
                    cursor,
                    state=record.state,
                    title="Workflow blocked by budget",
                    detail=f"The episode budget cannot fund {record.state.value}.",
                    status="warning",
                )
            break

    if checkpoint.state == PipelineState.NEEDS_APPROVAL:
        cursor = _expect_event(
            checkpoint,
            cursor,
            state=PipelineState.NEEDS_APPROVAL,
            title="Ready for owner approval",
            detail="All automated checks passed; publishing remains disabled.",
            status="waiting",
        )
    if cursor != len(checkpoint.events):
        raise CheckpointMismatchError("checkpoint events do not reconcile with stage records")


def _expect_event(
    checkpoint: WorkflowCheckpoint,
    cursor: int,
    *,
    state: PipelineState,
    title: str,
    detail: str,
    status: str,
) -> int:
    if cursor >= len(checkpoint.events):
        raise CheckpointMismatchError("checkpoint is missing an expected event")
    event = checkpoint.events[cursor]
    if (
        event.state != state
        or event.title != title
        or event.detail != detail
        or event.status != status
    ):
        raise CheckpointMismatchError("checkpoint event does not match its stage record")
    return cursor + 1


def run_episode(
    *,
    checkpoint: WorkflowCheckpoint,
    policy: WorkflowPolicy,
    provider: StageProvider,
    stop_after: PipelineState | None = None,
    checkpoint_callback: Callable[[WorkflowCheckpoint], None] | None = None,
) -> WorkflowCheckpoint:
    validate_checkpoint(checkpoint, policy, provider)
    if stop_after is not None:
        stop_index = WORKFLOW_STAGE_ORDER.index(stop_after)
        if checkpoint.stages[stop_index].status == StageStatus.COMPLETED:
            return checkpoint

    input_sha256 = sha256_json(checkpoint.episode.model_dump(mode="json", by_alias=True))

    for index, stage in enumerate(policy.stages):
        record = checkpoint.stages[index]
        if record.status == StageStatus.COMPLETED:
            if record.output is None:
                raise CheckpointMismatchError("completed stage is missing output metadata")
            if record.input_sha256 != input_sha256:
                raise CheckpointMismatchError("completed stage input digest does not match")
            input_sha256 = record.output.sha256
            continue

        if (
            checkpoint.cost.spent_micros + stage.simulated_cost_micros
            > checkpoint.cost.budget_micros
        ):
            already_blocked = bool(
                checkpoint.events
                and checkpoint.events[-1].state == stage.state
                and checkpoint.events[-1].title == "Workflow blocked by budget"
            )
            if not already_blocked:
                checkpoint.events.append(
                    WorkflowEvent(
                        sequence=len(checkpoint.events) + 1,
                        occurred_at=datetime.now(UTC),
                        state=stage.state,
                        title="Workflow blocked by budget",
                        detail=f"The episode budget cannot fund {stage.state.value}.",
                        status="warning",
                    )
                )
                checkpoint.updated_at = datetime.now(UTC)
                checkpoint = WorkflowCheckpoint.model_validate(checkpoint.model_dump())
            if checkpoint_callback is not None:
                checkpoint_callback(checkpoint)
            raise BudgetExceededError(f"budget exhausted before {stage.state.value}", checkpoint)

        first_attempt = record.attempt_count + 1
        if first_attempt > stage.attempt_limit:
            raise WorkflowExecutionError(
                f"attempt limit exhausted for {stage.state.value}", checkpoint
            )

        output = None
        attempt_count = first_attempt
        for attempt_count in range(first_attempt, stage.attempt_limit + 1):
            try:
                output = provider.execute(
                    brief=checkpoint.episode,
                    stage=stage,
                    input_sha256=input_sha256,
                    definition_version=policy.definition_version,
                )
                break
            except TransientProviderError:
                checkpoint.stages[index] = StageRecord(
                    state=stage.state,
                    idempotency_key=record.idempotency_key,
                    attempt_count=attempt_count,
                    attempt_limit=record.attempt_limit,
                    deadline_minutes=record.deadline_minutes,
                )
                checkpoint.events.append(
                    WorkflowEvent(
                        sequence=len(checkpoint.events) + 1,
                        occurred_at=datetime.now(UTC),
                        state=stage.state,
                        title=f"{stage.state.value.replace('_', ' ').title()} retry",
                        detail=f"Transient dry-run failure on attempt {attempt_count}.",
                        status="warning",
                    )
                )
                checkpoint.updated_at = datetime.now(UTC)
                checkpoint = WorkflowCheckpoint.model_validate(checkpoint.model_dump())
                if checkpoint_callback is not None:
                    checkpoint_callback(checkpoint)
        if output is None:
            raise WorkflowExecutionError(
                f"attempt limit exhausted for {stage.state.value}", checkpoint
            )

        checkpoint.stages[index] = StageRecord(
            state=stage.state,
            status=StageStatus.COMPLETED,
            idempotency_key=record.idempotency_key,
            input_sha256=input_sha256,
            attempt_count=attempt_count,
            attempt_limit=record.attempt_limit,
            deadline_minutes=record.deadline_minutes,
            cost_micros=stage.simulated_cost_micros,
            output=output,
        )
        checkpoint.cost.spent_micros += stage.simulated_cost_micros
        checkpoint.events.append(
            WorkflowEvent(
                sequence=len(checkpoint.events) + 1,
                occurred_at=datetime.now(UTC),
                state=stage.state,
                title=f"{stage.state.value.replace('_', ' ').title()} completed",
                detail=(
                    f"Accepted {output.item_count} metadata items; "
                    f"simulated cost {stage.simulated_cost_micros} micros."
                ),
                status="complete",
            )
        )

        input_sha256 = output.sha256
        if index + 1 < len(WORKFLOW_STAGE_ORDER):
            checkpoint.state = WORKFLOW_STAGE_ORDER[index + 1]
        else:
            checkpoint.state = PipelineState.NEEDS_APPROVAL
            checkpoint.final_render_sha256 = _completed_output(
                checkpoint, PipelineState.RENDERING
            ).sha256
            checkpoint.qa_report = _qa_report(checkpoint, stage.validator_count)
            checkpoint.events.append(
                WorkflowEvent(
                    sequence=len(checkpoint.events) + 1,
                    occurred_at=datetime.now(UTC),
                    state=PipelineState.NEEDS_APPROVAL,
                    title="Ready for owner approval",
                    detail="All automated checks passed; publishing remains disabled.",
                    status="waiting",
                )
            )

        checkpoint.updated_at = datetime.now(UTC)
        checkpoint = WorkflowCheckpoint.model_validate(checkpoint.model_dump())
        if checkpoint_callback is not None:
            checkpoint_callback(checkpoint)
        if stop_after == stage.state:
            break

    validate_checkpoint(checkpoint, policy, provider)
    return checkpoint


def _completed_output(checkpoint: WorkflowCheckpoint, state: PipelineState) -> StageOutput:
    record = next(stage for stage in checkpoint.stages if stage.state == state)
    if record.status != StageStatus.COMPLETED or record.output is None:
        raise CheckpointMismatchError(f"required {state.value} output is missing")
    return record.output


def _qa_report(checkpoint: WorkflowCheckpoint, checks_total: int) -> QAReport:
    output_hashes = [stage.output.sha256 for stage in checkpoint.stages if stage.output is not None]
    return QAReport(
        report_sha256=sha256_json(output_hashes),
        checks_total=checks_total,
        checks_passed=checks_total,
        finding_count=0,
        passed=True,
    )


def checkpoint_to_dashboard(checkpoint: WorkflowCheckpoint) -> DashboardSnapshot:
    completed_count = sum(stage.status == StageStatus.COMPLETED for stage in checkpoint.stages)
    progress = round((completed_count / len(checkpoint.stages)) * 100)
    qa = checkpoint.qa_report
    research_items = _stage_item_count(checkpoint, PipelineState.RESEARCHING)
    asset_items = _stage_item_count(checkpoint, PipelineState.ASSET_PREPARATION)
    scenes_complete = _stage_item_count(checkpoint, PipelineState.SCENE_PRODUCTION)
    scheduled = checkpoint.episode.scheduled_for.astimezone(UTC)
    scheduled_for = (
        f"{scheduled.strftime('%A')}, {scheduled.strftime('%I').lstrip('0')}:"
        f"{scheduled.strftime('%M %p')} UTC"
    )

    return DashboardSnapshot(
        generated_at=checkpoint.updated_at,
        mode="demo",
        metrics=[
            Metric(
                label="Workflow stages",
                value=f"{completed_count} / {len(checkpoint.stages)}",
                detail="Resumable checkpoint",
                tone="positive" if checkpoint.state == PipelineState.NEEDS_APPROVAL else "neutral",
            ),
            Metric(
                label="Needs review",
                value="1 episode"
                if checkpoint.state == PipelineState.NEEDS_APPROVAL
                else "0 episodes",
                detail="Owner gate enforced",
                tone="warning" if checkpoint.state == PipelineState.NEEDS_APPROVAL else "neutral",
            ),
            Metric(
                label="Quality gates",
                value=f"{qa.checks_passed} / {qa.checks_total}" if qa else "Pending",
                detail="Dry-run validation",
                tone="positive" if qa and qa.passed else "neutral",
            ),
            Metric(
                label="Simulated spend",
                value=f"${checkpoint.cost.spent_micros / 1_000_000:.2f}",
                detail=f"${checkpoint.cost.budget_micros / 1_000_000:.2f} episode limit",
                tone="neutral",
            ),
        ],
        active_episode=EpisodeSummary(
            id=checkpoint.episode.episode_id,
            title=checkpoint.episode.title,
            objective=checkpoint.episode.objective,
            format=checkpoint.episode.format,
            state=checkpoint.state,
            progress=progress,
            scene_progress=f"{scenes_complete} of {checkpoint.episode.scene_count} scenes",
            cost=f"${checkpoint.cost.spent_micros / 1_000_000:.2f} simulated",
            scheduled_for=scheduled_for,
        ),
        upcoming_episodes=[],
        events=[
            PipelineEvent(
                id=f"evt_{event.sequence}",
                time=event.occurred_at.astimezone(UTC).strftime("%H:%M"),
                title=event.title,
                detail=event.detail,
                status=event.status,
            )
            for event in reversed(checkpoint.events[-5:])
        ],
        library=LibrarySummary(
            sources=research_items,
            reusable_assets=asset_items,
            stale_sources=0,
            missing_rights=0,
            storage="Transient only",
        ),
    )


def _stage_item_count(checkpoint: WorkflowCheckpoint, state: PipelineState) -> int:
    record = next(stage for stage in checkpoint.stages if stage.state == state)
    return record.output.item_count if record.output is not None else 0
