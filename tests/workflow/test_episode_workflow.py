from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cartoon_studio.domain.api_models import PipelineState
from cartoon_studio.domain.workflow_models import (
    WORKFLOW_STAGE_ORDER,
    EpisodeBrief,
    StageOutput,
    StagePolicy,
    StageStatus,
    WorkflowCheckpoint,
    WorkflowPolicy,
    assert_public_safe,
)
from cartoon_studio.providers.contracts import TransientProviderError
from cartoon_studio.providers.dry_run import DryRunProvider
from cartoon_studio.workflows.episode import (
    BudgetExceededError,
    CheckpointMismatchError,
    WorkflowExecutionError,
    checkpoint_to_dashboard,
    create_checkpoint,
    load_brief,
    load_policy,
    run_episode,
)

ROOT = Path(__file__).parents[2]


@pytest.fixture
def brief() -> EpisodeBrief:
    return load_brief(ROOT / "config/episodes/letter-b.json")


@pytest.fixture
def policy() -> WorkflowPolicy:
    return load_policy(ROOT / "config/workflows/dry-run-v1.json")


def new_checkpoint(brief: EpisodeBrief, policy: WorkflowPolicy, budget: int = 10_000_000):
    return create_checkpoint(
        brief=brief,
        policy=policy,
        workflow_run_id="test-run",
        budget_micros=budget,
    )


def test_full_workflow_stops_for_owner_approval(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    checkpoint = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=DryRunProvider(),
    )

    assert checkpoint.state == PipelineState.NEEDS_APPROVAL
    assert all(stage.status == StageStatus.COMPLETED for stage in checkpoint.stages)
    assert [stage.state for stage in checkpoint.stages] == list(WORKFLOW_STAGE_ORDER)
    assert checkpoint.qa_report is not None and checkpoint.qa_report.passed
    assert checkpoint.final_render_sha256 is not None
    assert checkpoint.publishing_enabled is False
    assert checkpoint.cost.spent_micros == 5_150_000
    assert checkpoint.cost.reserved_micros == 0
    assert checkpoint.events[-1].status == "waiting"
    assert_public_safe(checkpoint)

    dashboard = checkpoint_to_dashboard(checkpoint)
    assert dashboard.active_episode.progress == 100
    assert dashboard.active_episode.scene_progress == "12 of 12 scenes"
    assert dashboard.active_episode.state == PipelineState.NEEDS_APPROVAL
    assert dashboard.library.storage == "Transient only"
    assert_public_safe(dashboard)


def test_resume_skips_completed_idempotent_stages(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    partial = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=DryRunProvider(),
        stop_after=PipelineState.STORYBOARDING,
    )
    completed_before = [
        stage.model_dump() for stage in partial.stages if stage.status == StageStatus.COMPLETED
    ]
    resumed = WorkflowCheckpoint.model_validate_json(partial.model_dump_json(by_alias=True))

    completed = run_episode(checkpoint=resumed, policy=policy, provider=DryRunProvider())

    assert [stage.model_dump() for stage in completed.stages[:5]] == completed_before
    assert all(stage.attempt_count == 1 for stage in completed.stages)
    rerun = run_episode(
        checkpoint=completed.model_copy(deep=True),
        policy=policy,
        provider=DryRunProvider(),
    )
    assert rerun == completed


def test_resume_rejects_tampered_digest(brief: EpisodeBrief, policy: WorkflowPolicy) -> None:
    partial = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=DryRunProvider(),
        stop_after=PipelineState.SCRIPTING,
    )
    payload = partial.model_dump()
    payload["stages"][0]["output"]["sha256"] = "0" * 64
    tampered = WorkflowCheckpoint.model_validate(payload)

    with pytest.raises(CheckpointMismatchError, match="output"):
        run_episode(checkpoint=tampered, policy=policy, provider=DryRunProvider())


@pytest.mark.parametrize("field", ["attempts", "cost", "idempotency", "final_render"])
def test_resume_reconciles_checkpoint_integrity(
    field: str, brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    completed = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=DryRunProvider(),
    )
    payload = completed.model_dump()
    if field == "attempts":
        payload["stages"][0]["attempt_count"] = 2
    elif field == "cost":
        payload["cost"]["spent_micros"] -= 1
    elif field == "idempotency":
        payload["stages"][0]["idempotency_key"] = "0" * 64
    else:
        payload["final_render_sha256"] = "0" * 64
    tampered = WorkflowCheckpoint.model_validate(payload)

    with pytest.raises(CheckpointMismatchError):
        run_episode(checkpoint=tampered, policy=policy, provider=DryRunProvider())


def test_budget_blocks_before_overspend(brief: EpisodeBrief, policy: WorkflowPolicy) -> None:
    checkpoint = new_checkpoint(brief, policy, budget=100_000)

    with pytest.raises(BudgetExceededError, match="researching") as first_block:
        run_episode(checkpoint=checkpoint, policy=policy, provider=DryRunProvider())

    checkpoint = first_block.value.checkpoint
    assert checkpoint.state == PipelineState.RESEARCHING
    assert checkpoint.cost.spent_micros == 100_000
    assert checkpoint.stages[0].status == StageStatus.COMPLETED
    assert checkpoint.stages[1].status == StageStatus.PENDING
    event_count = len(checkpoint.events)

    with pytest.raises(BudgetExceededError, match="researching") as second_block:
        run_episode(checkpoint=checkpoint, policy=policy, provider=DryRunProvider())

    assert len(second_block.value.checkpoint.events) == event_count


class FailPlanningOnceProvider(DryRunProvider):
    def __init__(self) -> None:
        self.failed = False

    def execute(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput:
        if stage.state == PipelineState.PLANNING and not self.failed:
            self.failed = True
            raise TransientProviderError("simulated timeout")
        return super().execute(
            brief=brief,
            stage=stage,
            input_sha256=input_sha256,
            definition_version=definition_version,
        )


def test_transient_provider_failure_retries_within_limit(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    checkpoint = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=FailPlanningOnceProvider(),
    )

    assert checkpoint.stages[0].attempt_count == 2
    assert any(event.status == "warning" for event in checkpoint.events)
    assert checkpoint.state == PipelineState.NEEDS_APPROVAL


class AlwaysFailProvider(DryRunProvider):
    def execute(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput:
        raise TransientProviderError("simulated outage")


class CrashDuringScriptingProvider(DryRunProvider):
    def execute(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput:
        if stage.state == PipelineState.SCRIPTING:
            raise RuntimeError("simulated process crash")
        return super().execute(
            brief=brief,
            stage=stage,
            input_sha256=input_sha256,
            definition_version=definition_version,
        )


def test_exhausted_retries_return_a_resumable_checkpoint(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    with pytest.raises(WorkflowExecutionError) as captured:
        run_episode(
            checkpoint=new_checkpoint(brief, policy),
            policy=policy,
            provider=AlwaysFailProvider(),
        )

    checkpoint = captured.value.checkpoint
    assert checkpoint.state == PipelineState.PLANNING
    assert checkpoint.stages[0].attempt_count == 2
    assert checkpoint.stages[0].status == StageStatus.PENDING
    assert len(checkpoint.events) == 2


def test_checkpoint_callback_preserves_progress_before_unexpected_failure(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    persisted: list[WorkflowCheckpoint] = []

    with pytest.raises(RuntimeError, match="process crash"):
        run_episode(
            checkpoint=new_checkpoint(brief, policy),
            policy=policy,
            provider=CrashDuringScriptingProvider(),
            checkpoint_callback=lambda checkpoint: persisted.append(
                checkpoint.model_copy(deep=True)
            ),
        )

    assert persisted[-1].state == PipelineState.SCRIPTING
    assert persisted[-1].stages[0].status == StageStatus.COMPLETED
    assert persisted[-1].stages[1].status == StageStatus.COMPLETED
    assert persisted[-1].stages[2].status == StageStatus.PENDING


def test_stop_after_completed_stage_does_not_advance(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    partial = run_episode(
        checkpoint=new_checkpoint(brief, policy),
        policy=policy,
        provider=DryRunProvider(),
        stop_after=PipelineState.STORYBOARDING,
    )

    unchanged = run_episode(
        checkpoint=partial.model_copy(deep=True),
        policy=policy,
        provider=DryRunProvider(),
        stop_after=PipelineState.PLANNING,
    )

    assert unchanged == partial


def test_episode_brief_requires_timezone() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        EpisodeBrief(
            episode_id="ep_naive",
            title="Naive timestamp",
            objective="Reject timestamps without an explicit timezone.",
            format="Test",
            scheduled_for=datetime(2026, 9, 7, 9),
            target_duration_seconds=60,
            scene_count=1,
        )


@pytest.mark.parametrize(
    "unsafe",
    [
        {"providerToken": "value"},
        {"report": "/home/runner/work/private.mov"},
        {"prompt": "hidden instructions"},
    ],
)
def test_public_output_rejects_sensitive_data(unsafe: object) -> None:
    with pytest.raises(ValueError, match="public output"):
        assert_public_safe(unsafe)


def test_public_output_rejects_secret_markers_in_free_text(
    brief: EpisodeBrief, policy: WorkflowPolicy
) -> None:
    unsafe_brief = brief.model_copy(update={"objective": "authorization: bearer github_pat_secret"})
    checkpoint = new_checkpoint(unsafe_brief, policy)

    with pytest.raises(ValueError, match="private value"):
        assert_public_safe(checkpoint)
