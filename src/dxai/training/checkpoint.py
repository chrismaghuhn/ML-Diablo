from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class CheckpointManifest:
    schema_version: str
    run_id: str
    learner_step: int
    model_class: str
    observation_version: str
    action_version: str
    task_ids: tuple[str, ...]
    upstream_revision: str
    config_sha256: str
    weights_sha256: str
    metrics: dict[str, float]

    def validate(self) -> None:
        if self.schema_version != "dxai.checkpoint.v1":
            raise ValueError("unsupported checkpoint schema")
        required_text = (
            self.run_id,
            self.model_class,
            self.observation_version,
            self.action_version,
            self.upstream_revision,
        )
        if any(not value for value in required_text):
            raise ValueError("checkpoint identifiers must be non-empty")
        if self.learner_step < 0:
            raise ValueError("learner_step must be non-negative")
        if not self.task_ids or len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("task_ids must be non-empty and unique")
        if any(not task_id for task_id in self.task_ids):
            raise ValueError("task_ids must not contain empty values")
        for name, value in (
            ("config_sha256", self.config_sha256),
            ("weights_sha256", self.weights_sha256),
        ):
            if _SHA256_RE.fullmatch(value) is None:
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if any(not key or not math.isfinite(value) for key, value in self.metrics.items()):
            raise ValueError("checkpoint metrics need non-empty keys and finite values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "learner_step": self.learner_step,
            "model_class": self.model_class,
            "observation_version": self.observation_version,
            "action_version": self.action_version,
            "task_ids": list(self.task_ids),
            "upstream_revision": self.upstream_revision,
            "config_sha256": self.config_sha256,
            "weights_sha256": self.weights_sha256,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CheckpointManifest:
        result = cls(
            schema_version=str(value["schema_version"]),
            run_id=str(value["run_id"]),
            learner_step=int(value["learner_step"]),
            model_class=str(value["model_class"]),
            observation_version=str(value["observation_version"]),
            action_version=str(value["action_version"]),
            task_ids=tuple(str(item) for item in value["task_ids"]),
            upstream_revision=str(value["upstream_revision"]),
            config_sha256=str(value["config_sha256"]),
            weights_sha256=str(value["weights_sha256"]),
            metrics={str(key): float(item) for key, item in value.get("metrics", {}).items()},
        )
        result.validate()
        return result
