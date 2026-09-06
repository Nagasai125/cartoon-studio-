import argparse
from pathlib import Path
from typing import cast

from cartoon_studio.domain.api_models import DashboardSnapshot
from cartoon_studio.workflows.demo import DemoStudio


def export_snapshot(output: Path, steps: int = 0) -> DashboardSnapshot:
    if steps < 0:
        raise ValueError("steps must be zero or greater")

    studio = DemoStudio(mode="demo")
    snapshot = studio.snapshot()
    for _ in range(steps):
        snapshot = studio.advance()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        snapshot.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Export public-safe dashboard data")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--steps", default=0, type=int)
    args = parser.parse_args()

    output = cast(Path, args.output)
    steps = cast(int, args.steps)
    export_snapshot(output=output, steps=steps)


if __name__ == "__main__":
    main()
