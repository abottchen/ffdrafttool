"""Player Info tool implementation."""

import logging
from typing import Any, Dict, List, Optional

from src.models.player_simple import Player
from src.tools.player_rankings import _rankings_cache, get_player_rankings

logger = logging.getLogger(__name__)


def _search_cached_players(
    last_name: str,
    first_name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None
) -> List[Player]:
    """Search for players in the cached rankings data."""
    matching_players = []

    # Use PlayerRankings search method if available
    if hasattr(_rankings_cache, 'search_players') and callable(_rankings_cache.search_players):
        matching_players = _rankings_cache.search_players(
            last_name=last_name,
            first_name=first_name,
            team=team,
            position=position
        )
    else:
        # Fallback: search all cached positions manually
        for pos in _rankings_cache.get_all_positions():
            pos_players = _rankings_cache.get_position_data(pos)
            if not pos_players:
                continue

            for player in pos_players:
                # Position filter
                if position and player.position.upper() != position.upper():
                    continue

                # Team filter
                if team and player.team.upper() != team.upper():
                    continue

                # Name matching
                player_name_lower = player.name.lower()
                last_name_lower = last_name.lower()

                if last_name_lower not in player_name_lower:
                    continue

                if first_name:
                    first_name_lower = first_name.lower()
                    if first_name_lower not in player_name_lower:
                        continue

                matching_players.append(player)

    return matching_players


async def get_player_info(
    last_name: str,
    first_name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific player by searching cached rankings.

    Args:
        last_name: Player's last name (required)
        first_name: Player's first name (optional)
        team: Team abbreviation (optional)
        position: Position filter (optional)

    Returns:
        Dict containing matching players or error information
    """
    import time

    start_time = time.time()
    logger.info(f"Searching for player: {last_name}, {first_name}, {team}, {position}")

    try:
        # First, search in cached data
        matching_players = _search_cached_players(last_name, first_name, team, position)

        # If no matches and position is provided, try loading that position's rankings
        if not matching_players and position:
            logger.info(f"Player not found in cache, loading {position} rankings")
            rankings_result = await get_player_rankings(position=position)

            if rankings_result.get("success"):
                # Try searching again after loading position data
                matching_players = _search_cached_players(last_name, first_name, team, position)
            else:
                # If loading rankings failed, still return player not found error
                logger.warning(f"Failed to load {position} rankings: {rankings_result.get('error')}")

        # If no matches found after all search attempts
        if not matching_players:
            if not position:
                # No position provided, suggest providing one
                error_msg = f"No players found for '{last_name}'" + \
                           (f" {first_name}" if first_name else "") + \
                           (f" ({team})" if team else "") + \
                           ". Try providing a position to search more data."
            else:
                # Position was provided but still no matches
                error_msg = f"No players found for '{last_name}'" + \
                           (f" {first_name}" if first_name else "") + \
                           (f" ({team})" if team else "") + \
                           (f" at {position}" if position else "")

            return {
                "success": False,
                "error": error_msg,
                "error_type": "player_not_found"
            }

        # Convert Player objects to dictionaries
        player_results = []
        for player in matching_players:
            player_dict = {
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "bye_week": player.bye_week,
                "ranking": player.ranking,
                "projected_points": player.projected_points,
                "injury_status": player.injury_status.value,
                "notes": player.notes
            }
            player_results.append(player_dict)

        # Sort by ranking (lower is better)
        player_results.sort(key=lambda p: p["ranking"])

        logger.info(f"get_player_info completed in {time.time() - start_time:.2f} seconds")
        return {
            "success": True,
            "players": player_results,
            "count": len(player_results),
            "search_criteria": {
                "last_name": last_name,
                "first_name": first_name,
                "team": team,
                "position": position
            }
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error in get_player_info: {error_message}")

        return {
            "success": False,
            "error": f"Failed to get player information: {error_message}",
            "error_type": "unexpected_error",
            "search_criteria": {
                "last_name": last_name,
                "first_name": first_name,
                "team": team,
                "position": position
            }
        }
