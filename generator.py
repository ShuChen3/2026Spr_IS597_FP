import random
from typing import List, Set, Tuple, Optional

from Basic_env_rules import Tile, TileType, TileColor, Meld, MeldType, PuzzleState
from graph_model import RummikubGraph
from candidate_generator import generate_all_candidates_graph_based
from solver import solve_puzzle



# Basic helpers
def _flatten_board_melds(board_melds: List[Meld]) -> List[Tile]:
    tiles: List[Tile] = []
    for meld in board_melds:
        tiles.extend(meld.tiles)
    return tiles


def _validate_goal_board(goal_board: List[Meld]) -> None:
    all_tiles = _flatten_board_melds(goal_board)
    uids = [tile.uid for tile in all_tiles]

    if len(uids) != len(set(uids)):
        raise ValueError("Goal board contains duplicate tile uids.")


def _meld_signature(meld: Meld) -> frozenset[int]:
    return frozenset(tile.uid for tile in meld.tiles)


def _board_signature(board_melds: List[Meld]) -> frozenset[frozenset[int]]:
    return frozenset(_meld_signature(meld) for meld in board_melds)



# Printing helpers
def print_goal_board(goal_board: List[Meld]) -> None:
    print("=== Goal Board ===")
    for i, meld in enumerate(goal_board, start=1):
        print(f"{i}. {meld}")


def print_puzzle_state(state: PuzzleState) -> None:
    print("=== Generated Puzzle State ===")
    print("Board:")
    for i, meld in enumerate(state.board_melds, start=1):
        print(f"{i}. {meld}")

    print("Hand:")
    if state.hand_tiles:
        print(", ".join(tile.short_label() for tile in state.hand_tiles))
    else:
        print("(empty)")



# Repartition remaining tiles into a legal board

def find_alternative_legal_board_for_tiles(remaining_tiles: List[Tile],original_remaining_melds: List[Meld],max_run_len: int = 4) -> Optional[List[Meld]]:
    """
    Repartition remaining tiles into legal melds.
    Prefer a board structure different from the direct leftover board.
    """

    temp_state = PuzzleState(
        board_melds=[],
        hand_tiles=remaining_tiles,
    )

    rg = RummikubGraph(temp_state)
    candidates = generate_all_candidates_graph_based(rg, max_run_len=max_run_len)

    target_uids = {tile.uid for tile in remaining_tiles}
    original_sig = _board_signature(original_remaining_melds)

    candidate_data = []
    for meld in candidates:
        uid_set = {tile.uid for tile in meld.tiles}
        if uid_set.issubset(target_uids):
            candidate_data.append((meld, uid_set))

    candidate_data.sort(key=lambda item: (-len(item[1]), sorted(item[1])))

    solution: List[Meld] = []
    fallback_same_solution: Optional[List[Meld]] = None

    def backtrack(used_uids: Set[int]) -> Optional[List[Meld]]:
        nonlocal fallback_same_solution

        if used_uids == target_uids:
            current_sig = _board_signature(solution)

            if current_sig != original_sig:
                return list(solution)

            if fallback_same_solution is None:
                fallback_same_solution = list(solution)

            return None

        remaining = target_uids - used_uids
        if not remaining:
            return None

        next_uid = min(remaining)

        for meld, uid_set in candidate_data:
            if next_uid not in uid_set:
                continue

            if uid_set & used_uids:
                continue

            solution.append(meld)
            result = backtrack(used_uids | uid_set)
            if result is not None:
                return result
            solution.pop()

        return None

    alternative = backtrack(set())

    if alternative is not None:
        return alternative

    return fallback_same_solution



# Build puzzle from existing goal board

def build_puzzle_from_goal_board_v2(
    goal_board: List[Meld],
    hand_tile_uids: List[int],
    verify_with_solver: bool = True,
    max_run_len: int = 4,
) -> Tuple[PuzzleState, bool, bool]:
    """
    Build puzzle from a known goal board and manually selected hand tiles.
    The remaining board is repartitioned into legal melds.
    """

    _validate_goal_board(goal_board)

    hand_uid_set = set(hand_tile_uids)

    hand_tiles: List[Tile] = []
    remaining_tiles: List[Tile] = []
    original_remaining_melds: List[Meld] = []

    for meld in goal_board:
        kept_tiles: List[Tile] = []

        for tile in meld.tiles:
            if tile.uid in hand_uid_set:
                hand_tiles.append(tile)
            else:
                kept_tiles.append(tile)
                remaining_tiles.append(tile)

        if kept_tiles:
            original_remaining_melds.append(
                Meld(
                    tiles=kept_tiles,
                    meld_type=meld.meld_type,
                    source="direct_leftover",
                )
            )

    alternative_board = find_alternative_legal_board_for_tiles(
        remaining_tiles=remaining_tiles,
        original_remaining_melds=original_remaining_melds,
        max_run_len=max_run_len,
    )

    if alternative_board is None:
        board_start_melds = original_remaining_melds
    else:
        board_start_melds = [
            Meld(
                tiles=meld.tiles,
                meld_type=meld.meld_type,
                source="reshuffled_board",
            )
            for meld in alternative_board
        ]

    changed = _board_signature(board_start_melds) != _board_signature(original_remaining_melds)

    puzzle_state = PuzzleState(
        board_melds=board_start_melds,
        hand_tiles=hand_tiles,
    )

    solvable = True
    if verify_with_solver:
        solvable, _ = solve_puzzle(puzzle_state, max_run_len=max_run_len)

    return puzzle_state, solvable, changed


def build_puzzle_from_goal_board_v3(
    goal_board: List[Meld],
    hand_size: int,
    require_changed_board: bool = True,
    prefer_special_tiles: bool = True,
    verify_with_solver: bool = True,
    max_run_len: int = 4,
    max_attempts: int = 200,
    random_seed: Optional[int] = None,
) -> Tuple[PuzzleState, bool, bool, List[int]]:
    """
    Build puzzle from a known goal board with automatically selected hand tiles.
    """

    rng = random.Random(random_seed)

    _validate_goal_board(goal_board)

    all_tiles = _flatten_board_melds(goal_board)

    if hand_size <= 0:
        raise ValueError("hand_size must be positive.")

    if hand_size >= len(all_tiles):
        raise ValueError("hand_size must be smaller than total number of tiles.")

    special_tiles = [tile for tile in all_tiles if tile.tile_type != TileType.NORMAL]

    best_fallback = None

    for _ in range(max_attempts):
        selected_tiles: List[Tile] = []

        if prefer_special_tiles and special_tiles:
            selected_tiles.append(rng.choice(special_tiles))

        selected_uids = {tile.uid for tile in selected_tiles}
        remaining_pool = [tile for tile in all_tiles if tile.uid not in selected_uids]

        if len(selected_tiles) < hand_size:
            selected_tiles.extend(
                rng.sample(
                    remaining_pool,
                    hand_size - len(selected_tiles),
                )
            )

        hand_tile_uids = [tile.uid for tile in selected_tiles]

        puzzle_state, solvable, changed = build_puzzle_from_goal_board_v2(
            goal_board=goal_board,
            hand_tile_uids=hand_tile_uids,
            verify_with_solver=verify_with_solver,
            max_run_len=max_run_len,
        )

        if solvable:
            if not require_changed_board or changed:
                return puzzle_state, solvable, changed, hand_tile_uids

            if best_fallback is None:
                best_fallback = (puzzle_state, solvable, changed, hand_tile_uids)

    if best_fallback is not None:
        return best_fallback

    raise RuntimeError(
        f"Failed to generate a valid puzzle after {max_attempts} attempts."
    )



# Mixed automatic goal board generation
from validator import is_valid_run_full, is_valid_group_full


STANDARD_COLORS = [
    TileColor.RED,
    TileColor.BLUE,
    TileColor.BLACK,
    TileColor.YELLOW,
]


def _next_uid(start_uid: int):
    uid = start_uid
    while True:
        yield uid
        uid += 1


def _make_standard_joker(uid_gen) -> Tile:
    return Tile(
        uid=next(uid_gen),
        tile_type=TileType.STANDARD_JOKER,
    )


def _make_rainbow_king(uid_gen) -> Tile:
    return Tile(
        uid=next(uid_gen),
        tile_type=TileType.RAINBOW_KING,
        color=TileColor.RAINBOW,
    )


def _make_prism_joker(uid_gen, prism_color: TileColor) -> Tile:
    return Tile(
        uid=next(uid_gen),
        tile_type=TileType.PRISM_JOKER,
        prism_color=prism_color,
    )


def _make_available_normal_tile(
    uid_gen,
    value: int,
    color: TileColor,
    normal_counts: dict[tuple[TileColor, int], int],
) -> Tile:
    """
    Create a normal tile while respecting the two-copy Rummikub rule.
    """
    key = (color, value)
    current_count = normal_counts.get(key, 0)

    if current_count >= 2:
        raise ValueError(f"No more available copies for {color.value}{value}")

    normal_counts[key] = current_count + 1

    return Tile(
        uid=next(uid_gen),
        tile_type=TileType.NORMAL,
        value=value,
        color=color,
        copy_index=normal_counts[key],
    )


def _try_make_normal_run(
    uid_gen,
    rng: random.Random,
    normal_counts: dict[tuple[TileColor, int], int],
    min_len: int = 3,
    max_len: int = 6,
) -> Meld:
    """
    Generate a normal same-color run.
    """
    for _ in range(100):
        run_len = rng.randint(min_len, max_len)
        color = rng.choice(STANDARD_COLORS)
        start = rng.randint(1, 13 - run_len + 1)

        try:
            tiles = [
                _make_available_normal_tile(uid_gen, value, color, normal_counts)
                for value in range(start, start + run_len)
            ]

            meld = Meld(tiles=tiles, meld_type=MeldType.RUN, source="goal_mixed")
            if is_valid_run_full(meld.tiles):
                return meld

        except ValueError:
            continue

    raise RuntimeError("Failed to generate a normal run.")


def _try_make_normal_group(
    uid_gen,
    rng: random.Random,
    normal_counts: dict[tuple[TileColor, int], int],
    min_size: int = 3,
    max_size: int = 4,
) -> Meld:
    """
    Generate a normal same-value group.
    """
    for _ in range(100):
        group_size = rng.randint(min_size, max_size)
        value = rng.randint(1, 13)
        colors = rng.sample(STANDARD_COLORS, group_size)

        try:
            tiles = [
                _make_available_normal_tile(uid_gen, value, color, normal_counts)
                for color in colors
            ]

            meld = Meld(tiles=tiles, meld_type=MeldType.GROUP, source="goal_mixed")
            if is_valid_group_full(meld.tiles):
                return meld

        except ValueError:
            continue

    raise RuntimeError("Failed to generate a normal group.")


def _try_make_joker_meld(
    uid_gen,
    rng: random.Random,
    normal_counts: dict[tuple[TileColor, int], int],
    run_min_len: int,
    run_max_len: int,
) -> Meld:
    """
    Generate a legal meld containing one Standard Joker.
    It can be either a run or a group.

    """
    for _ in range(100):
        mode = rng.choice(["run", "group"])
        joker = _make_standard_joker(uid_gen)

        try:
            if mode == "run":
                run_len = rng.randint(run_min_len, run_max_len)
                color = rng.choice(STANDARD_COLORS)
                start = rng.randint(1, 13 - run_len + 1)
                joker_pos = rng.randint(0, run_len - 1)

                tiles = []
                for pos in range(run_len):
                    value = start + pos

                    if pos == joker_pos:
                        tiles.append(joker)
                    else:
                        tiles.append(
                            _make_available_normal_tile(
                                uid_gen,
                                value,
                                color,
                                normal_counts,
                            )
                        )

                meld = Meld(
                    tiles=tiles,
                    meld_type=MeldType.RUN,
                    source="goal_mixed",
                )

                if is_valid_run_full(meld.tiles):
                    return meld

            else:
                group_size = rng.randint(3, 4)
                value = rng.randint(1, 13)
                normal_colors = rng.sample(STANDARD_COLORS, group_size - 1)

                tiles = [
                    _make_available_normal_tile(
                        uid_gen,
                        value,
                        color,
                        normal_counts,
                    )
                    for color in normal_colors
                ]
                tiles.append(joker)

                meld = Meld(
                    tiles=tiles,
                    meld_type=MeldType.GROUP,
                    source="goal_mixed",
                )

                if is_valid_group_full(meld.tiles):
                    return meld

        except ValueError:
            continue

    raise RuntimeError("Failed to generate a joker meld.")


def _try_make_prism_meld(
    uid_gen,
    rng: random.Random,
    normal_counts: dict[tuple[TileColor, int], int],
    available_prism_colors: list[TileColor],
    run_min_len: int,
    run_max_len: int,
) -> Meld:
    """
    Generate a legal meld containing one Prism Joker.
    It can be either a run or a group.

    """
    if not available_prism_colors:
        raise RuntimeError("No available Prism Joker colors left.")

    for _ in range(100):
        mode = rng.choice(["run", "group"])
        prism_color = rng.choice(available_prism_colors)
        prism = _make_prism_joker(uid_gen, prism_color)

        try:
            if mode == "run":
                run_len = rng.randint(run_min_len, run_max_len)
                start = rng.randint(1, 13 - run_len + 1)
                prism_pos = rng.randint(0, run_len - 1)

                tiles = []
                for pos in range(run_len):
                    value = start + pos

                    if pos == prism_pos:
                        tiles.append(prism)
                    else:
                        tiles.append(
                            _make_available_normal_tile(
                                uid_gen,
                                value,
                                prism_color,
                                normal_counts,
                            )
                        )

                meld = Meld(
                    tiles=tiles,
                    meld_type=MeldType.RUN,
                    source="goal_mixed",
                )

                if is_valid_run_full(meld.tiles):
                    available_prism_colors.remove(prism_color)
                    return meld

            else:
                group_size = rng.randint(3, 4)
                value = rng.randint(1, 13)

                normal_color_pool = [
                    color for color in STANDARD_COLORS
                    if color != prism_color
                ]
                normal_colors = rng.sample(normal_color_pool, group_size - 1)

                tiles = [
                    _make_available_normal_tile(
                        uid_gen,
                        value,
                        color,
                        normal_counts,
                    )
                    for color in normal_colors
                ]
                tiles.append(prism)

                meld = Meld(
                    tiles=tiles,
                    meld_type=MeldType.GROUP,
                    source="goal_mixed",
                )

                if is_valid_group_full(meld.tiles):
                    available_prism_colors.remove(prism_color)
                    return meld

        except ValueError:
            continue

    raise RuntimeError("Failed to generate a prism meld.")


def _try_make_rk_run(
    uid_gen,
    rng: random.Random,
    normal_counts: dict[tuple[TileColor, int], int],
    run_min_len: int,
    run_max_len: int,
) -> Meld:
    """
    Generate a legal run containing one Rainbow King.
    """
    for _ in range(100):
        run_len = rng.randint(run_min_len, run_max_len)

        # RK cannot be at either end, so length must be at least 3.
        if run_len < 3:
            continue

        start = rng.randint(1, 13 - run_len + 1)

        # RK position must be inside the run, not at the ends.
        rk_pos = rng.randint(1, run_len - 2)
        rk_value = start + rk_pos

        left_color, right_color = rng.sample(STANDARD_COLORS, 2)

        try:
            tiles = []

            for pos in range(run_len):
                value = start + pos

                if pos < rk_pos:
                    tiles.append(
                        _make_available_normal_tile(
                            uid_gen,
                            value,
                            left_color,
                            normal_counts,
                        )
                    )

                elif pos == rk_pos:
                    tiles.append(_make_rainbow_king(uid_gen))

                else:
                    tiles.append(
                        _make_available_normal_tile(
                            uid_gen,
                            value,
                            right_color,
                            normal_counts,
                        )
                    )

            meld = Meld(
                tiles=tiles,
                meld_type=MeldType.RUN,
                source="goal_mixed",
            )

            if is_valid_run_full(meld.tiles):
                return meld

        except ValueError:
            continue

    raise RuntimeError("Failed to generate an RK run.")


def generate_mixed_goal_board(
    num_normal_runs: int = 2,
    num_groups: int = 2,
    num_joker_melds: int = 1,
    num_prism_melds: int = 1,
    num_rk_runs: int = 1,
    normal_run_min_len: int = 3,
    normal_run_max_len: int = 6,
    random_seed: Optional[int] = None,
) -> List[Meld]:
    """
    Generate a mixed and more realistic legal goal board.

    It may include:
    - normal runs
    - normal groups
    - Standard Joker melds
    - Prism Joker melds
    - Rainbow King runs
    """

    if num_joker_melds > 2:
        raise ValueError("There are only 2 Standard Jokers available.")

    if num_rk_runs > 2:
        raise ValueError("There are only 2 Rainbow Kings available.")

    if num_prism_melds > 4:
        raise ValueError("There are only 4 Prism Jokers available.")

    rng = random.Random(random_seed)
    uid_gen = _next_uid(1)

    normal_counts: dict[tuple[TileColor, int], int] = {}
    available_prism_colors = STANDARD_COLORS.copy()

    goal_board: List[Meld] = []

    for _ in range(num_normal_runs):
        goal_board.append(
            _try_make_normal_run(
                uid_gen=uid_gen,
                rng=rng,
                normal_counts=normal_counts,
                min_len=normal_run_min_len,
                max_len=normal_run_max_len,
            )
        )

    for _ in range(num_groups):
        goal_board.append(
            _try_make_normal_group(
                uid_gen=uid_gen,
                rng=rng,
                normal_counts=normal_counts,
            )
        )

    for _ in range(num_joker_melds):
        goal_board.append(
            _try_make_joker_meld(
                uid_gen=uid_gen,
                rng=rng,
                normal_counts=normal_counts,
                run_min_len=normal_run_min_len,
                run_max_len=normal_run_max_len,
            )
        )

    for _ in range(num_prism_melds):
        goal_board.append(
            _try_make_prism_meld(
                uid_gen=uid_gen,
                rng=rng,
                normal_counts=normal_counts,
                available_prism_colors=available_prism_colors,
                run_min_len=normal_run_min_len,
                run_max_len=normal_run_max_len,
            )
        )

    for _ in range(num_rk_runs):
        goal_board.append(
            _try_make_rk_run(
                uid_gen=uid_gen,
                rng=rng,
                normal_counts=normal_counts,
                run_min_len=normal_run_min_len,
                run_max_len=normal_run_max_len,
            )
        )

    rng.shuffle(goal_board)
    _validate_goal_board(goal_board)

    return goal_board



# Final v4 generator


def build_auto_generated_puzzle_v4(
    num_normal_runs: int = 2,
    num_groups: int = 2,
    num_joker_melds: int = 1,
    num_prism_melds: int = 1,
    num_rk_runs: int = 1,
    normal_run_min_len: int = 3,
    normal_run_max_len: int = 6,
    hand_size: int = 5,
    require_changed_board: bool = True,
    prefer_special_tiles: bool = True,
    max_run_len: int = 4,
    max_attempts_goal: int = 50,
    max_attempts_hand: int = 300,
    random_seed: Optional[int] = None,
) -> Tuple[List[Meld], PuzzleState, bool, bool, List[int]]:
    """
    Final automatic mixed puzzle generator.

    1. Generate a mixed legal goal board.
    2. Automatically select hand tiles.
    3. Repartition remaining tiles into a legal board_start.
    4. Verify solvability.
    """

    rng = random.Random(random_seed)

    for _ in range(max_attempts_goal):
        seed = rng.randint(1, 10_000_000)

        goal_board = generate_mixed_goal_board(
            num_normal_runs=num_normal_runs,
            num_groups=num_groups,
            num_joker_melds=num_joker_melds,
            num_prism_melds=num_prism_melds,
            num_rk_runs=num_rk_runs,
            normal_run_min_len=normal_run_min_len,
            normal_run_max_len=normal_run_max_len,
            random_seed=seed,
        )

        try:
            state, solvable, changed, hand_tile_uids = build_puzzle_from_goal_board_v3(
                goal_board=goal_board,
                hand_size=hand_size,
                require_changed_board=require_changed_board,
                prefer_special_tiles=prefer_special_tiles,
                verify_with_solver=True,
                max_run_len=max_run_len,
                max_attempts=max_attempts_hand,
                random_seed=seed,
            )

            if solvable and (not require_changed_board or changed):
                return goal_board, state, solvable, changed, hand_tile_uids

        except RuntimeError:
            continue

    raise RuntimeError(
        f"Failed to auto-generate a puzzle after {max_attempts_goal} goal attempts."
    )