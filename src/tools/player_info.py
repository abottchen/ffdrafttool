import logging
from typing import Any, Dict, Optional

from src.tools.player_rankings import get_player_rankings

logger = logging.getLogger(__name__)


def _matches_last_name(search_last_name: str, full_player_name: str) -> bool:
    """
    Check if the search last name matches the player's actual last name.

    Implements logic where the search last name should match from the start of
    the actual last name up to the first space (to handle suffixes like Jr., Sr., III).

    Examples:
    - "Penix" matches "Michael Penix Jr." (Penix matches start of "Penix Jr.")
    - "Walker" matches "Kenneth Walker III" (Walker matches start of "Walker III")
    - "Walker" does NOT match "John Walker Smith" (Walker is not the last name)

    Args:
        search_last_name: The last name being searched for (already lowercased)
        full_player_name: The full player name from rankings (already lowercased)

    Returns:
        True if the search matches the player's last name, False otherwise
    """
    # Split the full name into parts
    name_parts = full_player_name.strip().split()

    if len(name_parts) < 2:
        # Single name - just check if search matches
        return search_last_name in full_player_name

    # For multi-part names, we need to identify the last name
    # Start from the end and work backwards to find the last name
    # Skip common suffixes when determining the core last name
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}

    # Find the last name part (excluding suffixes)
    last_name_start_idx = len(name_parts) - 1

    # If the last part is a suffix, the actual last name is the part before it
    while (
        last_name_start_idx >= 1 and name_parts[last_name_start_idx].lower() in suffixes
    ):
        last_name_start_idx -= 1

    # Now check if our search matches the identified last name part
    if last_name_start_idx >= 1:
        actual_last_name = name_parts[last_name_start_idx]

        # Check if search matches the beginning of the actual last name
        # This handles cases like "Penix" matching "Penix Jr."
        if actual_last_name.startswith(search_last_name):
            return True

        # Also check exact match for backwards compatibility
        if search_last_name == actual_last_name:
            return True

        # If we get here, the search doesn't match the actual last name
        return False

    # If we couldn't identify a proper last name structure, fall back to substring search
    return search_last_name in full_player_name


async def get_player_info(
    last_name: str,
    first_name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch ranking information for a specific player or players.

    Args:
        last_name: Player's last name (required)
        first_name: Player's first name (optional)
        team: Team abbreviation (optional)
        position: Position filter (optional)

    Returns:
        Dict containing array of matching players with their full info
    """
    import time

    start_time = time.time()
    logger.info(
        f"Fetching player info for: last_name={last_name}, first_name={first_name}, "
        f"team={team}, position={position}"
    )

    try:
        # Get current player rankings from all sources
        ranking_sources = ["fantasysharks", "espn", "yahoo", "fantasypros"]
        rankings_result = await get_player_rankings(
            sources=ranking_sources,
            position=position,  # Use position filter if provided
            limit=None,  # Get all players
            force_refresh=False,
        )

        if not rankings_result.get("success"):
            return {
                "success": False,
                "error": "Failed to fetch player rankings",
                "details": rankings_result.get("error"),
            }

        all_players = rankings_result["aggregated"]["players"]
        matched_players = []

        # Normalize search parameters for case-insensitive matching
        search_last_name = last_name.lower().strip()
        search_first_name = first_name.lower().strip() if first_name else None
        search_team = team.upper().strip() if team else None

        for player in all_players:
            player_name = player["name"].lower()
            player_team = player.get("team", "").upper()

            # Check last name match using more precise logic
            if not _matches_last_name(search_last_name, player_name):
                continue

            # Check first name match if provided
            if search_first_name and search_first_name not in player_name:
                continue

            # Check team match if provided
            if search_team and player_team != search_team:
                continue

            # Build player info object
            player_info = {
                "full_name": player["name"],
                "position": player["position"],
                "team": player.get("team", ""),
                "bye_week": player.get("bye_week"),
                "ranking_data": {
                    "rank": player.get("rank", player.get("average_rank", 999)),
                    "score": player.get("score", player.get("average_score", 0)),
                    "average_rank": player.get("average_rank", 999),
                    "average_score": player.get("average_score", 0),
                    "rankings_by_source": player.get("rankings", {}),
                },
                "projected_stats": player.get("projected_stats", {}),
                "injury_status": player.get("injury_status"),
                "commentary": player.get("commentary"),
            }

            matched_players.append(player_info)

        # Sort by rank (best players first)
        matched_players.sort(key=lambda p: p["ranking_data"]["average_rank"])

        if not matched_players:
            return {
                "success": True,
                "players": [],
                "message": f"No players found matching: {last_name}"
                + (f" {first_name}" if first_name else "")
                + (f" ({team})" if team else "")
                + (f" at {position}" if position else ""),
            }

        logger.info(
            f"get_player_info completed in {time.time() - start_time:.2f} seconds"
        )
        return {
            "success": True,
            "players": matched_players,
            "count": len(matched_players),
        }

    except Exception as e:
        logger.error(f"Error fetching player info: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to fetch player information: {str(e)}",
        }
