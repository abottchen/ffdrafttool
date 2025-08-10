"""Parser for Adam's draft format (auction draft)."""

import logging
from typing import Dict, List, Optional

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.sheet_parser import ParseError, SheetParser

logger = logging.getLogger(__name__)


class AdamDraftParser(SheetParser):
    """Parser for Adam's draft format.

    Expected format:
    - Auction draft with unequal rosters
    - Player names in "Last, First" format without team abbreviations
    - Defense format: "Ravens D/ST" with full team name
    - Alternating Player/$ columns for auction values
    - Owner names in first row
    """

    def __init__(self, rankings_cache: Optional[Dict] = None):
        """Initialize with optional rankings cache for team lookup."""
        self.rankings_cache = rankings_cache or {}

    def detect_format(self, sheet_data: List[List]) -> bool:
        """Detect if sheet data matches Adam's format.

        Adam format characteristics:
        - Owner names in first row
        - "Player" and "$" headers in second row
        - Player names in "Last, First" format (no team abbreviations)
        - Defense format like "Ravens D/ST"
        """
        if not sheet_data or len(sheet_data) < 2:
            return False

        # Check for alternating Player/$ pattern in row 2 (index 1)
        if len(sheet_data) > 1:
            header_row = sheet_data[1]
            player_count = sum(
                1
                for cell in header_row
                if cell and str(cell).strip().lower() == "player"
            )
            dollar_count = sum(
                1 for cell in header_row if cell and str(cell).strip() == "$"
            )

            # Should have roughly equal Player/$ columns
            if (
                player_count > 0
                and dollar_count > 0
                and abs(player_count - dollar_count) <= 1
            ):
                # If no data rows exist, accept based on headers alone
                if len(sheet_data) <= 2:
                    return True

                # Check for Adam format characteristics in player data
                for row_idx in range(
                    2, min(len(sheet_data), 5)
                ):  # Check first few data rows
                    row = sheet_data[row_idx]
                    for cell in row:
                        if cell and isinstance(cell, str) and not cell.startswith("$"):
                            # Adam format has either "Last, First" names or "Team D/ST" defenses
                            if "," in cell or "D/ST" in cell:
                                return True

                # If we have Player/$ headers but no recognizable data, still accept
                # This allows for empty sheets or sheets with only unfamiliar formats
                return True

        return False

    async def parse_draft_data(
        self, sheet_data: List[List], rankings_cache: Optional[Dict] = None
    ) -> DraftState:
        """Parse Adam's format sheet data into DraftState.

        This handles auction draft format with "Last, First" names and team lookup.
        """
        if not sheet_data:
            raise ParseError("Sheet data is empty")

        if not self.detect_format(sheet_data):
            error_msg = (
                "Sheet data does not match Adam's draft format. "
                "Expected format: Auction draft with 'Last, First' names and Player/$ columns. "
                "Draft analysis may be incomplete or incorrect."
            )
            logger.warning(error_msg)
            raise ParseError(error_msg)

        logger.info("Parsing Adam format draft data")

        # Update rankings cache if provided
        if rankings_cache:
            self.rankings_cache.update(rankings_cache)

        # Ensure rankings cache is populated for team/position lookup
        await self._ensure_rankings_cache_populated()

        try:
            # Extract team/owner structure from rows 1 and 2 (indices 0 and 1)
            teams = self._extract_teams_and_owners(sheet_data)

            # Parse draft picks from data rows (starting at row 3, index 2) if they exist
            if len(sheet_data) >= 3:
                picks = self._extract_draft_picks(sheet_data, teams)
            else:
                # No data rows, only headers - return empty picks with valid teams
                picks = []

            logger.info(
                f"Successfully parsed {len(picks)} picks for {len(teams)} teams"
            )

            return DraftState(picks=picks, teams=teams)

        except Exception as e:
            logger.error(f"Error parsing Adam format draft data: {str(e)}")
            raise ParseError(f"Failed to parse Adam format sheet: {str(e)}")

    def _extract_teams_and_owners(self, sheet_data: List[List]) -> List[Dict]:
        """Extract team and owner information from Adam's format."""
        owner_row = sheet_data[0] if len(sheet_data) > 0 else []
        header_row = sheet_data[1] if len(sheet_data) > 1 else []

        teams = []
        col_idx = 0

        while col_idx < len(owner_row):
            owner = owner_row[col_idx] if col_idx < len(owner_row) else ""
            header = header_row[col_idx] if col_idx < len(header_row) else ""

            # Clean up the values
            owner = owner.strip() if owner else ""
            header = header.strip() if header else ""

            # Look for "Player" column headers to identify team columns
            if header.lower() == "player" and owner:
                teams.append(
                    {
                        "owner": owner,
                        "team_name": f"{owner}'s Team",  # Generate team name from owner
                        "player_col": col_idx,
                        "value_col": col_idx
                        + 1,  # Assuming $ column follows Player column
                        "column_position": col_idx,
                    }
                )

            col_idx += 1

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
        """Extract draft picks from Adam's format."""
        # Rebuild team structure for pick extraction
        full_teams = self._rebuild_full_teams_structure(sheet_data)

        picks = []

        # Extract picks from data rows (starting at row 3, index 2)
        for row_idx in range(2, len(sheet_data)):
            row = sheet_data[row_idx]

            # Extract picks for each team column found in this row
            for team in full_teams:
                player_col = team["player_col"]

                player = row[player_col] if player_col < len(row) else ""

                # Clean up the data
                player = player.strip() if player else ""

                # Skip empty picks
                if not player:
                    continue

                # Create Player object from pick
                player_obj = self._create_player_from_pick(player)

                # Create DraftPick
                draft_pick = DraftPick(player=player_obj, owner=team["owner"])
                picks.append(draft_pick)

        return picks

    def _rebuild_full_teams_structure(self, sheet_data: List[List]) -> List[Dict]:
        """Rebuild the full teams structure needed for pick extraction."""
        owner_row = sheet_data[0] if len(sheet_data) > 0 else []
        header_row = sheet_data[1] if len(sheet_data) > 1 else []

        teams = []
        col_idx = 0

        while col_idx < len(owner_row):
            owner = owner_row[col_idx] if col_idx < len(owner_row) else ""
            header = header_row[col_idx] if col_idx < len(header_row) else ""

            owner = owner.strip() if owner else ""
            header = header.strip() if header else ""

            if header.lower() == "player" and owner:
                teams.append(
                    {
                        "owner": owner,
                        "team_name": f"{owner}'s Team",
                        "player_col": col_idx,
                        "value_col": col_idx + 1,
                        "column_position": col_idx,
                    }
                )

            col_idx += 1

        return teams

    def _create_player_from_pick(self, player_name: str) -> Player:
        """Create Player object from pick data with name reversal and team lookup."""
        # Reverse "Last, First" to "First Last" format
        normalized_name = self._reverse_player_name(player_name)

        # Handle defense format
        if self._is_defense(player_name):
            team_abbrev, position = self._parse_defense(player_name)
        else:
            # Look up team from rankings cache
            team_abbrev = self._lookup_team_from_cache(normalized_name)
            position = self._lookup_position_from_cache(normalized_name)

        return Player(
            name=normalized_name,
            team=team_abbrev,
            position=position,
            bye_week=0,  # Not available from sheet
            ranking=0,  # Not available from sheet
            projected_points=0.0,  # Not available from sheet
            injury_status=InjuryStatus.HEALTHY,
            notes="",
        )

    def _reverse_player_name(self, player_name: str) -> str:
        """Reverse 'Last, First' format to 'First Last' format.

        Handles patterns like:
        - "Hall, Breece" → "Breece Hall"
        - "McCaffrey, Christian" → "Christian McCaffrey"
        - "Harrison Jr., Marvin" → "Marvin Harrison Jr."
        """
        if not player_name or "," not in player_name:
            return player_name.strip()

        # Handle defense format separately
        if self._is_defense(player_name):
            return player_name.strip()

        # Split on comma and reverse
        parts = [part.strip() for part in player_name.split(",", 1)]
        if len(parts) == 2:
            last_name = parts[0]
            first_name = parts[1]
            return f"{first_name} {last_name}"

        return player_name.strip()

    def _is_defense(self, player_name: str) -> bool:
        """Check if the player name represents a defense."""
        return "D/ST" in player_name or player_name.endswith(" D/ST")

    def _parse_defense(self, defense_name: str) -> tuple[str, str]:
        """Parse defense name to extract team abbreviation.

        Examples:
        - "Ravens D/ST" → ("BAL", "DST")
        - "Steelers D/ST" → ("PIT", "DST")
        """
        # Map common defense names to abbreviations
        defense_mapping = {
            "ravens": "BAL",
            "steelers": "PIT",
            "bills": "BUF",
            "cowboys": "DAL",
            "saints": "NO",
            "bears": "CHI",
            "jets": "NYJ",
            "colts": "IND",
            "dolphins": "MIA",
            "browns": "CLE",
            "49ers": "SF",
        }

        defense_name = defense_name.lower().replace(" d/st", "")
        team_abbrev = defense_mapping.get(defense_name, "UNK")

        return team_abbrev, "DST"

    def _lookup_team_from_cache(self, player_name: str) -> str:
        """Look up team abbreviation from rankings cache."""
        if not self.rankings_cache:
            return "UNK"

        # Search through all positions in rankings cache
        for position_data in self.rankings_cache.values():
            if isinstance(position_data, dict) and "players" in position_data:
                for player in position_data["players"]:
                    if player.get("name", "").lower() == player_name.lower():
                        return player.get("team", "UNK")

        return "UNK"

    def _lookup_position_from_cache(self, player_name: str) -> str:
        """Look up position from rankings cache."""
        if not self.rankings_cache:
            return "FLEX"

        # Search through all positions in rankings cache
        for position, position_data in self.rankings_cache.items():
            if isinstance(position_data, dict) and "players" in position_data:
                for player in position_data["players"]:
                    if player.get("name", "").lower() == player_name.lower():
                        return position.upper()

        return "FLEX"

    async def _ensure_rankings_cache_populated(self):
        """Ensure rankings cache is populated for all positions.

        This method checks if the rankings cache has data and populates it
        if empty. This is needed for team/position lookup during parsing.
        """
        from src.tools.player_rankings import get_player_rankings

        # Define the positions we need rankings for
        positions = ["QB", "RB", "WR", "TE", "K", "DST"]

        # Check if cache needs population (either empty or missing key positions)
        needs_population = not self.rankings_cache or not any(
            pos in self.rankings_cache for pos in positions
        )

        if needs_population:
            logger.info(
                "Rankings cache is empty or incomplete, populating with all positions"
            )

            for position in positions:
                try:
                    logger.debug(f"Fetching rankings for position: {position}")
                    result = await get_player_rankings(
                        position=position, force_refresh=False
                    )

                    if result.get("success") and "players" in result:
                        # Store the position data in our cache
                        self.rankings_cache[position] = {
                            "players": result["players"],
                            "position": position,
                        }
                        logger.debug(
                            f"Cached {len(result['players'])} players for {position}"
                        )
                    else:
                        logger.warning(
                            f"Failed to fetch rankings for {position}: {result.get('error', 'Unknown error')}"
                        )

                except Exception as e:
                    logger.error(f"Error fetching rankings for {position}: {e}")
                    continue

            total_players = sum(
                len(pos_data.get("players", []))
                for pos_data in self.rankings_cache.values()
                if isinstance(pos_data, dict)
            )
            logger.info(
                f"Rankings cache population complete. Cached {total_players} players across {len(positions)} positions"
            )
        else:
            logger.debug("Rankings cache already populated, skipping population")
