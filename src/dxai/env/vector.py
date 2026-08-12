from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from dxai.contracts.observations import Observation
from dxai.env.client import DevilutionXEnvironment
from dxai.protocol.lifecycle import HealthResponse, PersistentStepResponse


class _EnvironmentSlot(Protocol):
    @property
    def observation(self) -> Observation | None: ...

    @property
    def worker_pid(self) -> int | None: ...

    @property
    def runtime_root(self) -> Path | None: ...

    @property
    def last_worker_startup_ns(self) -> int | None: ...

    def reset(self, *, seed: int, task_id: str) -> Observation: ...

    def step(self, candidate_id: int) -> PersistentStepResponse: ...

    def health_check(self) -> HealthResponse: ...

    def close(self) -> None: ...


class VectorEnvironmentError(RuntimeError):
    def __init__(
        self,
        slot_index: int,
        cause: BaseException,
        *,
        cleanup_error: VectorEnvironmentCloseError | None = None,
    ) -> None:
        self.slot_index = slot_index
        self.cause = cause
        self.cleanup_error = cleanup_error
        suffix = ""
        if cleanup_error is not None:
            suffix = f"; cleanup also failed: {cleanup_error}"
        super().__init__(f"vector environment slot {slot_index} failed: {cause}{suffix}")


class VectorEnvironmentCloseError(RuntimeError):
    def __init__(self, errors: tuple[tuple[int, BaseException], ...]) -> None:
        self.errors = errors
        details = "; ".join(f"slot {index}: {cause}" for index, cause in errors)
        super().__init__(f"vector environment cleanup failed: {details}")


class VectorDevilutionXEnvironment:
    """Synchronous process-isolated composition of existing M0.4 environments."""

    def __init__(
        self,
        num_envs: int,
        *,
        environment_factory: Callable[[int], _EnvironmentSlot] | None = None,
        executable: Path | None = None,
        assets_path: Path | None = None,
        core_assets_path: Path | None = None,
        engine_runtime_path: Path | None = None,
        runtime_root: Path | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        if isinstance(num_envs, bool) or num_envs <= 0:
            raise ValueError("num_envs must be positive")
        self._closed = False
        self._owned_runtime_root: Path | None = None
        slots: list[_EnvironmentSlot] = []
        try:
            if environment_factory is not None:
                slots = [environment_factory(index) for index in range(num_envs)]
            else:
                if executable is None or assets_path is None or core_assets_path is None:
                    raise ValueError(
                        "executable, assets_path, and core_assets_path are required "
                        "without environment_factory"
                    )
                base_root = runtime_root
                if base_root is None:
                    base_root = Path(tempfile.mkdtemp(prefix="dxai-m05-vector-"))
                    self._owned_runtime_root = base_root
                for index in range(num_envs):
                    slots.append(
                        DevilutionXEnvironment(
                            executable=executable,
                            assets_path=assets_path,
                            core_assets_path=core_assets_path,
                            engine_runtime_path=engine_runtime_path,
                            runtime_root=base_root / f"env-{index}",
                            timeout_seconds=timeout_seconds,
                        )
                    )
        except Exception:
            for slot in slots:
                try:
                    slot.close()
                except Exception:
                    continue
            self._cleanup_owned_runtime_root()
            raise
        self._environments = tuple(slots)

    @property
    def environments(self) -> tuple[_EnvironmentSlot, ...]:
        return self._environments

    @property
    def worker_pids(self) -> tuple[int | None, ...]:
        return tuple(slot.worker_pid for slot in self._environments)

    @property
    def runtime_roots(self) -> tuple[Path | None, ...]:
        return tuple(slot.runtime_root for slot in self._environments)

    def reset_many(self, seeds: Sequence[int], task_id: str) -> tuple[Observation, ...]:
        self._ensure_open()
        self._validate_batch(seeds, "seeds")
        observations: list[Observation] = []
        for index, (slot, seed) in enumerate(zip(self._environments, seeds, strict=True)):
            try:
                observations.append(slot.reset(seed=seed, task_id=task_id))
            except Exception as error:
                cleanup_error = self._close_after_failure()
                raise VectorEnvironmentError(
                    index,
                    error,
                    cleanup_error=cleanup_error,
                ) from error
        return tuple(observations)

    def step_many(self, candidate_ids: Sequence[int]) -> tuple[PersistentStepResponse, ...]:
        self._ensure_open()
        self._validate_batch(candidate_ids, "candidate_ids")
        responses: list[PersistentStepResponse] = []
        for index, (slot, candidate_id) in enumerate(
            zip(self._environments, candidate_ids, strict=True)
        ):
            try:
                responses.append(slot.step(candidate_id))
            except Exception as error:
                cleanup_error = self._close_after_failure()
                raise VectorEnvironmentError(
                    index,
                    error,
                    cleanup_error=cleanup_error,
                ) from error
        return tuple(responses)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        errors: list[tuple[int, BaseException]] = []
        for index, slot in enumerate(self._environments):
            try:
                slot.close()
            except Exception as error:
                errors.append((index, error))
        try:
            self._cleanup_owned_runtime_root()
        except Exception as error:
            errors.append((-1, error))
        if errors:
            raise VectorEnvironmentCloseError(tuple(errors))

    def __enter__(self) -> VectorDevilutionXEnvironment:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _validate_batch(self, values: Sequence[object], name: str) -> None:
        if len(values) != len(self._environments):
            raise ValueError(f"{name} must contain exactly {len(self._environments)} values")

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("vector environment is closed")

    def _close_after_failure(self) -> VectorEnvironmentCloseError | None:
        try:
            self.close()
        except VectorEnvironmentCloseError as error:
            return error
        return None

    def _cleanup_owned_runtime_root(self) -> None:
        root = self._owned_runtime_root
        self._owned_runtime_root = None
        if root is not None:
            shutil.rmtree(root)
