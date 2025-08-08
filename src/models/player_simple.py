"""Simplified Player model for fantasy football draft assistance."""

from dataclasses import dataclass
from typing import Any, Dict

from .injury_status import InjuryStatus


@dataclass
class Player:
    """Core player information with ranking data."""

    name: str
    team: str  # NFL team abbreviation
    position: str  # QB, RB, WR, TE, K, DST
    bye_week: int
    ranking: int  # FantasySharks ranking
    projected_points: float
    injury_status: InjuryStatus = InjuryStatus.HEALTHY
    notes: str = ""

    def __str__(self) -> str:
        """String representation showing key identifying information."""
        return f"{self.name} ({self.position} - {self.team})"

    def __eq__(self, other: object) -> bool:
        """Players are equal if they have the same name, team, and position."""
        if not isinstance(other, Player):
            return NotImplemented
        return (
            self.name == other.name
            and self.team == other.team
            and self.position == other.position
        )

    def __hash__(self) -> int:
        """Hash based on name, team, and position for use in sets/dicts."""
        return hash((self.name, self.team, self.position))

    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "bye_week": self.bye_week,
            "injury_status": self.injury_status.value,
            "ranking": self.ranking,
            "projected_points": self.projected_points,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        """Create player from dictionary, handling missing optional fields."""
        return cls(
            name=data["name"],
            team=data["team"],
            position=data["position"],
            bye_week=data["bye_week"],
            ranking=data["ranking"],
            projected_points=data["projected_points"],
            injury_status=InjuryStatus(data.get("injury_status", "HEALTHY")),
            notes=data.get("notes", ""),
        )
