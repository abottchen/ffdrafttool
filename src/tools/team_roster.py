"""Team roster tool implementation."""

import logging
from typing import Any, Dict, List

from src.models.player_simple import Player
from src.services.draft_state_cache import get_cached_draft_state

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
        owner_picks: List[Player] = []
        for pick in draft_picks:
            if pick.owner.lower() == owner_name.lower():
                owner_picks.append(pick.player)

        logger.info(
            f"get_team_roster completed in {time.time() - start_time:.2f} seconds. "
            f"Found {len(owner_picks)} picks for {owner_name}"
        )

        return {
            "success": True,
            "owner_name": owner_name,
            "players": owner_picks,
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
