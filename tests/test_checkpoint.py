from __future__ import annotations

import pytest

from dxai.training.checkpoint import CheckpointManifest


def test_checkpoint_manifest_serializes() -> None:
    manifest = CheckpointManifest(
        schema_version="dxai.checkpoint.v1",
        run_id="run-1",
        learner_step=123,
        model_class="CandidateQNetwork",
        observation_version="dxai.observation.v1",
        action_version="dxai.action.v1",
        task_ids=("combat.single_melee.v0",),
        upstream_revision="07385842840437cc9a785b195f5b40b121eaeb1c",
        config_sha256="a" * 64,
        weights_sha256="b" * 64,
        metrics={"validation_success": 0.75},
    )
    manifest.validate()
    value = manifest.to_dict()
    assert value["learner_step"] == 123
    assert value["task_ids"] == ["combat.single_melee.v0"]
    assert CheckpointManifest.from_dict(value) == manifest


def test_checkpoint_manifest_rejects_non_finite_metrics() -> None:
    manifest = CheckpointManifest(
        schema_version="dxai.checkpoint.v1",
        run_id="run-1",
        learner_step=0,
        model_class="CandidateQNetwork",
        observation_version="dxai.observation.v1",
        action_version="dxai.action.v1",
        task_ids=("combat.single_melee.v0",),
        upstream_revision="0738584",
        config_sha256="a" * 64,
        weights_sha256="b" * 64,
        metrics={"loss": float("nan")},
    )
    with pytest.raises(ValueError, match="finite"):
        manifest.validate()
