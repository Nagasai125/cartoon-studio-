from datetime import UTC, datetime
from threading import Lock
from typing import Literal

from cartoon_studio.domain.api_models import (
    DashboardSnapshot,
    EpisodeSummary,
    LibrarySummary,
    Metric,
    PipelineEvent,
    PipelineState,
)

DEMO_STATES = [
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
    PipelineState.NEEDS_APPROVAL,
]


class DemoStudio:
    def __init__(self, mode: Literal["live", "demo"] = "live") -> None:
        self.mode: Literal["live", "demo"] = mode
        self.state_index = 6
        self._lock = Lock()
        self.events: list[PipelineEvent] = [
            PipelineEvent(
                id="evt_5",
                time="10:17",
                title="Scene 8 started",
                detail="Illustration and voice timing submitted.",
                status="active",
            ),
            PipelineEvent(
                id="evt_4",
                time="10:14",
                title="Scene 7 repaired",
                detail="Character palette check now passes.",
                status="complete",
            ),
            PipelineEvent(
                id="evt_3",
                time="10:08",
                title="Scene 7 flagged",
                detail="Sleeve color drifted from the character bible.",
                status="warning",
            ),
            PipelineEvent(
                id="evt_2",
                time="09:56",
                title="Storyboard approved automatically",
                detail="Narrative, pacing, and interaction checks passed.",
                status="complete",
            ),
            PipelineEvent(
                id="evt_1",
                time="09:42",
                title="Sources locked",
                detail="Four source snapshots attached to this version.",
                status="complete",
            ),
        ]

    def snapshot(self) -> DashboardSnapshot:
        state = DEMO_STATES[self.state_index]
        progress = round(((self.state_index + 1) / len(DEMO_STATES)) * 100)
        return DashboardSnapshot(
            generated_at=datetime.now(UTC),
            mode=self.mode,
            metrics=[
                Metric(
                    label="This week",
                    value="3 episodes",
                    detail="1 active, 2 queued",
                    tone="neutral",
                ),
                Metric(
                    label="Needs review",
                    value="1 episode" if state == PipelineState.NEEDS_APPROVAL else "0 episodes",
                    detail=(
                        "Final QA passed"
                        if state == PipelineState.NEEDS_APPROVAL
                        else "No episodes waiting"
                    ),
                    tone="warning" if state == PipelineState.NEEDS_APPROVAL else "neutral",
                ),
                Metric(
                    label="Quality gates",
                    value="24 / 25",
                    detail="One audio warning",
                    tone="positive",
                ),
                Metric(
                    label="Monthly spend",
                    value="$42.18",
                    detail="Budget not configured",
                    tone="neutral",
                ),
            ],
            active_episode=EpisodeSummary(
                id="ep_letter_b",
                title="The Busy Letter B",
                objective=("Recognize the B sound and identify three words that begin with B."),
                format="Story with song",
                state=state,
                progress=progress,
                scene_progress="8 of 12 scenes",
                cost="$8.42",
                scheduled_for="Monday, 9:00 AM",
            ),
            upcoming_episodes=[
                EpisodeSummary(
                    id="ep_brushing",
                    title="Mina Brushes Bright",
                    objective=("Practice the sequence of brushing teeth with caregiver support."),
                    format="Daily routine",
                    state=PipelineState.QUEUED,
                    progress=0,
                    scene_progress="Not started",
                    cost="$0.00",
                    scheduled_for="Wednesday, 9:00 AM",
                ),
                EpisodeSummary(
                    id="ep_shapes",
                    title="Shapes at the Park",
                    objective="Find circles, squares, and triangles in familiar places.",
                    format="Interactive story",
                    state=PipelineState.QUEUED,
                    progress=0,
                    scene_progress="Not started",
                    cost="$0.00",
                    scheduled_for="Friday, 9:00 AM",
                ),
            ],
            events=self.events[:5],
            library=LibrarySummary(
                sources=128,
                reusable_assets=642,
                stale_sources=3,
                missing_rights=0,
                storage="18.4 GB",
            ),
        )

    def advance(self) -> DashboardSnapshot:
        with self._lock:
            if self.state_index < len(DEMO_STATES) - 1:
                self.state_index += 1
            state = DEMO_STATES[self.state_index]
            now = datetime.now().astimezone()
            self.events.insert(
                0,
                PipelineEvent(
                    id=f"evt_{now.timestamp()}",
                    time=now.strftime("%H:%M"),
                    title=f"Advanced to {state.value.replace('_', ' ')}",
                    detail="Manual simulation command completed successfully.",
                    status="active" if state != PipelineState.NEEDS_APPROVAL else "waiting",
                ),
            )
            return self.snapshot()


demo_studio = DemoStudio()
