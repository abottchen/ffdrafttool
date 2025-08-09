import asyncio
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.team_mapping import normalize_team_abbreviation

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SheetsProvider(ABC):
    """Abstract base class for Google Sheets providers"""

    @abstractmethod
    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Read data from a sheet range"""
        pass


class GoogleSheetsProvider(SheetsProvider):
    """Real Google Sheets provider using Google Sheets API"""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(
        self, credentials_file: Optional[str] = None, token_file: Optional[str] = None
    ):
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API dependencies not available. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        # Use absolute paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        default_creds = project_root / "credentials.json"
        default_token = project_root / "token.json"

        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CREDENTIALS_FILE", str(default_creds)
        )
        self.token_file = token_file or os.getenv(
            "GOOGLE_TOKEN_FILE", str(default_token)
        )
        self.service = None
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def _get_service(self):
        """Get authenticated Google Sheets service"""
        if self.service:
            return self.service

        def _auth():
            creds = None

            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(
                    self.token_file, self.SCOPES
                )

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Google credentials file not found: {self.credentials_file}"
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())

            return build("sheets", "v4", credentials=creds)

        # Run authentication in thread pool to avoid blocking
        self.service = await asyncio.get_event_loop().run_in_executor(
            self.executor, _auth
        )
        return self.service

    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Read data from Google Sheets"""
        try:
            service = await self._get_service()

            def _read():
                result = (
                    service.spreadsheets()
                    .values()
                    .get(spreadsheetId=sheet_id, range=range_name)
                    .execute()
                )
                return result.get("values", [])

            # Execute API call in thread pool
            values = await asyncio.get_event_loop().run_in_executor(
                self.executor, _read
            )
            logger.info(
                f"Successfully read {len(values)} rows from sheet {sheet_id}, range {range_name}"
            )
            return values

        except Exception as e:
            logger.error(f"Error reading from Google Sheets: {str(e)}")
            raise


class SheetsService:
    """Service for interacting with Google Sheets"""

    def __init__(
        self,
        provider: SheetsProvider,
        use_cache: bool = True,
    ):
        self.provider = provider
        # Cache simplified - draft_cache was removed in refactoring
        self.cache = None

    def _extract_player_info(self, raw_name: str) -> Tuple[str, str]:
        """Extract player name and team from raw name with team abbreviation.

        Args:
            raw_name: Raw player name from sheets (may include team like "Josh Allen   BUF" or "Kendrick Bourne - NE")

        Returns:
            tuple[str, str]: (clean_player_name, team_abbreviation)
        """
        # Match team abbreviation at the end with flexible separators
        # Handles patterns like:
        # - "Josh Allen   BUF" (multiple spaces)
        # - "Kendrick Bourne - NE" (space-hyphen-space)
        # - "Player Name  -  TEAM" (various spacing around hyphen)
        match = re.search(r"[\s\-]+([A-Z]{2,3})\s*$", raw_name)

        if match:
            team = match.group(1)  # Extract team abbreviation
            clean_name = raw_name[: match.start()].strip()  # Remove team from name
        else:
            team = "UNK"  # No team found
            clean_name = raw_name.strip()
            # Log error when team cannot be determined from draft data
            logger.error(
                f"Unable to extract NFL team from player name in draft data: '{raw_name}'. "
                f"Player will be marked with team 'UNK'. This may affect player matching and analysis."
            )

        return clean_name, team

    def _create_player_from_pick(self, pick_data: Dict[str, Any]) -> Player:
        """Create a Player object from pick data.

        Args:
            pick_data: Pick data from sheets

        Returns:
            Player: Simplified player object with defaults for missing data
        """
        raw_name = pick_data.get("player_name", "Unknown Player")
        name, raw_team = self._extract_player_info(raw_name)
        position = pick_data.get("position", "UNK")

        # Normalize team abbreviation (sheets use "normal" format, so pass through)
        team = normalize_team_abbreviation(raw_team, source="sheets")

        # Default values for data not available in sheets (team is extracted from name)
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

    def _find_team_by_pick_position(
        self,
        teams: List[Dict],
        pick_number: int,
        total_teams: int,
        round_num: int = None,
    ) -> Optional[Dict]:
        """
        Find which team should be making a specific pick based on draft rules.
        This provides a fallback when team identification by column position fails.
        """
        if not teams or total_teams == 0:
            return None

        # If we don't have round number, try to calculate it (legacy behavior)
        if round_num is None:
            round_num = ((pick_number - 1) // total_teams) + 1

        # Simplified: For now, just use basic snake logic for all rounds
        # Complex draft rules (auction/keeper) belong in MCP client analysis
        pick_in_round = ((pick_number - 1) % total_teams) + 1

        if round_num % 2 == 1:  # Odd round: 1→total_teams
            team_idx = pick_in_round - 1
        else:  # Even round: total_teams→1
            team_idx = total_teams - pick_in_round

        if 0 <= team_idx < len(teams):
            return teams[team_idx]

        return None

    async def read_draft_data(
        self, sheet_id: str, range_name: str, force_refresh: bool = False
    ) -> DraftState:
        """Read and parse draft data from sheets using team-column structure with intelligent caching"""
        try:
            # Determine if we can use incremental reading
            if self.cache:
                use_incremental, first_round_to_read = (
                    self.cache.should_use_incremental_read(
                        sheet_id, range_name, force_refresh
                    )
                )

                if use_incremental:
                    # We have cached data, try incremental read
                    cached_state = self.cache.get_cached_state(sheet_id, range_name)
                    if cached_state:
                        logger.info(
                            f"Attempting incremental read from round {first_round_to_read}"
                        )
                        incremental_range = self.cache.get_incremental_range(
                            sheet_id, range_name, first_round_to_read
                        )

                        try:
                            incremental_data = await self.provider.read_range(
                                sheet_id, incremental_range
                            )
                            if incremental_data and len(incremental_data) > 0:
                                # Parse the incremental data and merge with cache
                                new_picks = self._parse_incremental_picks(
                                    incremental_data, first_round_to_read
                                )
                                merged_state = self.cache.merge_incremental_data(
                                    sheet_id, cached_state, new_picks
                                )

                                # Update cache with merged state
                                self.cache.update_cache(
                                    sheet_id, range_name, merged_state
                                )
                                logger.info(
                                    f"Successfully merged {len(new_picks)} new picks with cached data"
                                )
                                return merged_state
                            else:
                                logger.info("No new data found, returning cached state")
                                return cached_state
                        except Exception as e:
                            logger.warning(
                                f"Incremental fetch failed, falling back to full fetch: {e}"
                            )

            # Full fetch (either no cache, force refresh, or incremental failed)
            logger.info(f"Performing full fetch for {sheet_id} range {range_name}")
            data = await self.provider.read_range(sheet_id, range_name)

            if not data or len(data) < 5:
                # Return empty DraftState when no data is available
                return DraftState(picks=[], teams=[])

            # Extract team structure from rows 2 and 3 (indices 1 and 2)
            owner_row = data[1] if len(data) > 1 else []
            team_row = data[2] if len(data) > 2 else []

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
            # The draft order is determined by the left-to-right column order in the sheet
            teams.sort(key=lambda x: x["column_position"])

            # Re-number teams after sorting
            for i, team in enumerate(teams):
                team["team_number"] = i + 1

            # Extract picks starting from row 5 (index 4)
            picks = []

            # Create a comprehensive list of all picks found in the sheet
            # We'll determine which team made each pick later
            all_sheet_picks = []

            for row_idx in range(4, len(data)):
                row = data[row_idx]

                if not row or not row[0] or not str(row[0]).isdigit():
                    continue

                round_num = int(row[0])

                # Extract picks for each team column found in this row
                for team in teams:
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
                    teams, pick_number, len(teams), round_num
                )

                # Use the correct team (from draft logic) rather than just the column position
                if correct_team:
                    final_team = correct_team
                else:
                    # For auction/keeper rounds, or when logic fails, use the team found in the column
                    final_team = sheet_pick["team_found"]

                # Calculate pick in round
                pick_in_round = ((pick_number - 1) % len(teams)) + 1

                picks.append(
                    {
                        "pick_number": pick_number,
                        "round": round_num,
                        "pick_in_round": pick_in_round,
                        "team": final_team["team_name"],
                        "owner": final_team["owner"],
                        "player_name": sheet_pick["player_name"],
                        "position": sheet_pick["position"],
                        "column_team": sheet_pick["team_found"][
                            "team_name"
                        ],  # Track which column it came from for debugging
                    }
                )

            # Sort by pick number
            picks.sort(key=lambda x: x["pick_number"])

            # Create team name to owner mapping for DraftPick creation
            team_to_owner = {}
            for team in teams:
                team_name = team.get("team_name", "")
                owner = team.get("owner", "Unknown")
                if team_name:
                    team_to_owner[team_name] = owner

            # Convert picks to DraftPick objects with Player models
            draft_picks = []
            for pick_data in picks:
                # Create Player object
                player = self._create_player_from_pick(pick_data)

                # Get owner for this pick
                owner = self._get_owner_for_pick(pick_data, team_to_owner)

                # Create DraftPick
                draft_pick = DraftPick(player=player, owner=owner)
                draft_picks.append(draft_pick)

            # Convert teams to simple dictionaries for DraftState
            simple_teams = []
            for team in teams:
                simple_team = {
                    "owner": team.get("owner", "Unknown"),
                    "team_name": team.get("team_name", "Unknown Team"),
                }
                simple_teams.append(simple_team)

            # Create and return DraftState object directly
            draft_state = DraftState(picks=draft_picks, teams=simple_teams)

            # Cache the draft state if caching is enabled
            # Note: We may need to update cache to handle DraftState objects
            if self.cache:
                # For now, cache the raw data for compatibility
                cache_data = {
                    "picks": picks,
                    "teams": teams,
                    "draft_state": {
                        "total_picks": len(picks),
                        "total_teams": len(teams),
                        "completed_rounds": (
                            max(pick["round"] for pick in picks) if picks else 0
                        ),
                    },
                }
                self.cache.update_cache(sheet_id, range_name, cache_data)

            return draft_state

        except Exception as e:
            logger.error(f"Error reading draft data: {str(e)}")
            raise

    def _parse_incremental_picks(
        self, incremental_data: List[List[Any]], start_round: int
    ) -> List[Dict[str, Any]]:
        """
        Parse incremental draft data starting from a specific round.

        Args:
            incremental_data: Raw data from Google Sheets starting from start_round
            start_round: The round number that the data starts from

        Returns:
            List of new pick dictionaries
        """
        if not incremental_data:
            return []

        # We need team structure to parse picks correctly
        # For now, use a simplified approach assuming teams are consistent
        # In a real implementation, we'd cache team structure separately

        new_picks = []

        # Assuming similar structure to main parsing but starting from a different round
        for row_idx, row in enumerate(incremental_data):
            if not row or not row[0] or not str(row[0]).isdigit():
                continue

            round_num = int(row[0])

            # Skip if this round is before our start round
            if round_num < start_round:
                continue

            # Parse picks from this row - simplified version
            # This assumes teams are in columns 1,2 then 3,4 then 5,6 etc.
            col_idx = 1
            team_number = 1

            while col_idx < len(row) - 1:
                player = (
                    row[col_idx].strip() if col_idx < len(row) and row[col_idx] else ""
                )
                position = (
                    row[col_idx + 1].strip()
                    if col_idx + 1 < len(row) and row[col_idx + 1]
                    else ""
                )

                if player and player.lower() not in ["player", ""]:
                    # Calculate pick number - this is an approximation
                    # In a real implementation, we'd use the cached team structure
                    teams_per_round = 10  # Default assumption
                    pick_number = (round_num - 1) * teams_per_round + team_number

                    new_picks.append(
                        {
                            "pick_number": pick_number,
                            "round": round_num,
                            "team": f"Team {team_number}",  # Placeholder
                            "player_name": player,
                            "position": position,
                        }
                    )

                col_idx += 2  # Move to next team (player + position columns)
                team_number += 1

        logger.info(
            f"Parsed {len(new_picks)} picks from incremental data starting at round {start_round}"
        )
        return new_picks
