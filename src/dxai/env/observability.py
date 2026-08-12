from __future__ import annotations

from dxai.contracts.actions import ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import Observation, TileCell


def validate_observable_move_candidates(observation: Observation) -> None:
    """Audit the observation projection of the restricted native move slice.

    This does not decide legality. DevilutionX remains the legality authority. It
    only verifies that a native candidate can be explained by fields already
    exposed in ``dxai.observation.v1``.
    """

    tiles = {tile.relative: tile for tile in observation.local_tiles}
    for action in observation.legal_actions:
        if action.kind is not ActionKind.MOVE_TO_TILE:
            raise ValueError("M0.3 exposes only MOVE_TO_TILE candidates")
        if action.target_tile is None:
            raise ValueError("MOVE_TO_TILE requires target_tile")
        relative = Vec2(
            action.target_tile.x - observation.player.position.x,
            action.target_tile.y - observation.player.position.y,
        )
        if max(abs(relative.x), abs(relative.y)) != 1:
            raise ValueError("M0.3 move candidates must be adjacent")
        _require_observable_open(tiles, relative)

        # DevilutionX CanStep inspects the two corner terrain tiles for cardinal
        # steps. Requiring the same tiles to be visible and open prevents that
        # native check from becoming a hidden-information candidate filter.
        for corner in _native_corner_tiles(relative):
            _require_observable_open(tiles, corner)


def _native_corner_tiles(relative: Vec2) -> tuple[Vec2, ...]:
    if relative.x == 0 and relative.y in (-1, 1):
        return (Vec2(-1, relative.y), Vec2(1, relative.y))
    if relative.y == 0 and relative.x in (-1, 1):
        return (Vec2(relative.x, -1), Vec2(relative.x, 1))
    return ()


def _require_observable_open(tiles: dict[Vec2, TileCell], relative: Vec2) -> None:
    tile = tiles.get(relative)
    if tile is None:
        raise ValueError(f"candidate depends on an unobserved tile: {relative}")
    if not tile.visible or not tile.explored:
        raise ValueError(f"candidate depends on a non-visible tile: {relative}")
    if not tile.walkable or tile.occupied:
        raise ValueError(f"candidate depends on a blocked or occupied tile: {relative}")
