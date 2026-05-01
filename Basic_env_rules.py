from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

"""
IS 597 DS - Final Project

Rummikub endgame puzzle generator and solver - v1
"""

class TileColor(Enum):
    RED = "Red"
    BLUE = "Blue"
    YELLOW = "Yellow"
    BLACK = "Black"
    RAINBOW = "Rainbow"


class TileType(Enum):
    NORMAL = "Normal"
    STANDARD_JOKER = "Standard_Joker"
    RAINBOW_KING = "Rainbow_King"
    PRISM_JOKER = "Prism_Joker"


class MeldType(Enum):
    RUN = "run"
    GROUP = "group"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Tile:
    """
    A single tile in the extended Rummikub system.

    Notes:
    - Normal tiles should have both value and color.
    - Standard Joker usually has value=None and color=None.
    - Rainbow King usually has value=None and color=RAINBOW.
    - Prism Joker usually has value=None and color=None, but prism_color must be set.
    """
    uid: int
    tile_type: TileType
    value: Optional[int] = None
    color: Optional[TileColor] = None
    prism_color: Optional[TileColor] = None
    copy_index: Optional[int] = None   # useful for duplicated normal tiles
    zone: Optional[str] = None         # "board" or "hand", can be updated in copied objects

    def is_normal(self) -> bool:
        return self.tile_type == TileType.NORMAL

    def is_standard_joker(self) -> bool:
        return self.tile_type == TileType.STANDARD_JOKER

    def is_rainbow_king(self) -> bool:
        return self.tile_type == TileType.RAINBOW_KING

    def is_prism_joker(self) -> bool:
        return self.tile_type == TileType.PRISM_JOKER

    def is_special(self) -> bool:
        return self.tile_type != TileType.NORMAL

    def short_label(self) -> str:
        """
        Return a short human-readable label for display/debugging.
        """
        color_map = {
            TileColor.RED: "R",
            TileColor.BLUE: "U",  # use U for blUe
            TileColor.YELLOW: "Y",
            TileColor.BLACK: "K",  # use K for blacK
            TileColor.RAINBOW: "W",  # W for rainboW
        }

        if self.tile_type == TileType.NORMAL:
            if self.color is None or self.value is None:
                return f"INVALID_NORMAL[{self.uid}]"
            return f"{color_map[self.color]}{self.value}"

        if self.tile_type == TileType.STANDARD_JOKER:
            return f"J[{self.uid}]"

        if self.tile_type == TileType.RAINBOW_KING:
            return f"RK[{self.uid}]"

        if self.tile_type == TileType.PRISM_JOKER:
            if self.prism_color is None:
                return f"PJ?[{self.uid}]"
            return f"PJ-{color_map[self.prism_color]}[{self.uid}]"

        return f"UNKNOWN[{self.uid}]"

    def __str__(self) -> str:
        return self.short_label()


@dataclass
class Meld:
    """
    A meld on the board or a candidate meld.
    Validation will be implemented later.
    """
    tiles: List[Tile]
    meld_type: MeldType = MeldType.UNKNOWN
    source: str = "unknown"   # optional: "board", "hand", "candidate"

    def tile_ids(self) -> List[int]:
        return [tile.uid for tile in self.tiles]

    def labels(self) -> List[str]:
        return [tile.short_label() for tile in self.tiles]

    def __len__(self) -> int:
        return len(self.tiles)

    def __str__(self) -> str:
        tile_str = ", ".join(self.labels())
        return f"{self.meld_type.value.upper()}([{tile_str}])"


@dataclass
class PuzzleState:
    """
    Represents one endgame puzzle state.
    """
    board_melds: List[Meld] = field(default_factory=list)
    hand_tiles: List[Tile] = field(default_factory=list)

    def all_board_tiles(self) -> List[Tile]:
        tiles: List[Tile] = []
        for meld in self.board_melds:
            tiles.extend(meld.tiles)
        return tiles

    def all_tiles(self) -> List[Tile]:
        return self.all_board_tiles() + self.hand_tiles

    def all_tile_ids(self) -> List[int]:
        return [tile.uid for tile in self.all_tiles()]

    def has_duplicate_tiles(self) -> bool:
        ids = self.all_tile_ids()
        return len(ids) != len(set(ids))

    def summary(self) -> str:
        board_lines = []
        for i, meld in enumerate(self.board_melds, start=1):
            board_lines.append(f"  Meld {i}: {meld}")

        hand_str = ", ".join(tile.short_label() for tile in self.hand_tiles)
        board_text = "\n".join(board_lines) if board_lines else "  (empty board)"

        return (
            "PuzzleState\n"
            f"Board:\n{board_text}\n"
            f"Hand: [{hand_str}]"
        )

    def __str__(self) -> str:
        return self.summary()


@dataclass
class RuleConfig:
    """
    Stores the fixed game/project rules for implementation.
    """

    # Standard system
    numbers_min: int = 1
    numbers_max: int = 13
    standard_colors: List[TileColor] = field(
        default_factory=lambda: [
            TileColor.RED,
            TileColor.BLUE,
            TileColor.YELLOW,
            TileColor.BLACK
        ]
    )
    duplicate_normal_sets: int = 2

    # Standard Joker
    standard_joker_allowed_in_run: bool = True
    standard_joker_allowed_in_group: bool = True
    multiple_standard_jokers_allowed_per_meld: bool = True
    standard_joker_can_be_replaced_and_moved: bool = True

    # Rainbow King
    rk_allowed_in_run_only: bool = True
    rk_allowed_in_group: bool = False
    rk_cannot_be_at_run_ends: bool = True
    rk_requires_two_neighbors: bool = True
    rk_neighbors_must_have_different_colors: bool = True
    rk_neighbors_value_gap_must_be_two: bool = True
    rk_fills_missing_middle_value: bool = True
    max_rk_per_run: int = 1

    # Prism Joker
    prism_has_fixed_color: bool = True
    prism_allowed_in_run: bool = True
    prism_allowed_in_group: bool = True
    prism_can_appear_at_run_ends: bool = True
    multiple_prisms_allowed_in_run: bool = True

    # Puzzle objective
    must_empty_hand_in_one_turn: bool = True
    final_board_must_be_fully_partitioned_into_legal_melds: bool = True
    unchanged_board_structure_is_allowed: bool = True

