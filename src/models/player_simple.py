"""Simplified Player model for fantasy football draft assistance."""

from typing import Any, Dict

from pydantic import BaseModel, Field

from .injury_status import InjuryStatus


class Player(BaseModel):
    """Core player information with ranking data."""

    name: str
    team: str  # NFL team abbreviation
    position: str  # QB, RB, WR, TE, K, DST
    bye_week: int
    ranking: int  # FantasySharks ranking
    projected_points: float
    injury_status: InjuryStatus = Field(default=InjuryStatus.HEALTHY)
    notes: str = Field(default="")

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
        """Convert player to dictionary for JSON serialization.

        Note: This method is deprecated. Use model_dump() instead for Pydantic v2.
        """
        result = self.model_dump()
        # Ensure injury_status is serialized as string for backward compatibility
        result["injury_status"] = self.injury_status.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        """Create player from dictionary, handling missing optional fields.

        Note: This method is deprecated. Use Player(**data) or Player.model_validate(data) instead.
        """
        return cls.model_validate(data)
