import json
from pathlib import Path

from cartoon_studio.domain.api_models import DashboardSnapshot, PipelineState
from cartoon_studio.workflows.export_snapshot import export_snapshot


def test_export_snapshot_writes_camel_case_contract(tmp_path: Path) -> None:
    output = tmp_path / "data" / "dashboard.json"

    snapshot = export_snapshot(output=output, steps=5)
    payload = json.loads(output.read_text(encoding="utf-8"))
    validated = DashboardSnapshot.model_validate(payload)

    assert snapshot.mode == "demo"
    assert validated.active_episode.state == PipelineState.NEEDS_APPROVAL
    assert "generatedAt" in payload
    assert "activeEpisode" in payload
    assert "upcomingEpisodes" in payload
    assert "reusableAssets" in payload["library"]
