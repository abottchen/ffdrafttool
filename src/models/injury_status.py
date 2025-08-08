"""Injury status enumeration for fantasy football players."""

from enum import Enum


class InjuryStatus(Enum):
    """Player injury status based on standard NFL designations."""
    
    HEALTHY = "HEALTHY"
    QUESTIONABLE = "Q"
    DOUBTFUL = "D"
    OUT = "O"
    INJURED_RESERVE = "IR"