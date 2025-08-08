"""Adapter to convert sheets data to simplified models."""

from typing import Any, Dict

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player


class SheetsAdapter:
    """Converts sheets service data to simplified DraftState models."""

    def convert_to_draft_state(self, sheets_data: Dict[str, Any]) -> DraftState:
        """Convert sheets data format to simplified DraftState.

        Args:
            sheets_data: Data in the format returned by read_draft_progress

        Returns:
            DraftState: Converted draft state with simplified models

        Raises:
            ValueError: If sheets_data indicates failure
        """
        if not sheets_data.get("success", False):
            error_msg = sheets_data.get("error", "Unknown sheets error")
            raise ValueError(f"Sheets data conversion failed: {error_msg}")

        # Extract teams and create mapping
        teams = sheets_data.get("teams", [])
        picks_data = sheets_data.get("picks", [])

        # Create team name to owner mapping for picks
        team_to_owner = {}
        for team in teams:
            team_name = team.get("team_name", "")
            owner = team.get("owner", "Unknown")
            if team_name:
                team_to_owner[team_name] = owner

        # Convert picks to DraftPick objects
        picks = []
        for pick_data in picks_data:
            player = self._create_player_from_pick(pick_data)
            owner = self._get_owner_for_pick(pick_data, team_to_owner)

            draft_pick = DraftPick(player=player, owner=owner)
            picks.append(draft_pick)

        # Convert teams to simple dictionaries
        simple_teams = []
        for team in teams:
            simple_team = {
                "owner": team.get("owner", "Unknown"),
                "team_name": team.get("team_name", "Unknown Team"),
            }
            simple_teams.append(simple_team)

        return DraftState(picks=picks, teams=simple_teams)

    def _create_player_from_pick(self, pick_data: Dict[str, Any]) -> Player:
        """Create a Player object from pick data.

        Args:
            pick_data: Pick data from sheets

        Returns:
            Player: Simplified player object with defaults for missing data
        """
        name = pick_data.get("player_name", "Unknown Player")
        position = pick_data.get("position", "UNK")

        # Default values for data not available in sheets
        team = "UNK"  # NFL team not available in draft sheets
        bye_week = 1  # Default bye week
        ranking = 999  # Default ranking for unknown players
        projected_points = 0.0  # Default projection
        injury_status = InjuryStatus.HEALTHY  # Default to healthy
        notes = ""  # No notes from sheets

        return Player(
            name=name,
            team=team,
            position=position,
            bye_week=bye_week,
            ranking=ranking,
            projected_points=projected_points,
            injury_status=injury_status,
            notes=notes,
        )

    def _get_owner_for_pick(
        self, pick_data: Dict[str, Any], team_to_owner: Dict[str, str]
    ) -> str:
        """Get the owner for a pick based on column_team mapping.

        Args:
            pick_data: Pick data from sheets
            team_to_owner: Mapping from team name to owner

        Returns:
            str: Owner name or "Unknown" if not found
        """
        column_team = pick_data.get("column_team", "")

        # Try to find owner by team name
        if column_team and column_team in team_to_owner:
            return team_to_owner[column_team]

        # Fallback to "Unknown" if no mapping found
        return "Unknown"
