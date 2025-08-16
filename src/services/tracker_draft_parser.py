"""Parser for tracker API draft format."""

import logging
from typing import Dict, List, Optional

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.sheet_parser import ParseError, SheetParser
from src.services.team_mapping import normalize_position_for_rankings
from src.services.tracker_api_service import TrackerAPIService

logger = logging.getLogger(__name__)


class TrackerDraftParser(SheetParser):
    """Parser for tracker API draft format.

    This parser fetches draft data from the tracker API endpoints instead
    of Google Sheets, but converts the data to the same DraftState format
    for compatibility with existing tools.
    """

    def __init__(self, base_url: str = "http://localhost:8175"):
        self.api_service = TrackerAPIService(base_url)

    def detect_format(self, sheet_data: List[List]) -> bool:
        """For tracker format, we don't use sheet_data detection.

        Args:
            sheet_data: Ignored for tracker format

        Returns:
            Always True since this parser is explicitly chosen via config
        """
        # Tracker format is explicitly chosen via configuration,
        # not auto-detected from sheet data
        return True

    async def parse_draft_data(
        self, sheet_data: List[List], rankings_cache: Optional[Dict] = None
    ) -> DraftState:
        """Parse draft data from tracker API instead of sheet_data.

        Args:
            sheet_data: Ignored for tracker format (we use API instead)
            rankings_cache: Optional rankings cache (not used for tracker)

        Returns:
            DraftState object with picks and team information

        Raises:
            ParseError: If API calls fail or data is malformed
        """
        try:
            logger.info("Parsing draft data from tracker API")

            # Fetch all required data from API
            draft_state_raw = await self.api_service.get_draft_state()
            players_raw = await self.api_service.get_all_players()

            # Build player lookup dictionary
            player_lookup = {p["id"]: p for p in players_raw}
            logger.info(f"Built player lookup with {len(player_lookup)} players")

            # Extract teams from draft state
            teams_raw = draft_state_raw.get("teams", [])
            if not teams_raw:
                logger.warning("No teams found in draft state")
                return DraftState(picks=[], teams=[])

            # Get unique owner IDs and fetch owner/team info
            owner_ids = list(set(team["owner_id"] for team in teams_raw))

            # Fetch all owner details (includes both owner_name and team_name)
            owner_details = {}
            for owner_id in owner_ids:
                owner_info = await self.api_service.get_owner_info(owner_id)
                owner_details[owner_id] = {
                    "owner_name": owner_info["owner_name"],
                    "team_name": owner_info["team_name"],
                }

            # Build picks and teams lists
            all_picks = []
            teams_info = []

            for team_data in teams_raw:
                owner_id = team_data["owner_id"]
                owner_detail = owner_details.get(owner_id, {})
                owner_name = owner_detail.get("owner_name", f"Owner {owner_id}")
                team_name = owner_detail.get("team_name", owner_name)

                # Add team info
                teams_info.append({"owner": owner_name, "team": team_name})

                # Process picks for this team
                picks = team_data.get("picks", [])
                for pick_data in picks:
                    player_id = pick_data["player_id"]

                    # Look up player info
                    player_info = player_lookup.get(player_id)
                    if not player_info:
                        logger.warning(
                            f"Player ID {player_id} not found in players list"
                        )
                        continue

                    # Create Player object
                    player = Player(
                        name=f"{player_info['first_name']} {player_info['last_name']}",
                        team=player_info["team"],
                        position=normalize_position_for_rankings(
                            player_info["position"]
                        ),
                        bye_week=0,  # Not available from tracker API
                        ranking=0,  # Not available from tracker API
                        projected_points=0.0,  # Not available from tracker API
                        injury_status=InjuryStatus.HEALTHY,  # Default to healthy
                        notes="",  # No notes from tracker API
                    )

                    # Create DraftPick object
                    draft_pick = DraftPick(player=player, owner=owner_name)

                    all_picks.append(draft_pick)

            logger.info(
                f"Successfully parsed {len(all_picks)} picks for {len(teams_info)} teams"
            )

            return DraftState(picks=all_picks, teams=teams_info)

        except Exception as e:
            logger.error(f"Error parsing tracker draft data: {str(e)}")
            raise ParseError(f"Failed to parse tracker draft data: {str(e)}") from e
