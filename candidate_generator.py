from itertools import combinations
from typing import List, Tuple, Set

from Basic_env_rules import Tile, TileType, Meld, MeldType
from graph_model import RummikubGraph
from validator import is_valid_run_full, is_valid_group_full


def _run_display_sort_key(tile: Tile):
    """
    A display-only sort key for run melds.
    """
    if tile.tile_type == TileType.NORMAL:
        return (0, tile.value if tile.value is not None else 999, tile.uid)

    # Prism / Joker / RK after normal tiles
    return (1, 999, tile.uid)


def _make_meld_from_tiles(tiles: List[Tile], meld_kind: str) -> Meld:
    """
    Convert a list of Tile objects into a Meld object.
    """
    if meld_kind == "run":
        meld_type = MeldType.RUN
        sorted_tiles = sorted(tiles, key=_run_display_sort_key)
    elif meld_kind == "group":
        meld_type = MeldType.GROUP
        sorted_tiles = sorted(tiles, key=lambda t: t.uid)
    else:
        meld_type = MeldType.UNKNOWN
        sorted_tiles = sorted(tiles, key=lambda t: t.uid)

    return Meld(
        tiles=sorted_tiles,
        meld_type=meld_type,
        source="candidate"
    )

def _uid_key_from_tiles(tiles: List[Tile]) -> Tuple[int, ...]:
    """
    Build a hashable sorted uid key for deduplication.
    """
    return tuple(sorted(tile.uid for tile in tiles))


"""
 Graph-based group candidates
"""


def _get_group_related_neighbors(rg: RummikubGraph, uid: int) -> List[int]:
    """
    Return neighbors of a node that are connected by group-related edge types.
    """
    graph = rg.get_graph()
    neighbors = set()

    for _, v, data in graph.edges(uid, data=True):
        relation = data.get("relation_type")
        if relation in {"group_candidate", "prism_group_candidate", "joker_candidate"}:
            neighbors.add(v)

    return sorted(neighbors)


def generate_candidate_groups_graph_based(rg: RummikubGraph) -> List[Meld]:
    """
    Graph-based candidate group generator.

    - For each anchor node u
    - Collect only group-related neighbors of u
    - Enumerate 3-tile and 4-tile combinations inside this local neighborhood
    - Require the candidate to include u
    - Validate with is_valid_group_full()
    - Deduplicate globally
    """
    graph = rg.get_graph()

    candidates: List[Meld] = []
    seen: Set[Tuple[int, ...]] = set()

    for uid in graph.nodes:
        anchor_tile = graph.nodes[uid]["tile_obj"]

        # RK can never be in a group, so no need to use it as anchor
        if anchor_tile.tile_type == TileType.RAINBOW_KING:
            continue

        neighbors = _get_group_related_neighbors(rg, uid)

        # local node pool = anchor + its local group-related neighbors
        local_ids = [uid] + neighbors
        local_ids = sorted(set(local_ids))

        # group size can only be 3 or 4
        for size in [3, 4]:
            if len(local_ids) < size:
                continue

            for combo in combinations(local_ids, size):
                # require anchor to be part of this candidate
                if uid not in combo:
                    continue

                tiles = [graph.nodes[node_id]["tile_obj"] for node_id in combo]

                if not is_valid_group_full(tiles):
                    continue

                uid_key = _uid_key_from_tiles(tiles)
                if uid_key in seen:
                    continue

                seen.add(uid_key)
                candidates.append(_make_meld_from_tiles(tiles, "group"))

    # stable sort for nicer output
    candidates.sort(key=lambda m: (len(m.tiles), [t.uid for t in m.tiles]))
    return candidates




def _get_run_related_neighbors(rg: RummikubGraph, uid: int) -> List[int]:
    """
    Return neighbors of a node that are connected by run-related edge types.
    """
    graph = rg.get_graph()
    neighbors = set()

    for _, v, data in graph.edges(uid, data=True):
        relation = data.get("relation_type")
        if relation in {"run_candidate", "prism_run_candidate", "joker_candidate", "rk_candidate"}:
            neighbors.add(v)

    return sorted(set(list(neighbors)))




def generate_candidate_runs_graph_path_based(rg: RummikubGraph, max_len: int = 6) -> List[Meld]:
    """
    Graph-based run generator.

    - Start from each node as an anchor
    - Expand only through run-related neighbors
    - Build simple node paths (no repeated node)
    - Validate only when path length reaches 3..max_len
    - Deduplicate globally by tile uid set
    - Only expand to neighbors whose uid is greater than the start uid
      to reduce repeated discovery of the same candidate from multiple starts.
    """

    graph = rg.get_graph()
    candidates: List[Meld] = []
    seen: Set[Tuple[int, ...]] = set()

    def dfs(start_uid: int, path: List[int], visited: Set[int]) -> None:
        # Validate current path if length is enough
        if 3 <= len(path) <= max_len:
            tiles = [graph.nodes[node_id]["tile_obj"] for node_id in path]

            if is_valid_run_full(tiles):
                uid_key = _uid_key_from_tiles(tiles)
                if uid_key not in seen:
                    seen.add(uid_key)
                    candidates.append(_make_meld_from_tiles(tiles, "run"))

        # Stop expansion if max length reached
        if len(path) == max_len:
            return

        last_uid = path[-1]
        next_neighbors = _get_run_related_neighbors(rg, last_uid)

        for nbr in next_neighbors:
            if nbr in visited:
                continue


            # only expand to nodes with uid greater than the start uid
            if nbr <= start_uid:
                continue

            visited.add(nbr)
            path.append(nbr)

            dfs(start_uid, path, visited)

            path.pop()
            visited.remove(nbr)

    for start_uid in sorted(graph.nodes):
        dfs(start_uid, [start_uid], {start_uid})

    # Stable sort for easier reading
    candidates.sort(key=lambda m: (len(m.tiles), [t.uid for t in m.tiles]))
    return candidates



def generate_all_candidates_graph_based(rg: RummikubGraph, max_run_len: int = 4) -> List[Meld]:
    """
    Unified graph-based candidate generator for solver use.
    """
    group_candidates = generate_candidate_groups_graph_based(rg)
    run_candidates = generate_candidate_runs_graph_path_based(rg, max_len=max_run_len)

    all_candidates = group_candidates + run_candidates

    seen: Set[Tuple[int, ...]] = set()
    unique_candidates: List[Meld] = []

    for meld in all_candidates:
        uid_key = _uid_key_from_tiles(meld.tiles)
        if uid_key in seen:
            continue
        seen.add(uid_key)
        unique_candidates.append(meld)

    unique_candidates.sort(key=lambda m: (len(m.tiles), m.meld_type.value, [t.uid for t in m.tiles]))
    return unique_candidates