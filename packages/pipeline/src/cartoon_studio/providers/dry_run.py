import hashlib
import json

from cartoon_studio.domain.workflow_models import EpisodeBrief, StageOutput, StagePolicy


class DryRunProvider:
    def _expected_output(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput:
        material = {
            "brief": brief.model_dump(mode="json", by_alias=True),
            "definitionVersion": definition_version,
            "inputSha256": input_sha256,
            "state": stage.state.value,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return StageOutput(
            sha256=digest,
            item_count=stage.output_items,
            duration_seconds=stage.output_duration_seconds,
            validator_count=stage.validator_count,
        )

    def execute(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
    ) -> StageOutput:
        return self._expected_output(
            brief=brief,
            stage=stage,
            input_sha256=input_sha256,
            definition_version=definition_version,
        )

    def verify(
        self,
        *,
        brief: EpisodeBrief,
        stage: StagePolicy,
        input_sha256: str,
        definition_version: str,
        output: StageOutput,
    ) -> bool:
        return output == self._expected_output(
            brief=brief,
            stage=stage,
            input_sha256=input_sha256,
            definition_version=definition_version,
        )
