"""Simplified DraftState model for fantasy football draft tracking."""

from pydantic import BaseModel
from typing import Any, Dict, List, Set

from .draft_pick import DraftPick
from .player_simple import Player


class DraftState(BaseModel):
    """Represents the current state of the draft."""
    
    model_config = {"extra": "allow"}  # Allow additional attributes for metadata

    picks: List[DraftPick]  # All picks made so far
    teams: List[Dict[str, Any]]  # Team/owner pairs: [{"owner": str, "team_name": str}]

    def get_picks_by_owner(self, owner: str) -> List[DraftPick]:
        """Get all picks for a specific owner."""
        return [pick for pick in self.picks if pick.owner == owner]

    def get_drafted_players(self) -> Set[Player]:
        """Get set of all drafted players."""
        return {pick.player for pick in self.picks}

    def is_player_drafted(self, player: Player) -> bool:
        """Check if a specific player has been drafted."""
        return player in self.get_drafted_players()

    def to_dict(self) -> Dict[str, Any]:
        """Convert draft state to dictionary for JSON serialization.
        
        Note: This method is deprecated. Use model_dump() instead for Pydantic v2.
        """
        return {
            "teams": self.teams,
            "picks": [pick.to_dict() for pick in self.picks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DraftState":
        """Create draft state from dictionary.
        
        Note: This method is deprecated. Use DraftState(**data) or DraftState.model_validate(data) instead.
        """
        return cls.model_validate(data)
