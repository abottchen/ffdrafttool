"""
Standardized dataclasses for test data structures.

This module provides clean, type-safe dataclasses for creating test data
instead of manually constructing dictionaries.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Pick:
    """Represents a single draft pick."""
    pick_number: int
    round: int
    team: str
    player: str  # Can be "player" or "player_name" depending on context
    position: str
    pick_in_round: Optional[int] = None
    owner: Optional[str] = None
    player_name: Optional[str] = None  # Alternative field name
    bye_week: Optional[int] = None
    column_team: Optional[str] = None  # For sheets format

    def __post_init__(self):
        """Handle field name variations after initialization."""
        # Standardize player field - use player_name if player is empty
        if not self.player and self.player_name:
            self.player = self.player_name
        elif not self.player_name and self.player:
            self.player_name = self.player
            
        # Use column_team as team if team is empty
        if not self.team and self.column_team:
            self.team = self.column_team

    @classmethod
    def builder(cls):
        """Return a builder for this pick."""
        return PickBuilder()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class Team:
    """Represents a team in the draft."""
    team_name: str
    owner: str
    team_number: Optional[int] = None
    player_col: Optional[int] = None
    position_col: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class DraftRules:
    """Represents draft rules configuration."""
    auction_rounds: List[int] = field(default_factory=lambda: [1, 2, 3])
    keeper_round: int = 4
    snake_start_round: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


@dataclass
class DraftStateInfo:
    """Represents draft state metadata."""
    total_picks: int
    total_teams: int
    current_round: int
    completed_rounds: int = 0
    draft_rules: DraftRules = field(default_factory=DraftRules)
    current_pick: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = asdict(self)
        result["draft_rules"] = self.draft_rules.to_dict()
        return result


@dataclass
class DraftData:
    """Main draft data container."""
    picks: List[Pick]
    draft_state: DraftStateInfo
    teams: List[Team] = field(default_factory=list)
    current_team: Optional[Team] = None

    @classmethod
    def builder(cls):
        """Return a builder for this draft data."""
        return DraftDataBuilder()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format that matches current API expectations."""
        result = {
            "picks": [pick.to_dict() for pick in self.picks],
            "draft_state": self.draft_state.to_dict(),
        }
        
        if self.teams:
            result["teams"] = [team.to_dict() for team in self.teams]
            
        if self.current_team:
            result["current_team"] = self.current_team.to_dict()
            
        return result


class PickBuilder:
    """Builder for Pick objects."""
    
    def __init__(self):
        self._pick_number = 0
        self._round = 0
        self._team = ""
        self._player = ""
        self._position = ""
        self._pick_in_round = None
        self._owner = None
        self._player_name = None
        self._bye_week = None
        self._column_team = None

    def pick_number(self, value: int):
        self._pick_number = value
        return self

    def round(self, value: int):
        self._round = value
        return self

    def team(self, value: str):
        self._team = value
        return self

    def player(self, value: str):
        self._player = value
        return self

    def position(self, value: str):
        self._position = value
        return self

    def pick_in_round(self, value: int):
        self._pick_in_round = value
        return self

    def owner(self, value: str):
        self._owner = value
        return self

    def player_name(self, value: str):
        self._player_name = value
        return self

    def bye_week(self, value: int):
        self._bye_week = value
        return self

    def column_team(self, value: str):
        self._column_team = value
        return self

    def build(self) -> Pick:
        return Pick(
            pick_number=self._pick_number,
            round=self._round,
            team=self._team,
            player=self._player,
            position=self._position,
            pick_in_round=self._pick_in_round,
            owner=self._owner,
            player_name=self._player_name,
            bye_week=self._bye_week,
            column_team=self._column_team,
        )


class DraftDataBuilder:
    """Builder for DraftData objects."""
    
    def __init__(self):
        self._picks: List[Pick] = []
        self._teams: List[Team] = []
        self._current_team: Optional[Team] = None
        self._draft_state: Optional[DraftStateInfo] = None

    def add_pick(self, pick: Pick):
        self._picks.append(pick)
        return self

    def add_team(self, team: Team):
        self._teams.append(team)
        return self

    def current_team(self, team: Team):
        self._current_team = team
        return self

    def draft_state(self, draft_state: DraftStateInfo):
        self._draft_state = draft_state
        return self

    def with_standard_auction_rules(self, total_teams: int = 10, current_round: int = 1):
        """Add standard auction draft rules."""
        self._draft_state = DraftStateInfo(
            total_picks=len(self._picks),
            total_teams=total_teams,
            current_round=current_round,
            completed_rounds=current_round - 1,
            draft_rules=DraftRules(
                auction_rounds=[1, 2, 3],
                keeper_round=4,
                snake_start_round=5,
            ),
        )
        return self

    def build(self) -> DraftData:
        if self._draft_state is None:
            # Provide default draft state
            self._draft_state = DraftStateInfo(
                total_picks=len(self._picks),
                total_teams=10,
                current_round=1,
                completed_rounds=0,
            )
        
        return DraftData(
            picks=self._picks,
            draft_state=self._draft_state,
            teams=self._teams,
            current_team=self._current_team,
        )


# Convenience factory functions for common test scenarios
def create_basic_pick(
    pick_number: int, 
    round: int, 
    team: str, 
    player: str, 
    position: str,
    **kwargs
) -> Pick:
    """Create a basic pick with minimal required fields."""
    return Pick(
        pick_number=pick_number,
        round=round,
        team=team,
        player=player,
        position=position,
        **kwargs
    )


def create_auction_draft_data(picks: List[Pick], teams: List[Team] = None) -> DraftData:
    """Create draft data with standard auction rules."""
    return (DraftDataBuilder()
            .with_standard_auction_rules(current_round=1)
            .build())


def create_sample_teams() -> List[Team]:
    """Create sample teams for testing."""
    return [
        Team(team_name="Team Alpha", owner="Alice", team_number=1),
        Team(team_name="Team Beta", owner="Bob", team_number=2),
        Team(team_name="Team Gamma", owner="Charlie", team_number=3),
        Team(team_name="Test Team", owner="Test Owner", team_number=4),
    ]