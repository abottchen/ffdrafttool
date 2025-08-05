import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.models.player import InjuryStatus, Position
from src.services.web_scraper import (
    ESPNScraper,
    FantasyProsScraper,
    FantasySharksScraper,
    YahooScraper,
)

logger = logging.getLogger(__name__)

# Global cache for player rankings
_rankings_cache = {
    "data": None,
    "timestamp": None,
    "cache_duration": timedelta(hours=24),  # Rankings valid for entire draft session
}


async def get_player_rankings(
    sources: List[str],
    position: Optional[str] = None,
    limit: Optional[int] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Fetch current player rankings from multiple sources with caching.

    Args:
        sources: List of ranking sources ("espn", "yahoo", "fantasypros", "fantasysharks")
        position: Optional position filter ("QB", "RB", "WR", "TE", "K", "DST")
        limit: Optional limit on number of players to return
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        Dict containing player data with rankings from each source
    """
    import time

    start_time = time.time()
    logger.info(
        f"Starting get_player_rankings - sources: {sources}, position: {position}, limit: {limit}"
    )
    global _rankings_cache

    # Check if we have valid cached data
    if not force_refresh and _rankings_cache["data"] is not None:
        cache_age = datetime.now() - _rankings_cache["timestamp"]
        if cache_age < _rankings_cache["cache_duration"]:
            logger.info(
                f"Using cached rankings (age: {cache_age.total_seconds():.0f}s)"
            )

            # Extract from cache and apply filters
            cached_data = _rankings_cache["data"]

            # If position filter requested, filter the cached aggregated players
            if position:
                try:
                    position_filter = Position(position.upper())
                    filtered_players = [
                        p
                        for p in cached_data["aggregated"]["players"]
                        if p["position"] == position_filter.value
                    ]

                    # Create filtered response
                    result = {
                        "success": True,
                        "aggregated": {
                            "players": (
                                filtered_players[:limit] if limit else filtered_players
                            ),
                            "count": len(filtered_players),
                        },
                        "position": position,
                        "limit": limit,
                        "from_cache": True,
                    }
                    return result
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid position: {position}. Valid positions: QB, RB, WR, TE, K, DST",
                    }

            # Apply limit if requested (no position filter)
            if limit:
                limited_players = cached_data["aggregated"]["players"][:limit]
                result = {
                    "success": True,
                    "aggregated": {
                        "players": limited_players,
                        "count": len(limited_players),
                    },
                    "limit": limit,
                    "from_cache": True,
                }
                return result

            # Return full cached data
            return {**cached_data, "from_cache": True}

    logger.info(f"Fetching fresh rankings from sources: {sources}")

    # Parse position filter
    position_filter = None
    if position:
        try:
            position_filter = Position(position.upper())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid position: {position}. Valid positions: QB, RB, WR, TE, K, DST",
            }

    # Map source names to scrapers
    scrapers = {
        "espn": ESPNScraper(),
        "yahoo": YahooScraper(),
        "fantasypros": FantasyProsScraper(),
        "fantasysharks": FantasySharksScraper(),
    }

    results = {}
    all_players = {}  # player_name -> Player object (for aggregation)

    for source in sources:
        source_lower = source.lower()
        if source_lower not in scrapers:
            logger.warning(
                f"Unknown source: {source}. Available: {list(scrapers.keys())}"
            )
            results[source] = {"success": False, "error": f"Unknown source: {source}"}
            continue

        try:
            scraper = scrapers[source_lower]
            players = await scraper.scrape_rankings(position_filter)

            # Convert to serializable format
            player_data = []
            for player in players:
                player_dict = {
                    "name": player.name,
                    "position": player.position.value,
                    "team": player.team,
                    "bye_week": player.bye_week,
                    "rankings": {},
                    "average_rank": player.average_rank,
                    "average_score": player.average_score,
                    "commentary": player.commentary,  # Include expert analysis if available
                }

                # Add rankings from all sources for this player
                for ranking_source, ranking in player.rankings.items():
                    player_dict["rankings"][ranking_source.value] = {
                        "rank": ranking["rank"],
                        "score": ranking["score"],
                    }

                player_data.append(player_dict)

                # Store for aggregation
                if player.name not in all_players:
                    all_players[player.name] = player
                else:
                    # Merge rankings from multiple sources
                    for ranking_source, ranking in player.rankings.items():
                        all_players[player.name].add_ranking(
                            ranking_source, ranking["rank"], ranking["score"]
                        )

            results[source] = {
                "success": True,
                "players": player_data,
                "count": len(player_data),
            }

            logger.info(
                f"Successfully fetched {len(player_data)} players from {source}"
            )

        except Exception as e:
            logger.error(f"Error fetching from {source}: {str(e)}")
            results[source] = {"success": False, "error": str(e)}

    # Create aggregated rankings
    aggregated_players = []
    for player in all_players.values():
        if position_filter and player.position != position_filter:
            continue

        player_dict = {
            "name": player.name,
            "position": player.position.value,
            "team": player.team,
            "bye_week": player.bye_week,
            "average_rank": player.average_rank,
            "average_score": player.average_score,
            "injury_status": (
                player.injury_status.value
                if player.injury_status != InjuryStatus.HEALTHY
                else None
            ),
        }

        # Add injury warning for long-term injuries
        if (
            hasattr(player, "commentary")
            and player.commentary
            and "injury:" in player.commentary.lower()
        ):
            injury_commentary = player.commentary
            # Check for long-term injury indicators in commentary
            if any(
                indicator in injury_commentary.lower()
                for indicator in [
                    "season",
                    "year",
                    "months",
                    "week 8",
                    "week 9",
                    "week 10",
                    "week 11",
                    "week 12",
                    "week 13",
                    "week 14",
                    "week 15",
                    "week 16",
                    "week 17",
                    "week 18",
                    "playoffs",
                ]
            ):
                player_dict["injury_warning"] = (
                    f"⚠️ LONG-TERM INJURY: {injury_commentary}"
                )
            elif player.injury_status in [InjuryStatus.OUT, InjuryStatus.DOUBTFUL]:
                player_dict["injury_warning"] = f"⚠️ INJURY: {injury_commentary}"

        # Only include primary ranking source to save tokens
        if player.rankings:
            primary_source = next(iter(player.rankings.keys()))
            primary_ranking = player.rankings[primary_source]
            player_dict["rank"] = primary_ranking["rank"]
            player_dict["score"] = primary_ranking["score"]

        aggregated_players.append(player_dict)

    # Sort by average rank (lower is better) or average score (higher is better)
    aggregated_players.sort(key=lambda p: p.get("average_rank") or 999)

    # Apply limit if specified
    if limit and limit > 0:
        aggregated_players = aggregated_players[:limit]
        for source_data in results.values():
            if source_data.get("success") and "players" in source_data:
                source_data["players"] = source_data["players"][:limit]

    # Build the result
    result = {
        "success": True,
        "aggregated": {"players": aggregated_players, "count": len(aggregated_players)},
        "position": position,
        "limit": limit,
    }

    # Cache the full unfiltered data if this was a fresh fetch without filters
    if not position and not limit:
        _rankings_cache["data"] = result
        _rankings_cache["timestamp"] = datetime.now()
        logger.info(f"Cached {len(aggregated_players)} players for future requests")

    logger.info(
        f"get_player_rankings completed in {time.time() - start_time:.2f} seconds"
    )
    return result


def clear_rankings_cache():
    """Clear the player rankings cache."""
    global _rankings_cache
    _rankings_cache["data"] = None
    _rankings_cache["timestamp"] = None
    logger.info("Player rankings cache cleared")
