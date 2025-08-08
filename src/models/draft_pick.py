"""DraftPick model for fantasy football draft tracking."""

from dataclasses import dataclass
from typing import Any, Dict

from .player_simple import Player


@dataclass
class DraftPick:
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
        """Convert draft pick to dictionary for JSON serialization."""
        return {
            "owner": self.owner,
            "player": self.player.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DraftPick":
        """Create draft pick from dictionary."""
        return cls(
            owner=data["owner"],
            player=Player.from_dict(data["player"]),
        )