"""Team roster tool implementation."""

import logging
from typing import Any, Dict, List

from src.models.player_simple import Player
from src.services.draft_state_cache import get_cached_draft_state
from src.tools.player_rankings import get_player_rankings

logger = logging.getLogger(__name__)


async def get_team_roster(owner_name: str) -> Dict[str, Any]:
    """
    Get all drafted players for a specific owner.

    Args:
        owner_name: Name of the team owner to get roster for

    Returns:
        Dict containing owner name and list of Player objects
    """
    import time

    start_time = time.time()
    logger.info(f"Getting team roster for owner: {owner_name}")

    try:
        # Validate input
        if not owner_name or not owner_name.strip():
            return {
                "success": False,
                "error": "Owner name cannot be empty",
                "error_type": "invalid_owner_name",
            }

        owner_name = owner_name.strip()

        # Fetch current draft state (with caching)
        draft_state_result = await get_cached_draft_state()

        # Handle error cases from draft state fetch
        if isinstance(draft_state_result, dict) and not draft_state_result.get(
            "success", True
        ):
            return {
                "success": False,
                "error": f"Failed to fetch draft state: {draft_state_result.get('error')}",
                "error_type": "draft_state_failed",
            }

        # Extract owner's picks from draft state
        if hasattr(draft_state_result, "picks"):
            # It's a DraftState object
            draft_picks = draft_state_result.picks
        else:
            # This shouldn't happen, but handle gracefully
            return {
                "success": False,
                "error": "Unexpected draft state format",
                "error_type": "invalid_draft_state",
            }

        # Find picks by this owner
        basic_picks: List[Player] = []
        for pick in draft_picks:
            if pick.owner.lower() == owner_name.lower():
                basic_picks.append(pick.player)

        # Enrich player data with rankings information (bye weeks, projections, etc.)
        enriched_picks: List[Player] = []
        positions_fetched = set()  # Track which positions we've already fetched

        for player in basic_picks:
            try:
                # Check if we need to fetch rankings for this position
                if player.position not in positions_fetched:
                    logger.info(
                        f"Fetching rankings for position {player.position} to enrich player data"
                    )
                    rankings_result = await get_player_rankings(
                        position=player.position
                    )
                    if not rankings_result.get("success"):
                        logger.warning(
                            f"Failed to fetch rankings for {player.position}: {rankings_result.get('error')}"
                        )
                    positions_fetched.add(player.position)

                # Try to find this player in rankings to get enriched data
                rankings_result = await get_player_rankings(position=player.position)
                if rankings_result.get("success"):
                    # Look for matching player in rankings
                    enriched_player = None
                    for ranked_player_data in rankings_result["players"]:
                        # Match by name and team
                        if (
                            ranked_player_data["name"].lower() == player.name.lower()
                            and ranked_player_data["team"].upper()
                            == player.team.upper()
                        ):
                            # Create enriched Player object from rankings data
                            enriched_player = Player(
                                name=ranked_player_data["name"],
                                team=ranked_player_data["team"],
                                position=ranked_player_data["position"],
                                bye_week=ranked_player_data["bye_week"],
                                ranking=ranked_player_data["ranking"],
                                projected_points=ranked_player_data["projected_points"],
                                injury_status=player.injury_status,  # Keep original injury status
                                notes=ranked_player_data.get("notes", ""),
                            )
                            logger.debug(
                                f"Enriched {player.name} with rankings data (bye week: {ranked_player_data['bye_week']})"
                            )
                            break

                    if enriched_player:
                        enriched_picks.append(enriched_player)
                    else:
                        # Player not found in rankings - this is concerning
                        logger.error(
                            f"PLAYER DATA ISSUE: Drafted player '{player.name}' ({player.team} {player.position}) "
                            f"was not found in {player.position} rankings. This indicates a potential data quality "
                            f"issue - either the player name/team doesn't match between draft sheet and rankings, "
                            f"or the rankings data is incomplete. Using basic draft sheet data as fallback."
                        )
                        enriched_picks.append(player)
                else:
                    # Rankings fetch failed, use basic data
                    logger.warning(
                        f"Could not fetch rankings for {player.position}, using basic data for {player.name}"
                    )
                    enriched_picks.append(player)

            except Exception as e:
                logger.error(
                    f"Error enriching data for {player.name}: {e}. Using basic data."
                )
                enriched_picks.append(player)

        logger.info(
            f"get_team_roster completed in {time.time() - start_time:.2f} seconds. "
            f"Found {len(enriched_picks)} picks for {owner_name} (enriched with rankings data)"
        )

        return {
            "success": True,
            "owner_name": owner_name,
            "players": enriched_picks,
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error in get_team_roster: {error_message}")

        return {
            "success": False,
            "error": f"Failed to get team roster: {error_message}",
            "error_type": "unexpected_error",
            "troubleshooting": {
                "problem": f"An unexpected error occurred: {error_message}",
                "solution": "Check logs for detailed error information",
                "next_steps": [
                    "1. Verify Google Sheets connection is working",
                    "2. Ensure owner name matches exactly with draft data",
                    "3. Check that draft data contains valid picks",
                ],
            },
            "inputs": {
                "owner_name": owner_name,
            },
        }
