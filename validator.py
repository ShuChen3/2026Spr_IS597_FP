from typing import Dict, List, Optional, Tuple
from Basic_env_rules import Tile, TileType, TileColor, Meld, MeldType


STANDARD_COLORS = [
    TileColor.RED,
    TileColor.BLUE,
    TileColor.YELLOW,
    TileColor.BLACK,
]



# Basic helpers

def _color_name(color: Optional[TileColor]) -> str:
    return color.value if color is not None else "Unknown"


def _tile_matches_requirement(tile: Tile, required_value: int, required_color: TileColor) -> bool:
    """
    Check whether one non-RK tile can fill one required run position.
    RK is handled separately.
    """
    if tile.tile_type == TileType.NORMAL:
        return tile.value == required_value and tile.color == required_color

    if tile.tile_type == TileType.STANDARD_JOKER:
        return True

    if tile.tile_type == TileType.PRISM_JOKER:
        return tile.prism_color == required_color

    return False


def _assign_tiles_to_requirements(tiles: List[Tile],requirements: List[Tuple[int, TileColor]]) -> Optional[Dict[int, Tuple[int, TileColor]]]:
    """
    Backtracking assignment.

    Returns:
        {tile.uid: (assigned_value, assigned_color)}
        or None if impossible.
    """
    if len(tiles) != len(requirements):
        return None

    used = [False] * len(tiles)
    assignment: Dict[int, Tuple[int, TileColor]] = {}

    def backtrack(req_idx: int) -> bool:
        if req_idx == len(requirements):
            return True

        required_value, required_color = requirements[req_idx]

        for i, tile in enumerate(tiles):
            if used[i]:
                continue

            if not _tile_matches_requirement(tile, required_value, required_color):
                continue

            used[i] = True
            assignment[tile.uid] = (required_value, required_color)

            if backtrack(req_idx + 1):
                return True

            used[i] = False
            assignment.pop(tile.uid, None)

        return False

    return assignment if backtrack(0) else None


def _format_assignment_item(tile: Tile,assigned_value: int,assigned_color: Optional[TileColor] = None) -> str:
    """
    Unified display for normal and special tiles.
    """
    if tile.tile_type == TileType.NORMAL:
        return tile.short_label()

    if tile.tile_type == TileType.RAINBOW_KING:
        return f"RK={assigned_value}"

    if tile.tile_type == TileType.STANDARD_JOKER:
        return f"J={_color_name(assigned_color)}{assigned_value}"

    if tile.tile_type == TileType.PRISM_JOKER:
        prism_color = _color_name(tile.prism_color)
        return f"PJ-{prism_color}={_color_name(assigned_color)}{assigned_value}"

    return tile.short_label()


def _preferred_run_starts(tiles: List[Tile], n: int) -> List[int]:
    """
    Return possible run starts with pruning.

    If normal tiles exist, every normal value must fit inside:
        start <= value <= start + n - 1
    """
    valid_min = 1
    valid_max = 13 - n + 1

    normal_values = sorted(
        tile.value
        for tile in tiles
        if tile.tile_type == TileType.NORMAL and tile.value is not None
    )

    if not normal_values:
        return list(range(valid_min, valid_max + 1))

    lower = max(valid_min, max(normal_values) - n + 1)
    upper = min(valid_max, min(normal_values))

    if lower > upper:
        return []

    candidate_starts = list(range(lower, upper + 1))
    anchor = min(normal_values)

    return sorted(candidate_starts, key=lambda start: abs(start - anchor))



# Run validation / explanation

def _find_run_assignment(tiles: List[Tile]) -> Optional[List[str]]:
    """
    Validate and explain a run in one pass.

    Returns:
        A list of display strings in final run order,
        or None if the tiles cannot form a legal run.
    """
    n = len(tiles)

    if n < 3 or n > 13:
        return None

    rk_tiles = [tile for tile in tiles if tile.tile_type == TileType.RAINBOW_KING]

    if len(rk_tiles) > 1:
        return None


    # no RK, single-color run

    if len(rk_tiles) == 0:
        normal_colors = {
            tile.color
            for tile in tiles
            if tile.tile_type == TileType.NORMAL
        }

        prism_colors = {
            tile.prism_color
            for tile in tiles
            if tile.tile_type == TileType.PRISM_JOKER
        }

        if len(normal_colors) > 1:
            return None

        if len(prism_colors) > 1:
            return None

        if normal_colors and prism_colors:
            if next(iter(normal_colors)) != next(iter(prism_colors)):
                return None

        if normal_colors:
            possible_colors = [next(iter(normal_colors))]
        elif prism_colors:
            possible_colors = [next(iter(prism_colors))]
        else:
            possible_colors = STANDARD_COLORS

        for target_color in possible_colors:
            if target_color is None:
                continue

            for start in _preferred_run_starts(tiles, n):
                requirements = [
                    (value, target_color)
                    for value in range(start, start + n)
                ]

                assignment = _assign_tiles_to_requirements(tiles, requirements)
                if assignment is None:
                    continue

                pos_to_tile: Dict[Tuple[int, TileColor], Tile] = {}
                for tile in tiles:
                    assigned_value, assigned_color = assignment[tile.uid]
                    pos_to_tile[(assigned_value, assigned_color)] = tile

                result = []
                for value in range(start, start + n):
                    tile = pos_to_tile[(value, target_color)]
                    result.append(
                        _format_assignment_item(
                            tile=tile,
                            assigned_value=value,
                            assigned_color=target_color,
                        )
                    )

                return result

        return None


    # exactly one RK

    rk_tile = rk_tiles[0]
    other_tiles = [tile for tile in tiles if tile.uid != rk_tile.uid]

    for start in _preferred_run_starts(tiles, n):
        for rk_pos in range(1, n - 1):
            rk_value = start + rk_pos

            for left_color in STANDARD_COLORS:
                for right_color in STANDARD_COLORS:
                    if left_color == right_color:
                        continue

                    requirements: List[Tuple[int, TileColor]] = []

                    for pos in range(0, rk_pos):
                        value = start + pos
                        requirements.append((value, left_color))

                    for pos in range(rk_pos + 1, n):
                        value = start + pos
                        requirements.append((value, right_color))

                    assignment = _assign_tiles_to_requirements(other_tiles, requirements)
                    if assignment is None:
                        continue

                    pos_to_tile: Dict[Tuple[int, TileColor], Tile] = {}
                    for tile in other_tiles:
                        assigned_value, assigned_color = assignment[tile.uid]
                        pos_to_tile[(assigned_value, assigned_color)] = tile

                    result = []

                    for pos in range(n):
                        value = start + pos

                        if pos < rk_pos:
                            color = left_color
                            tile = pos_to_tile[(value, color)]
                            result.append(
                                _format_assignment_item(
                                    tile=tile,
                                    assigned_value=value,
                                    assigned_color=color,
                                )
                            )

                        elif pos == rk_pos:
                            result.append(
                                _format_assignment_item(
                                    tile=rk_tile,
                                    assigned_value=rk_value,
                                    assigned_color=None,
                                )
                            )

                        else:
                            color = right_color
                            tile = pos_to_tile[(value, color)]
                            result.append(
                                _format_assignment_item(
                                    tile=tile,
                                    assigned_value=value,
                                    assigned_color=color,
                                )
                            )

                    return result

    return None


def is_valid_run_full(tiles: List[Tile]) -> bool:
    return _find_run_assignment(tiles) is not None


def explain_run_assignment(tiles: List[Tile]) -> Optional[List[str]]:
    return _find_run_assignment(tiles)



# Group validation / explanation

def _find_group_assignment(tiles: List[Tile]) -> Optional[List[str]]:
    """
    Validate and explain a group.

    Group rules:
    - length 3 or 4
    - same value
    - all colors different
    - RK is not allowed
    """
    n = len(tiles)

    if n < 3 or n > 4:
        return None

    normal_tiles: List[Tile] = []
    prism_tiles: List[Tile] = []
    joker_tiles: List[Tile] = []

    for tile in tiles:
        if tile.tile_type == TileType.NORMAL:
            if tile.value is None or tile.color is None:
                return None
            normal_tiles.append(tile)

        elif tile.tile_type == TileType.PRISM_JOKER:
            if tile.prism_color is None:
                return None
            prism_tiles.append(tile)

        elif tile.tile_type == TileType.STANDARD_JOKER:
            joker_tiles.append(tile)

        elif tile.tile_type == TileType.RAINBOW_KING:
            return None

        else:
            return None

    normal_values = {tile.value for tile in normal_tiles}

    if len(normal_values) > 1:
        return None

    if normal_values:
        target_value = next(iter(normal_values))
    else:
        target_value = 1

    used_colors = set()

    for tile in normal_tiles:
        if tile.color in used_colors:
            return None
        used_colors.add(tile.color)

    for tile in prism_tiles:
        if tile.prism_color in used_colors:
            return None
        used_colors.add(tile.prism_color)

    remaining_colors = [color for color in STANDARD_COLORS if color not in used_colors]

    if len(joker_tiles) > len(remaining_colors):
        return None

    joker_assignment: Dict[int, Tuple[int, TileColor]] = {}

    for idx, joker in enumerate(joker_tiles):
        joker_assignment[joker.uid] = (target_value, remaining_colors[idx])

    result = []

    for tile in tiles:
        if tile.tile_type == TileType.NORMAL:
            result.append(tile.short_label())

        elif tile.tile_type == TileType.PRISM_JOKER:
            result.append(
                _format_assignment_item(
                    tile=tile,
                    assigned_value=target_value,
                    assigned_color=tile.prism_color,
                )
            )

        elif tile.tile_type == TileType.STANDARD_JOKER:
            assigned_value, assigned_color = joker_assignment[tile.uid]
            result.append(
                _format_assignment_item(
                    tile=tile,
                    assigned_value=assigned_value,
                    assigned_color=assigned_color,
                )
            )

    return result


def is_valid_group_full(tiles: List[Tile]) -> bool:
    return _find_group_assignment(tiles) is not None


def explain_group_assignment(tiles: List[Tile]) -> Optional[List[str]]:
    return _find_group_assignment(tiles)



# Public APIs

def classify_meld(tiles: List[Tile]) -> Optional[str]:
    if is_valid_run_full(tiles):
        return "run"

    if is_valid_group_full(tiles):
        return "group"

    return None


def explain_meld_assignment(meld: Meld) -> Optional[List[str]]:
    if meld.meld_type == MeldType.RUN:
        return explain_run_assignment(meld.tiles)

    if meld.meld_type == MeldType.GROUP:
        return explain_group_assignment(meld.tiles)

    return None