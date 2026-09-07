import sys
from pathlib import Path

import pytest

from cartoon_studio.domain.api_models import DashboardSnapshot, PipelineState
from cartoon_studio.domain.workflow_models import WorkflowCheckpoint
from cartoon_studio.workflows.episode import BudgetExceededError
from cartoon_studio.workflows.run_episode import main

ROOT = Path(__file__).parents[2]


def test_cli_persists_checkpoint_when_budget_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint.json"
    dashboard_path = tmp_path / "dashboard.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_episode",
            "--brief",
            str(ROOT / "config/episodes/letter-b.json"),
            "--policy",
            str(ROOT / "config/workflows/dry-run-v1.json"),
            "--checkpoint-out",
            str(checkpoint_path),
            "--dashboard-out",
            str(dashboard_path),
            "--run-id",
            "budget-test",
            "--budget-micros",
            "100000",
        ],
    )

    with pytest.raises(BudgetExceededError):
        main()

    checkpoint = WorkflowCheckpoint.model_validate_json(checkpoint_path.read_bytes())
    dashboard = DashboardSnapshot.model_validate_json(dashboard_path.read_bytes())
    assert checkpoint.state == PipelineState.RESEARCHING
    assert checkpoint.cost.spent_micros == 100_000
    assert checkpoint.events[-1].status == "warning"
    assert dashboard.active_episode.state == PipelineState.RESEARCHING


def test_cli_rejects_zero_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_episode",
            "--brief",
            str(ROOT / "config/episodes/letter-b.json"),
            "--policy",
            str(ROOT / "config/workflows/dry-run-v1.json"),
            "--checkpoint-out",
            str(tmp_path / "checkpoint.json"),
            "--dashboard-out",
            str(tmp_path / "dashboard.json"),
            "--run-id",
            "zero-budget-test",
            "--budget-micros",
            "0",
        ],
    )

    with pytest.raises(SystemExit):
        main()
    assert not (tmp_path / "checkpoint.json").exists()
