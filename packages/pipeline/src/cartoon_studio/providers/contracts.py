from typing import Protocol

from cartoon_studio.domain.workflow_models import EpisodeBrief, StageOutput, StagePolicy


class TransientProviderError(RuntimeError):
    pass


class StageProvider(Protocol):
    def execute(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput: ...

    def verify(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
        output: StageOutput,
    ) -> bool: ...
