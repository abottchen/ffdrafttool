"""Available Players tool implementation."""

import logging
from typing import Any, Dict

from src.models.draft_state_simple import DraftState
from src.tools.player_rankings import get_player_rankings

logger = logging.getLogger(__name__)


def _normalize_player_name(name: str) -> str:
    """Normalize player name for comparison."""
    normalized = name.lower()
    # Remove common punctuation and suffixes
    normalized = normalized.replace(".", "").replace("'", "").replace("-", "")
    normalized = normalized.replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")
    return " ".join(normalized.split()).strip()


async def get_available_players(
    draft_state: DraftState,
    position: str,
    limit: int
) -> Dict[str, Any]:
    """
    Get a list of top undrafted players at a position.

    Args:
        draft_state: Current draft state to determine who's available
        position: Position to filter ("QB", "RB", "WR", "TE", "K", "DST")
        limit: Maximum number of players to return

    Returns:
        Dict containing list of available players with ranking data
    """
    import time

    start_time = time.time()
    logger.info(f"Getting available {position} players (limit: {limit})")

    try:
        # Validate inputs
        valid_positions = ["QB", "RB", "WR", "TE", "K", "DST"]
        if position.upper() not in valid_positions:
            return {
                "success": False,
                "error": f"Invalid position: {position}. Valid positions: {valid_positions}",
                "error_type": "invalid_position"
            }

        if limit <= 0:
            return {
                "success": False,
                "error": "Limit must be greater than 0",
                "error_type": "invalid_limit"
            }

        # Get player rankings for the specified position
        rankings_result = await get_player_rankings(position=position.upper())

        if not rankings_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to get player rankings: {rankings_result.get('error')}",
                "error_type": "rankings_failed"
            }

        all_position_players = rankings_result["players"]

        # Create set of drafted player names for fast lookup
        drafted_players = set()
        for pick in draft_state.picks:
            normalized_name = _normalize_player_name(pick.player.name)
            drafted_players.add(normalized_name)

        logger.info(f"Found {len(drafted_players)} drafted players to filter out")

        # Filter out drafted players
        available_players = []
        for player_data in all_position_players:
            normalized_ranking_name = _normalize_player_name(player_data["name"])

            if normalized_ranking_name not in drafted_players:
                available_players.append(player_data)

        # Sort by projected_points (descending - higher is better)
        available_players.sort(key=lambda p: p["projected_points"], reverse=True)

        # Apply limit
        limited_players = available_players[:limit]

        logger.info(f"get_available_players completed in {time.time() - start_time:.2f} seconds")
        return {
            "success": True,
            "position": position.upper(),
            "limit": limit,
            "total_available": len(available_players),
            "returned_count": len(limited_players),
            "players": limited_players,
            "draft_context": {
                "total_picks_made": len(draft_state.picks),
                "total_teams": len(draft_state.teams)
            }
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error in get_available_players: {error_message}")

        return {
            "success": False,
            "error": f"Failed to get available players: {error_message}",
            "error_type": "unexpected_error",
            "troubleshooting": {
                "problem": f"An unexpected error occurred: {error_message}",
                "solution": "Check logs for detailed error information",
                "next_steps": [
                    "1. Verify draft_state contains valid picks data",
                    "2. Ensure position parameter is valid",
                    "3. Check that player rankings tool is working",
                    "4. Verify limit parameter is positive"
                ]
            },
            "inputs": {
                "position": position,
                "limit": limit,
                "draft_picks_count": len(draft_state.picks) if draft_state else 0
            }
        }
