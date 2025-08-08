"""Player Rankings tool implementation."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.models.player_rankings import PlayerRankings
from src.services.scraper_adapter import ScraperAdapter
from src.services.web_scraper import FantasySharksScraper

logger = logging.getLogger(__name__)


# Global cache instance with TTL
_rankings_cache = PlayerRankings()
_cache_timestamp = None
_cache_ttl_hours = 6


async def get_player_rankings(
    position: Optional[str] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get player rankings with caching support.

    Args:
        position: Filter by position (QB, RB, WR, TE, K, DST). If None, returns all positions.
        force_refresh: If True, ignore cache and fetch fresh data from FantasySharks

    Returns:
        Dict containing player rankings data
    """
    import time

    start_time = time.time()
    logger.info(f"Getting player rankings for position: {position or 'all'}")

    try:
        global _cache_timestamp

        # Check cache first (unless force refresh)
        if not force_refresh and _cache_timestamp is not None:
            cache_age = datetime.now() - _cache_timestamp
            if cache_age < timedelta(hours=_cache_ttl_hours):
                # Get cached data
                if position:
                    cached_players = _rankings_cache.get_position_data(position.upper())
                    if cached_players:
                        logger.info(f"get_player_rankings (cached) completed in {time.time() - start_time:.2f} seconds")
                        return {
                            "success": True,
                            "position_filter": position,
                            "total_players": len(cached_players),
                            "last_updated": _cache_timestamp.isoformat(),
                            "data_source": "FantasySharks",
                            "cache_hit": True,
                            "players": [
                                {
                                    "name": p.name,
                                    "team": p.team,
                                    "position": p.position,
                                    "bye_week": p.bye_week,
                                    "ranking": p.ranking,
                                    "projected_points": p.projected_points,
                                    "injury_status": p.injury_status.value,
                                    "notes": p.notes
                                }
                                for p in cached_players
                            ]
                        }
                else:
                    # Get all cached players
                    all_players = []
                    for pos in _rankings_cache.get_all_positions():
                        pos_players = _rankings_cache.get_position_data(pos)
                        if pos_players:
                            all_players.extend(pos_players)

                    if all_players:
                        logger.info(f"get_player_rankings (cached) completed in {time.time() - start_time:.2f} seconds")
                        return {
                            "success": True,
                            "position_filter": position,
                            "total_players": len(all_players),
                            "last_updated": _cache_timestamp.isoformat(),
                            "data_source": "FantasySharks",
                            "cache_hit": True,
                            "players": [
                                {
                                    "name": p.name,
                                    "team": p.team,
                                    "position": p.position,
                                    "bye_week": p.bye_week,
                                    "ranking": p.ranking,
                                    "projected_points": p.projected_points,
                                    "injury_status": p.injury_status.value,
                                    "notes": p.notes
                                }
                                for p in all_players
                            ]
                        }

        # Fetch fresh data from FantasySharks
        logger.info("Fetching fresh rankings from FantasySharks")
        scraper = FantasySharksScraper()

        try:
            if position:
                from src.models.player import Position
                position_enum = Position(position.upper())
                raw_players = await scraper.scrape_rankings(position_enum)
            else:
                # Get all positions
                from src.models.player import Position
                raw_players = []
                for pos_enum in Position:
                    if pos_enum not in [Position.FLEX, Position.BE, Position.IR]:  # Skip non-draftable positions
                        pos_players = await scraper.scrape_rankings(pos_enum)
                        raw_players.extend(pos_players)
        except Exception as e:
            logger.error(f"Failed to fetch data from FantasySharks: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch rankings from FantasySharks: {str(e)}",
                "error_type": "scraper_failed",
                "troubleshooting": {
                    "problem": "Unable to fetch player rankings from FantasySharks",
                    "solution": "Check network connection and FantasySharks website availability",
                    "next_steps": [
                        "1. Verify internet connection",
                        "2. Check if FantasySharks.com is accessible",
                        "3. Try again with force_refresh=True",
                        "4. Check logs for detailed error information"
                    ]
                },
                "position_filter": position
            }

        if not raw_players:
            logger.warning("No players returned from FantasySharks")
            return {
                "success": False,
                "error": "No player data available from FantasySharks",
                "error_type": "no_data",
                "position_filter": position
            }

        # Convert to simplified Player models
        adapter = ScraperAdapter()
        simplified_players = []

        for raw_player in raw_players:
            try:
                simplified_player = adapter.convert_player(raw_player)
                simplified_players.append(simplified_player)
            except Exception as e:
                logger.warning(f"Failed to convert player {raw_player}: {e}")
                continue

        if not simplified_players:
            logger.error("No players could be converted from raw data")
            return {
                "success": False,
                "error": "Failed to convert player data to simplified format",
                "error_type": "conversion_failed",
                "position_filter": position
            }

        # Cache the new data by position
        _rankings_cache.clear_cache()
        positions_cached = set()

        for player in simplified_players:
            pos = player.position.upper()
            if pos not in positions_cached:
                pos_players = [p for p in simplified_players if p.position.upper() == pos]
                _rankings_cache.set_position_data(pos, pos_players)
                positions_cached.add(pos)

        _cache_timestamp = datetime.now()

        # Filter by position if requested
        players_to_return = simplified_players
        if position:
            players_to_return = [p for p in simplified_players if p.position.upper() == position.upper()]

        logger.info(f"get_player_rankings completed in {time.time() - start_time:.2f} seconds")
        return {
            "success": True,
            "position_filter": position,
            "total_players": len(players_to_return),
            "last_updated": _cache_timestamp.isoformat(),
            "data_source": "FantasySharks",
            "cache_hit": False,
            "players": [
                {
                    "name": p.name,
                    "team": p.team,
                    "position": p.position,
                    "bye_week": p.bye_week,
                    "ranking": p.ranking,
                    "projected_points": p.projected_points,
                    "injury_status": p.injury_status.value,
                    "notes": p.notes
                }
                for p in players_to_return
            ]
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error in get_player_rankings: {error_message}")

        return {
            "success": False,
            "error": f"Unexpected error: {error_message}",
            "error_type": "unexpected_error",
            "troubleshooting": {
                "problem": f"An unexpected error occurred: {error_message}",
                "solution": "Check logs for detailed error information",
                "next_steps": [
                    "1. Check the application logs for stack traces",
                    "2. Verify all dependencies are installed",
                    "3. Try force_refresh=True to bypass any caching issues",
                    "4. Contact support if error persists"
                ]
            },
            "position_filter": position
        }


def clear_rankings_cache():
    """Clear the player rankings cache."""
    global _cache_timestamp
    _rankings_cache.clear_cache()
    _cache_timestamp = None
    logger.info("Player rankings cache cleared")
