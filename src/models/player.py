"""Enums for fantasy football positions and ranking sources."""

from enum import Enum


class Position(Enum):
    """Fantasy football positions."""

    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DST = "DST"
    FLEX = "FLEX"  # Flex position (RB/WR/TE eligible)
    BE = "BE"  # Bench
    IR = "IR"  # Injured Reserve


class RankingSource(Enum):
    """Sources for fantasy football rankings."""

    ESPN = "ESPN"
    YAHOO = "YAHOO"
    CBS = "CBS"
    FANTASYPROS = "FANTASYPROS"
    OTHER = "OTHER"
