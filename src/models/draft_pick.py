"""DraftPick model for fantasy football draft tracking."""

from typing import Any, Dict

from pydantic import BaseModel

from .player_simple import Player


class DraftPick(BaseModel):
    """Represents a single draft pick - player and owner."""

    player: Player
    owner: str  # Fantasy owner who drafted the player

    def __str__(self) -> str:
        """String representation showing owner and player."""
        return f"{self.owner}: {self.player}"

    def __eq__(self, other: object) -> bool:
        """Draft picks are equal if they have the same player and owner."""
        if not isinstance(other, DraftPick):
            return NotImplemented
        return self.player == other.player and self.owner == other.owner

    def __hash__(self) -> int:
        """Hash based on player and owner for use in sets/dicts."""
        return hash((self.player, self.owner))

    def to_dict(self) -> Dict[str, Any]:
        """Convert draft pick to dictionary for JSON serialization.

        Note: This method is deprecated. Use model_dump() instead for Pydantic v2.
        """
        return {
            "owner": self.owner,
            "player": self.player.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DraftPick":
        """Create draft pick from dictionary.

        Note: This method is deprecated. Use DraftPick(**data) or DraftPick.model_validate(data) instead.
        """
        return cls.model_validate(data)
