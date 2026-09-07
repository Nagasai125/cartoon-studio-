import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from cartoon_studio.domain.api_models import PipelineState
from cartoon_studio.domain.workflow_models import (
    WORKFLOW_STAGE_ORDER,
    WorkflowCheckpoint,
    assert_public_safe,
)
from cartoon_studio.providers.dry_run import DryRunProvider
from cartoon_studio.workflows.episode import (
    WorkflowExecutionError,
    checkpoint_to_dashboard,
    create_checkpoint,
    load_brief,
    load_policy,
    run_episode,
    validate_checkpoint,
)


def _write_public_json(path: Path, value: BaseModel) -> None:
    assert_public_safe(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(value.model_dump_json(by_alias=True, indent=2) + "\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the resumable dry-run episode workflow")
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--checkpoint-in", type=Path)
    parser.add_argument("--checkpoint-out", required=True, type=Path)
    parser.add_argument("--dashboard-out", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--budget-micros", default=10_000_000, type=int)
    parser.add_argument("--stop-after", choices=[state.value for state in WORKFLOW_STAGE_ORDER])
    args = parser.parse_args()

    brief_path = cast(Path, args.brief)
    policy_path = cast(Path, args.policy)
    checkpoint_in = cast(Path | None, args.checkpoint_in)
    checkpoint_out = cast(Path, args.checkpoint_out)
    dashboard_out = cast(Path, args.dashboard_out)
    run_id = cast(str | None, args.run_id)
    budget_micros = cast(int, args.budget_micros)
    stop_after_value = cast(str | None, args.stop_after)
    if budget_micros <= 0:
        parser.error("--budget-micros must be greater than zero")

    brief = load_brief(brief_path)
    policy = load_policy(policy_path)
    if checkpoint_in is not None:
        checkpoint_bytes = checkpoint_in.read_bytes()
        checkpoint = WorkflowCheckpoint.model_validate_json(checkpoint_bytes)
        if checkpoint.episode != brief:
            parser.error("checkpoint episode does not match the selected brief")
        if budget_micros > checkpoint.cost.budget_micros:
            parser.error("a resumed workflow cannot increase its episode budget")
        if budget_micros < checkpoint.cost.spent_micros:
            parser.error("resume budget cannot be lower than recorded spend")
        checkpoint.cost = checkpoint.cost.model_copy(update={"budget_micros": budget_micros})
        checkpoint.parent_checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    else:
        if run_id is None:
            parser.error("--run-id is required for a new workflow")
        checkpoint = create_checkpoint(
            brief=brief,
            policy=policy,
            workflow_run_id=run_id,
            budget_micros=budget_micros,
        )

    stop_after = PipelineState(stop_after_value) if stop_after_value else None
    provider = DryRunProvider()
    validate_checkpoint(checkpoint, policy, provider)

    def persist(current: WorkflowCheckpoint) -> None:
        _write_public_json(checkpoint_out, current)
        _write_public_json(dashboard_out, checkpoint_to_dashboard(current))

    persist(checkpoint)
    try:
        checkpoint = run_episode(
            checkpoint=checkpoint,
            policy=policy,
            provider=provider,
            stop_after=stop_after,
            checkpoint_callback=persist,
        )
    except WorkflowExecutionError as error:
        checkpoint = error.checkpoint
        persist(checkpoint)
        raise
    persist(checkpoint)


if __name__ == "__main__":
    main()
