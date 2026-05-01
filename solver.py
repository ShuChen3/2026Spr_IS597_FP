from typing import List, Set, Tuple, FrozenSet, Dict, Optional
from collections import defaultdict

from Basic_env_rules import PuzzleState, Meld, MeldType
from graph_model import RummikubGraph
from candidate_generator import generate_all_candidates_graph_based
from validator import explain_meld_assignment



# Helpers

def _meld_uid_set(meld: Meld) -> Set[int]:
    return {tile.uid for tile in meld.tiles}


def _all_state_tile_uids(state: PuzzleState) -> Set[int]:
    return {tile.uid for tile in state.all_tiles()}


def _normalize_explanation_item(item: str) -> str:
    """
    Convert explanation item into a display-level canonical form.

    Examples:
        R7 -> R7
        J=Yellow10 -> WILD=Yellow10
        PJ-Yellow=Yellow10 -> WILD=Yellow10
        RK=8 -> RK=8

    This helps merge solutions that only differ by:
    - physical duplicate tile uid
    - group ordering
    - Joker / Prism Joker interchangeable assignment
    """

    if "=" not in item:
        return item.strip()

    left, right = item.split("=", 1)
    left = left.strip()
    right = right.strip()

    if left.startswith("RK"):
        return f"RK={right}"

    if left.startswith("J") or left.startswith("PJ"):
        return f"WILD={right}"

    return f"{left}={right}"


def _meld_display_structure_key(meld: Meld) -> Tuple[str, Tuple[str, ...]]:
    """
    Human-level canonical key for one meld.
    """

    meld_type_key = str(meld.meld_type)

    explanation = explain_meld_assignment(meld)

    if explanation is None:
        labels = [tile.short_label() for tile in meld.tiles]
    else:
        labels = [_normalize_explanation_item(item) for item in explanation]

    if meld.meld_type == MeldType.GROUP:
        labels = sorted(labels)

    return meld_type_key, tuple(labels)


def _solution_display_structure_key(solution: List[Meld]) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """
    Human-level canonical key for a whole solution.
    """
    meld_keys = [_meld_display_structure_key(meld) for meld in solution]
    return tuple(sorted(meld_keys))


def _prepare_candidate_data(state: PuzzleState,max_run_len: int,) -> Tuple[List[Tuple[Meld, Set[int]]], Set[int]]:
    """
    Generate graph-based candidates.

    Use uid sets for actual solving, because physical tiles cannot overlap.
    """
    rg = RummikubGraph(state)
    candidates = generate_all_candidates_graph_based(rg, max_run_len=max_run_len)

    target_uids = _all_state_tile_uids(state)

    candidate_data: List[Tuple[Meld, Set[int]]] = []
    seen_candidate_keys = set()

    for meld in candidates:
        uid_set = _meld_uid_set(meld)

        # Deduplicate exact physical candidates first
        physical_key = (meld.meld_type.value, tuple(sorted(uid_set)))
        if physical_key in seen_candidate_keys:
            continue

        seen_candidate_keys.add(physical_key)
        candidate_data.append((meld, uid_set))

    candidate_data.sort(key=lambda item: (-len(item[1]), sorted(item[1])))

    return candidate_data, target_uids



# Main Solver

def solve_puzzle(state: PuzzleState,max_run_len: int = 4,) -> Tuple[bool, List[Meld]]:
    """
    Find one valid solution.

    - graph-based candidate generation
    - inverted index
    - MRV heuristic
    - failed-state memoization
    """
    candidate_data, target_uids = _prepare_candidate_data(state, max_run_len=max_run_len)

    uid_to_candidate_indices: Dict[int, List[int]] = defaultdict(list)
    for idx, (_, uid_set) in enumerate(candidate_data):
        for uid in uid_set:
            uid_to_candidate_indices[uid].append(idx)

    solution: List[Meld] = []
    failed_states: Set[FrozenSet[int]] = set()

    def choose_next_uid_mrv(used_uids: Set[int]) -> Optional[int]:
        remaining = target_uids - used_uids
        if not remaining:
            return None

        best_uid = None
        best_count = None

        for uid in remaining:
            valid_count = 0

            for idx in uid_to_candidate_indices.get(uid, []):
                _, uid_set = candidate_data[idx]
                if uid_set & used_uids:
                    continue
                valid_count += 1

            if best_count is None or valid_count < best_count:
                best_uid = uid
                best_count = valid_count

            if best_count == 0:
                break

        return best_uid

    def backtrack(used_uids: Set[int]) -> bool:
        if used_uids == target_uids:
            return True

        state_key = frozenset(used_uids)
        if state_key in failed_states:
            return False

        next_uid = choose_next_uid_mrv(used_uids)
        if next_uid is None:
            return True

        for idx in uid_to_candidate_indices.get(next_uid, []):
            meld, uid_set = candidate_data[idx]

            if uid_set & used_uids:
                continue

            solution.append(meld)

            if backtrack(used_uids | uid_set):
                return True

            solution.pop()

        failed_states.add(state_key)
        return False

    success = backtrack(set())
    return (True, solution) if success else (False, [])



# Unique Multi-solution Solver


def solve_all_puzzles(state: PuzzleState,max_run_len: int = 4,max_solutions: int = 20,max_raw_search: int = 5000) -> List[List[Meld]]:
    """
    Find multiple human-level unique solutions.

    Deduplication removes solutions that only differ by:
    - order of melds
    - order of tiles inside a group
    - physical duplicate tile uid
    - Joker / Prism Joker interchangeable assignment display

    max_solutions:
        Maximum number of unique solutions to return.

    max_raw_search:
        Safety limit for raw complete solutions inspected.
    """
    candidate_data, target_uids = _prepare_candidate_data(state, max_run_len=max_run_len)

    solutions: List[List[Meld]] = []
    seen_solution_keys = set()
    current_solution: List[Meld] = []

    raw_solution_count = 0

    def backtrack(used_uids: Set[int]) -> None:
        nonlocal raw_solution_count

        if len(solutions) >= max_solutions:
            return

        if raw_solution_count >= max_raw_search:
            return

        if used_uids == target_uids:
            raw_solution_count += 1

            key = _solution_display_structure_key(current_solution)

            if key not in seen_solution_keys:
                seen_solution_keys.add(key)
                solutions.append(list(current_solution))

            return

        remaining = target_uids - used_uids
        if not remaining:
            return

        next_uid = min(remaining)

        for meld, uid_set in candidate_data:
            if next_uid not in uid_set:
                continue

            if uid_set & used_uids:
                continue

            current_solution.append(meld)
            backtrack(used_uids | uid_set)
            current_solution.pop()

    backtrack(set())
    return solutions