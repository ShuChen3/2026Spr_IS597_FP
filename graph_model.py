from typing import Optional
import networkx as nx
from Basic_env_rules import Tile, TileType, TileColor, PuzzleState

STANDARD_COLORS = [
    TileColor.RED,
    TileColor.BLUE,
    TileColor.YELLOW,
    TileColor.BLACK,
]

class RummikubGraph:
    """
    Graph-based representation of one puzzle state.

    Nodes:
        Each tile is one node.

    Edges:
        Candidate relationships only, not final meld legality.
        Edge attribute "relation_type" describes why the edge exists.
    """

    def __init__(self, state: PuzzleState):
        self.state = state
        self.graph = nx.MultiGraph()
        self._build_graph()


    # Main build pipeline
    def _build_graph(self) -> None:
        self._add_nodes_from_state()
        self._build_candidate_edges()


    # Node building
    def _add_nodes_from_state(self) -> None:
        # Add board tiles
        for meld_idx, meld in enumerate(self.state.board_melds):
            for tile in meld.tiles:
                self.graph.add_node(
                    tile.uid,
                    tile_obj=tile,
                    value=tile.value,
                    color=tile.color,
                    tile_type=tile.tile_type,
                    prism_color=tile.prism_color,
                    zone="board",
                    meld_index=meld_idx,
                )

        # Add hand tiles
        for tile in self.state.hand_tiles:
            self.graph.add_node(
                tile.uid,
                tile_obj=tile,
                value=tile.value,
                color=tile.color,
                tile_type=tile.tile_type,
                prism_color=tile.prism_color,
                zone="hand",
                meld_index=None,
            )


    # Edge building
    def _build_candidate_edges(self) -> None:
        node_ids = list(self.graph.nodes)

        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                uid1 = node_ids[i]
                uid2 = node_ids[j]

                tile1 = self.graph.nodes[uid1]["tile_obj"]
                tile2 = self.graph.nodes[uid2]["tile_obj"]

                self._maybe_add_edges_between(tile1, tile2)

    def _maybe_add_edges_between(self, tile1: Tile, tile2: Tile) -> None:
        """
        Add candidate edges between two tiles if they may relate
        in a run/group context.
        """
        uid1, uid2 = tile1.uid, tile2.uid


        # Normal <-> Normal
        if tile1.tile_type == TileType.NORMAL and tile2.tile_type == TileType.NORMAL:
            # run candidate: same color, adjacent values
            if tile1.color == tile2.color and abs(tile1.value - tile2.value) == 1:
                self.graph.add_edge(uid1, uid2, relation_type="run_candidate")

            # group candidate: same value, different colors
            if tile1.value == tile2.value and tile1.color != tile2.color:
                self.graph.add_edge(uid1, uid2, relation_type="group_candidate")


        # Standard Joker with anything except RK
        elif (
            tile1.tile_type == TileType.STANDARD_JOKER and
            tile2.tile_type != TileType.RAINBOW_KING
        ) or (
            tile2.tile_type == TileType.STANDARD_JOKER and
            tile1.tile_type != TileType.RAINBOW_KING
        ):
            self.graph.add_edge(uid1, uid2, relation_type="joker_candidate")


        # Prism Joker relations
        elif tile1.tile_type == TileType.PRISM_JOKER and tile2.tile_type == TileType.NORMAL:
            # Prism can join run if colors match
            if tile1.prism_color == tile2.color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_run_candidate")

            # Prism can join group if it can represent same value with its own color
            if tile1.prism_color != tile2.color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_group_candidate")

        elif tile2.tile_type == TileType.PRISM_JOKER and tile1.tile_type == TileType.NORMAL:
            if tile2.prism_color == tile1.color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_run_candidate")

            if tile2.prism_color != tile1.color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_group_candidate")

        elif tile1.tile_type == TileType.PRISM_JOKER and tile2.tile_type == TileType.PRISM_JOKER:
            # same-color prism may relate in run context
            if tile1.prism_color == tile2.prism_color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_run_candidate")

            # different-color prism may relate in group context
            if tile1.prism_color != tile2.prism_color:
                self.graph.add_edge(uid1, uid2, relation_type="prism_group_candidate")


        # Rainbow King relations
        elif tile1.tile_type == TileType.RAINBOW_KING and tile2.tile_type != TileType.RAINBOW_KING:
            # RK is only for run, never group
            # At graph level we just mark that RK may connect with non-RK tiles
            if tile2.tile_type in {TileType.NORMAL, TileType.STANDARD_JOKER, TileType.PRISM_JOKER}:
                self.graph.add_edge(uid1, uid2, relation_type="rk_candidate")

        elif tile2.tile_type == TileType.RAINBOW_KING and tile1.tile_type != TileType.RAINBOW_KING:
            if tile1.tile_type in {TileType.NORMAL, TileType.STANDARD_JOKER, TileType.PRISM_JOKER}:
                self.graph.add_edge(uid1, uid2, relation_type="rk_candidate")


    # Public helpers
    def get_graph(self) -> nx.MultiGraph:
        return self.graph

    def number_of_nodes(self) -> int:
        return self.graph.number_of_nodes()

    def number_of_edges(self) -> int:
        return self.graph.number_of_edges()

    def get_tile_by_uid(self, uid: int) -> Optional[Tile]:
        if uid not in self.graph.nodes:
            return None
        return self.graph.nodes[uid]["tile_obj"]

    def print_summary(self) -> None:
        print("=== RummikubGraph Summary ===")
        print(f"Nodes: {self.number_of_nodes()}")
        print(f"Edges: {self.number_of_edges()}")

        board_nodes = [n for n, data in self.graph.nodes(data=True) if data["zone"] == "board"]
        hand_nodes = [n for n, data in self.graph.nodes(data=True) if data["zone"] == "hand"]

        print(f"Board nodes: {len(board_nodes)}")
        print(f"Hand nodes: {len(hand_nodes)}")

    def print_edges(self, limit: int = 50) -> None:
        print("=== Edge List ===")
        count = 0
        for u, v, data in self.graph.edges(data=True):
            tile_u = self.graph.nodes[u]["tile_obj"]
            tile_v = self.graph.nodes[v]["tile_obj"]
            relation = data.get("relation_type", "unknown")
            print(f"{tile_u.short_label()} -- {tile_v.short_label()} [{relation}]")
            count += 1
            if count >= limit:
                print(f"... (showing first {limit} edges only)")
                break