"""Parser for Dan's draft format (current implementation)."""

import logging
import re
from typing import Dict, List, Optional

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.sheet_parser import ParseError, SheetParser

logger = logging.getLogger(__name__)


class DanDraftParser(SheetParser):
    """Parser for Dan's draft format.

    Expected format:
    - Snake draft with balanced rosters
    - Player names include team abbreviations: "Josh Allen (BUF)"
    - Team names and owners embedded in sheet structure
    - Equal rounds, structured layout
    """

    def detect_format(self, sheet_data: List[List]) -> bool:
        """Detect if sheet data matches Dan's format.

        Dan format characteristics:
        - Has team abbreviations in parentheses in player names
        - Structured team/owner layout with position columns
        """
        if not sheet_data or len(sheet_data) < 5:
            return False

        # Look for owner/team structure in rows 2-3
        if len(sheet_data) > 2:
            owner_row = sheet_data[1] if len(sheet_data) > 1 else []
            team_row = sheet_data[2] if len(sheet_data) > 2 else []

            # Check for alternating owner/position pattern
            owner_count = sum(1 for cell in owner_row[1:] if cell and str(cell).strip())
            team_count = sum(1 for cell in team_row[1:] if cell and str(cell).strip())

            if owner_count > 0 and team_count > 0:
                return True

        return False

    async def parse_draft_data(
        self, sheet_data: List[List], rankings_cache: Optional[Dict] = None
    ) -> DraftState:
        """Parse Dan's format sheet data into DraftState.

        This implements the existing parsing logic from sheets_service.py.
        """
        if not sheet_data:
            raise ParseError("Sheet data is empty")

        if not self.detect_format(sheet_data):
            error_msg = (
                "Sheet data does not match Dan's draft format. "
                "Expected format: Snake draft with team/owner structure and player names with team abbreviations. "
                "Draft analysis may be incomplete or incorrect."
            )
            logger.warning(error_msg)
            raise ParseError(error_msg)

        logger.info("Parsing Dan format draft data")

        try:
            if len(sheet_data) < 5:
                # Return empty DraftState when no data is available
                return DraftState(picks=[], teams=[])

            # Extract team structure from rows 2 and 3 (indices 1 and 2)
            teams = self._extract_teams_and_owners(sheet_data)

            # Parse draft picks from data rows (starting at row 5, index 4)
            picks = self._extract_draft_picks(sheet_data, teams)

            logger.info(
                f"Successfully parsed {len(picks)} picks for {len(teams)} teams"
            )

            return DraftState(picks=picks, teams=teams)

        except Exception as e:
            logger.error(f"Error parsing Dan format draft data: {str(e)}")
            raise ParseError(f"Failed to parse Dan format sheet: {str(e)}")

    def _extract_teams_and_owners(self, sheet_data: List[List]) -> List[Dict]:
        """Extract team and owner information from Dan's format."""
        owner_row = sheet_data[1] if len(sheet_data) > 1 else []
        team_row = sheet_data[2] if len(sheet_data) > 2 else []

        # Parse teams dynamically by scanning for owner/team pairs
        teams = []
        col_idx = 1  # Start from column B

        while col_idx < max(len(owner_row), len(team_row)):
            owner = owner_row[col_idx] if col_idx < len(owner_row) else ""
            team = team_row[col_idx] if col_idx < len(team_row) else ""

            # Clean up the values
            owner = owner.strip() if owner else ""
            team = team.strip() if team else ""

            # Skip empty columns or header-like content
            if (
                not owner
                or not team
                or owner.lower() in ["player", "pos", "position", ""]
                or team.lower() in ["player", "pos", "position", ""]
            ):
                col_idx += 1
                continue

            # Look ahead to see if this is a player/position pair
            next_col = col_idx + 1
            next_owner = owner_row[next_col] if next_col < len(owner_row) else ""
            next_team = team_row[next_col] if next_col < len(team_row) else ""

            # Clean the next column values
            next_owner = next_owner.strip() if next_owner else ""
            next_team = next_team.strip() if next_team else ""

            # Check if the next column is a position column
            # Position columns typically have: empty team name, and owner contains notes/symbols
            is_position_col = not next_team and (  # Team name is empty
                not next_owner  # Owner is empty OR
                or next_owner in ["*", "**", "***", "****"]  # Owner is asterisks OR
                or next_owner.lower()
                in ["pos", "position"]  # Owner is position header OR
                or len(next_owner) <= 5
                and not next_owner.replace("*", "").replace(" ", "").isalpha()
            )  # Short notes/symbols

            if is_position_col:
                teams.append(
                    {
                        "team_number": len(teams) + 1,
                        "owner": owner,
                        "team_name": team,
                        "player_col": col_idx,
                        "position_col": col_idx + 1,
                        "owner_identifier": owner.lower().replace(
                            " ", ""
                        ),  # For matching
                        "team_identifier": team.lower()
                        .replace(" ", "")
                        .replace("'", ""),  # For matching
                        "column_position": col_idx,  # Track original column position for sorting
                    }
                )
                col_idx += 2  # Skip to next team (player + position columns)
            else:
                col_idx += 1

        # Sort teams by column position to establish draft order
        teams.sort(key=lambda x: x["column_position"])

        # Re-number teams after sorting
        for i, team in enumerate(teams):
            team["team_number"] = i + 1

        # Convert to simple format for DraftState
        simple_teams = []
        for team in teams:
            simple_team = {
                "owner": team.get("owner", "Unknown"),
                "team_name": team.get("team_name", "Unknown Team"),
            }
            simple_teams.append(simple_team)

        return simple_teams

    def _extract_draft_picks(
        self, sheet_data: List[List], teams: List[Dict]
    ) -> List[DraftPick]:
        """Extract draft picks from Dan's format."""
        # Rebuild full teams structure for pick extraction
        full_teams = self._rebuild_full_teams_structure(sheet_data)

        picks = []

        # Create a comprehensive list of all picks found in the sheet
        all_sheet_picks = []

        for row_idx in range(4, len(sheet_data)):
            row = sheet_data[row_idx]

            if not row or not row[0] or not str(row[0]).isdigit():
                continue

            round_num = int(row[0])

            # Extract picks for each team column found in this row
            for team in full_teams:
                player_col = team["player_col"]
                pos_col = team["position_col"]

                player = row[player_col] if player_col < len(row) else ""
                position = row[pos_col] if pos_col < len(row) else ""

                # Clean up the data
                player = player.strip() if player else ""
                position = position.strip() if position else ""

                # Skip empty picks or headers
                if not player or player.lower() in ["player", ""]:
                    continue

                all_sheet_picks.append(
                    {
                        "round": round_num,
                        "team_found": team,  # The team column where this pick was found
                        "player_name": player,
                        "position": position,
                        "row_idx": row_idx,
                    }
                )

        # Sort all picks by round and assign pick numbers
        all_sheet_picks.sort(key=lambda x: (x["round"], x["row_idx"]))

        # Now assign pick numbers and determine correct team ownership
        for pick_idx, sheet_pick in enumerate(all_sheet_picks):
            pick_number = pick_idx + 1
            round_num = sheet_pick["round"]

            # Determine which team should have made this pick based on draft rules
            correct_team = self._find_team_by_pick_position(
                full_teams, pick_number, len(full_teams), round_num
            )

            # Use the correct team (from draft logic) rather than just the column position
            if correct_team:
                final_team = correct_team
            else:
                # For auction/keeper rounds, or when logic fails, use the team found in the column
                final_team = sheet_pick["team_found"]

            # Create Player object
            player = self._create_player_from_pick(sheet_pick)

            # Get owner for this pick
            owner = final_team["owner"]

            # Create DraftPick
            draft_pick = DraftPick(player=player, owner=owner)
            picks.append(draft_pick)

        return picks

    def _rebuild_full_teams_structure(self, sheet_data: List[List]) -> List[Dict]:
        """Rebuild the full teams structure needed for pick extraction."""
        owner_row = sheet_data[1] if len(sheet_data) > 1 else []
        team_row = sheet_data[2] if len(sheet_data) > 2 else []

        teams = []
        col_idx = 1  # Start from column B

        while col_idx < max(len(owner_row), len(team_row)):
            owner = owner_row[col_idx] if col_idx < len(owner_row) else ""
            team = team_row[col_idx] if col_idx < len(team_row) else ""

            owner = owner.strip() if owner else ""
            team = team.strip() if team else ""

            if (
                not owner
                or not team
                or owner.lower() in ["player", "pos", "position", ""]
                or team.lower() in ["player", "pos", "position", ""]
            ):
                col_idx += 1
                continue

            next_col = col_idx + 1
            next_owner = owner_row[next_col] if next_col < len(owner_row) else ""
            next_team = team_row[next_col] if next_col < len(team_row) else ""

            next_owner = next_owner.strip() if next_owner else ""
            next_team = next_team.strip() if next_team else ""

            is_position_col = not next_team and (
                not next_owner
                or next_owner in ["*", "**", "***", "****"]
                or next_owner.lower() in ["pos", "position"]
                or len(next_owner) <= 5
                and not next_owner.replace("*", "").replace(" ", "").isalpha()
            )

            if is_position_col:
                teams.append(
                    {
                        "team_number": len(teams) + 1,
                        "owner": owner,
                        "team_name": team,
                        "player_col": col_idx,
                        "position_col": col_idx + 1,
                        "column_position": col_idx,
                    }
                )
                col_idx += 2
            else:
                col_idx += 1

        teams.sort(key=lambda x: x["column_position"])
        for i, team in enumerate(teams):
            team["team_number"] = i + 1

        return teams

    def _find_team_by_pick_position(
        self, teams: List[Dict], pick_number: int, total_teams: int, round_num: int
    ) -> Optional[Dict]:
        """Find which team should make a pick based on snake draft logic."""
        if not teams or total_teams == 0:
            return None

        # Snake draft logic: odd rounds go 1->N, even rounds go N->1
        pick_in_round = ((pick_number - 1) % total_teams) + 1

        if round_num % 2 == 1:  # Odd round
            team_index = pick_in_round - 1
        else:  # Even round (snake back)
            team_index = total_teams - pick_in_round

        if 0 <= team_index < len(teams):
            return teams[team_index]

        return None

    def _create_player_from_pick(self, pick_data: Dict) -> Player:
        """Create Player object from pick data."""
        player_name = pick_data["player_name"]
        position = pick_data["position"]

        # Parse team from player name if it includes team info like "Josh Allen (BUF)"
        name, team = self._parse_player_info(player_name)

        return Player(
            name=name,
            team=team,
            position=position,
            bye_week=0,  # Not available from sheet
            ranking=0,  # Not available from sheet
            projected_points=0.0,  # Not available from sheet
            injury_status=InjuryStatus.HEALTHY,
            notes="",
        )

    def _parse_player_info(self, player_cell: str) -> tuple[str, str]:
        """Parse player name and team from cell with team abbreviation.

        Handles patterns like:
        - "Isiah Pacheco   KC" (multiple spaces)
        - "DJ Moore -  CHI" (space-hyphen-space)
        - "Player Name  -  TEAM" (various spacing around hyphen)
        """
        if not player_cell:
            return "", "UNK"

        # Match team abbreviation at the end with flexible separators
        match = re.search(r"[\s\-]+([A-Z]{2,3})\s*$", player_cell.strip())

        if match:
            team = match.group(1)  # Extract team abbreviation
            clean_name = player_cell[: match.start()].strip()  # Remove team from name
        else:
            team = "UNK"  # No team found
            clean_name = player_cell.strip()

        return clean_name, team
