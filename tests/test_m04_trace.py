from __future__ import annotations

from dxai.env.determinism import canonical_trace_sha256


def _trace(
    *, episode_id: str, request_id: int, position_x: int = 1, engine_tick: int = 0
) -> list[dict[str, object]]:
    return [
        {
            "request_id": request_id,
            "pid": 100 + request_id,
            "episode_id": episode_id,
            "observation": {
                "episode_id": episode_id,
                "seed": 123,
                "step_id": 0,
                "engine_tick": engine_tick,
                "player": {"position": {"x": position_x, "y": 1}},
            },
            "action": {"kind": "MOVE_TO_TILE", "target_tile": {"x": 2, "y": 1}},
        }
    ]


def test_lifecycle_metadata_is_excluded_but_semantic_state_is_not() -> None:
    assert canonical_trace_sha256(_trace(episode_id="episode-a", request_id=1)) == (
        canonical_trace_sha256(_trace(episode_id="episode-b", request_id=900))
    )
    assert canonical_trace_sha256(_trace(episode_id="episode-a", request_id=1, position_x=2)) != (
        canonical_trace_sha256(_trace(episode_id="episode-b", request_id=900, position_x=1))
    )
    assert canonical_trace_sha256(_trace(episode_id="episode-a", request_id=1, engine_tick=1)) != (
        canonical_trace_sha256(_trace(episode_id="episode-b", request_id=900, engine_tick=0))
    )
