import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.models.player import InjuryStatus, Position
from src.services.sheets_service import (
    GoogleSheetsProvider,
    SheetsService,
)
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

    return result


def clear_rankings_cache():
    """Clear the player rankings cache."""
    global _rankings_cache
    _rankings_cache["data"] = None
    _rankings_cache["timestamp"] = None
    logger.info("Player rankings cache cleared")


async def read_draft_progress(
    sheet_id: str, sheet_range: str = "Draft!A1:V24", force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Read draft progress from Google Sheets with caching support.

    Args:
        sheet_id: Google Sheets ID
        sheet_range: Range to read (e.g., "Draft!A1:V24")
        force_refresh: If True, ignore cache and fetch fresh data from Google Sheets

    Returns:
        Dict containing draft state, picks, and available players
    """
    logger.info(f"Reading draft progress from sheet {sheet_id}, range {sheet_range}")

    try:
        # Create Google Sheets provider - fail fast if not available
        try:
            provider = GoogleSheetsProvider()
        except ImportError as e:
            logger.error(f"Google Sheets API dependencies not installed: {e}")
            return {
                "success": False,
                "error": "Google Sheets API not available",
                "error_type": "missing_dependencies",
                "troubleshooting": {
                    "problem": "Google Sheets API dependencies are not installed",
                    "solution": "Install required packages with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
                    "next_steps": [
                        "1. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
                        "2. Set up Google Sheets API credentials using setup_google_sheets.py",
                        "3. Retry reading draft progress",
                    ],
                },
                "sheet_id": sheet_id,
                "sheet_range": sheet_range,
            }
        except FileNotFoundError as e:
            logger.error(f"Google Sheets credentials not found: {e}")
            return {
                "success": False,
                "error": "Google Sheets credentials not configured",
                "error_type": "missing_credentials",
                "troubleshooting": {
                    "problem": "Google Sheets API credentials file (credentials.json) not found",
                    "solution": "Set up Google Sheets API authentication",
                    "next_steps": [
                        "1. Go to https://console.developers.google.com/",
                        "2. Create a project and enable Google Sheets API",
                        "3. Create OAuth 2.0 credentials for desktop application",
                        "4. Download credentials.json to the project directory",
                        "5. Run setup_google_sheets.py to test authentication",
                        "6. Retry reading draft progress",
                    ],
                },
                "sheet_id": sheet_id,
                "sheet_range": sheet_range,
            }

        sheets_service = SheetsService(provider)

        # Read and parse draft data with caching support
        draft_data = await sheets_service.read_draft_data(
            sheet_id, sheet_range, force_refresh
        )

        # Create a more compact summary to avoid token limits
        # Remove draft_type (not useful) and team name (player name is sufficient)
        picks_summary = []
        for pick in draft_data.get("picks", []):
            picks_summary.append(
                {
                    "pick": pick.get("pick_number"),
                    "round": pick.get("round"),
                    "player": pick.get("player_name"),
                    "position": pick.get("position"),
                    "column_team": pick.get(
                        "column_team"
                    ),  # Include actual column team for proper roster tracking
                }
            )

        teams_summary = []
        for team in draft_data.get("teams", []):
            teams_summary.append(
                {
                    "team_name": team.get("team_name"),
                    "owner": team.get("owner"),
                    "team_number": team.get("team_number"),
                }
            )

        return {
            "success": True,
            "sheet_id": sheet_id,
            "current_pick": draft_data.get("current_pick"),
            "current_round": (
                (
                    (draft_data.get("current_pick", 1) - 1)
                    // len(draft_data.get("teams", []))
                )
                + 1
                if draft_data.get("teams")
                else 1
            ),
            "total_picks": len(picks_summary),
            "teams": teams_summary,
            "picks": picks_summary,
            "draft_state": {
                "picks": picks_summary,
                "teams": teams_summary,
                "current_pick": draft_data.get("current_pick"),
                "current_team": draft_data.get("current_team"),
            },
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error reading draft progress: {error_message}")

        # Provide specific troubleshooting based on error type
        troubleshooting = {
            "problem": f"Failed to read draft data from Google Sheets: {error_message}",
            "next_steps": [
                "1. Verify the Google Sheet ID is correct",
                "2. Ensure the sheet is accessible (shared with your Google account or public)",
                "3. Check that the sheet range exists and contains data",
                "4. Verify your Google Sheets API authentication is working",
            ],
        }

        # Add specific guidance for common errors
        if "403" in error_message or "permission" in error_message.lower():
            troubleshooting["solution"] = "Sheet access denied - check permissions"
            troubleshooting["next_steps"] = [
                "1. Ensure the Google Sheet is shared with your Google account",
                "2. Or make the sheet publicly viewable with link sharing",
                "3. Verify the sheet ID in the URL is correct",
                "4. Check that your Google account has access to the sheet",
            ]
        elif "404" in error_message or "not found" in error_message.lower():
            troubleshooting["solution"] = "Sheet not found - check sheet ID and range"
            troubleshooting["next_steps"] = [
                "1. Verify the Google Sheet ID from the URL",
                "2. Check that the sheet tab name is correct (e.g., 'Draft')",
                "3. Ensure the range exists in the sheet",
                "4. Confirm the sheet hasn't been deleted or moved",
            ]
        elif (
            "authentication" in error_message.lower()
            or "credentials" in error_message.lower()
        ):
            troubleshooting["solution"] = "Authentication failed - refresh credentials"
            troubleshooting["next_steps"] = [
                "1. Delete token.json to force re-authentication",
                "2. Run setup_google_sheets.py to re-authenticate",
                "3. Ensure credentials.json is valid and for the correct project",
                "4. Check that Google Sheets API is enabled in your project",
            ]
        else:
            troubleshooting["solution"] = (
                "Check network connection and sheet accessibility"
            )

        return {
            "success": False,
            "error": error_message,
            "error_type": "sheet_access_failed",
            "troubleshooting": troubleshooting,
            "sheet_id": sheet_id,
            "sheet_range": sheet_range,
        }


def _extract_player_name_and_team(player_field: str) -> tuple[str, str]:
    """
    Extract player name and team from draft data format.

    Examples:
    - "Jahmyr Gibbs DET" -> ("Jahmyr Gibbs", "DET")
    - "Saquon Barkley NYG" -> ("Saquon Barkley", "NYG")
    - "Player Name" -> ("Player Name", "")

    Args:
        player_field: The player field from draft data

    Returns:
        tuple of (player_name, team_abbreviation)
    """
    if not player_field:
        return "", ""

    # Known NFL team abbreviations
    NFL_TEAMS = {
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAC",
        "JAX",
        "KC",
        "LAC",
        "LAR",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    }

    # Split by spaces and check if last part is a known team abbreviation
    parts = player_field.strip().split()
    if not parts:
        return "", ""

    # Check if the last part is a known NFL team abbreviation
    if len(parts) > 1 and parts[-1].upper() in NFL_TEAMS:
        team = parts[-1].upper()
        name = " ".join(parts[:-1])
        return name, team
    else:
        # No team found, return full string as name
        return player_field, ""


async def analyze_available_players(
    draft_state: Dict[str, Any],
    position_filter: Optional[str] = None,
    limit: int = 20,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Analyze available players with value metrics and scarcity.

    Args:
        draft_state: Current draft state with picks and team info
        position_filter: Optional position filter ("QB", "RB", "WR", "TE", "K", "DST")
        limit: Number of players to return (default: 20)
        force_refresh: If True, bypass cache and fetch fresh rankings data

    Returns:
        Dict containing analyzed players with value metrics, scarcity info, and recommendations
    """
    logger.info(
        f"Analyzing available players with position filter: {position_filter}, limit: {limit}, force_refresh: {force_refresh}"
    )

    try:
        # Parse position filter
        if position_filter:
            try:
                Position(position_filter.upper())
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid position filter: {position_filter}. Valid positions: QB, RB, WR, TE, K, DST",
                }

        # Extract drafted players and analyze current roster composition
        picks = draft_state.get("picks", [])
        drafted_players = set()
        current_roster = {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": []}
        bye_week_conflicts = {}  # bye_week -> {position: [players]}

        # Determine which team we're analyzing for - ALWAYS look for FF_OWNER's team by owner name
        # Note: draft_state.current_team represents who's "on the clock", not who we're analyzing for
        from config import USER_OWNER_NAME

        teams = draft_state.get("teams", [])
        analysis_team = None  # The team we're providing analysis for (FF_OWNER's team)

        # Always try to find user's team by owner name (ignore current_team as it's who's on the clock)
        if teams:
            # Try to match by owner name (exact match first, then partial match)
            for team in teams:
                owner_name = team.get("owner", "").strip()
                if owner_name.lower() == USER_OWNER_NAME.lower():
                    analysis_team = team
                    logger.info(
                        f"Found FF_OWNER's team by exact owner match: {team.get('team_name')} (owner: {owner_name})"
                    )
                    break

            # If exact match fails, try partial match (in case of formatting differences)
            if not analysis_team:
                for team in teams:
                    owner_name = team.get("owner", "").strip()
                    if (
                        USER_OWNER_NAME.lower() in owner_name.lower()
                        or owner_name.lower() in USER_OWNER_NAME.lower()
                    ):
                        analysis_team = team
                        logger.info(
                            f"Found FF_OWNER's team by partial owner match: {team.get('team_name')} (owner: {owner_name})"
                        )
                        break

            # If no owner match found, provide general analysis instead of fallback
            if not analysis_team:
                logger.info(
                    f"Could not find team for owner '{USER_OWNER_NAME}', will provide general best available player analysis"
                )

        if analysis_team:
            logger.info(
                f"Analyzing for FF_OWNER's team: {analysis_team.get('team_name')} (owner: {analysis_team.get('owner')})"
            )
        else:
            logger.info(
                f"Providing general analysis (no specific team identified for {USER_OWNER_NAME})"
            )

        for pick in picks:
            player_field = pick.get("player", "").strip()
            if player_field:
                # Extract player name and team from formats like "Jahmyr Gibbs DET" or "Jahmyr Gibbs"
                player_name, player_team = _extract_player_name_and_team(player_field)

                # Create a normalized key for comparison: "name|team"
                normalized_name = player_name.lower()
                # Remove team abbreviations in parentheses like "(BUF)" FIRST
                if "(" in normalized_name:
                    normalized_name = normalized_name.split("(")[0]
                normalized_name = (
                    normalized_name.replace(".", "").replace("'", "").replace("-", "")
                )
                normalized_name = (
                    normalized_name.replace("jr", "")
                    .replace("sr", "")
                    .replace("iii", "")
                    .replace("ii", "")
                )
                normalized_name = " ".join(normalized_name.split()).strip()

                # Create composite key to handle players with same name on different teams
                composite_key = (
                    f"{normalized_name}|{player_team.upper()}"
                    if player_team
                    else normalized_name
                )
                drafted_players.add(composite_key)

                logger.info(
                    f"DRAFT_DEBUG: Raw='{player_field}' -> Name='{player_name}' Team='{player_team}' -> Key='{composite_key}'"
                )

                # Track FF_OWNER's team roster for bye week analysis
                # Use column_team (actual column position) instead of team (snake draft logic)
                pick_team = pick.get("column_team") or pick.get("team")
                if analysis_team and pick_team == analysis_team.get("team_name"):
                    position = pick.get("position", "").upper()
                    bye_week = pick.get("bye_week", 0)

                    if position in current_roster:
                        current_roster[position].append(
                            {
                                "name": player_name,
                                "position": position,
                                "bye_week": bye_week,
                            }
                        )

                        # Track bye week conflicts
                        if bye_week not in bye_week_conflicts:
                            bye_week_conflicts[bye_week] = {}
                        if position not in bye_week_conflicts[bye_week]:
                            bye_week_conflicts[bye_week][position] = []
                        bye_week_conflicts[bye_week][position].append(player_name)

        logger.info(f"Found {len(drafted_players)} drafted players")
        logger.info(
            f"First 10 drafted players (normalized): {list(list(drafted_players)[:10])}"
        )
        if analysis_team:
            logger.info(
                f"Analyzing bye weeks for team: {analysis_team.get('team_name')}"
            )

        # Get current player rankings from all available sources
        ranking_sources = ["fantasysharks", "espn", "yahoo", "fantasypros"]
        rankings_result = await get_player_rankings(
            sources=ranking_sources,
            position=position_filter,
            limit=None,  # Get all players for analysis
            force_refresh=force_refresh,
        )

        if not rankings_result.get("success"):
            return {
                "success": False,
                "error": "Failed to fetch player rankings for analysis",
                "ranking_error": rankings_result.get("error"),
            }

        all_players = rankings_result["aggregated"]["players"]
        logger.info(f"Retrieved {len(all_players)} players from rankings")

        # Filter out drafted players
        available_players = []
        for player in all_players:
            # Clean the display name to remove team abbreviations
            clean_name = player["name"]
            # Remove team abbreviations in parentheses like "(BUF)"
            if "(" in clean_name:
                clean_name = clean_name.split("(")[0].strip()

            # Apply normalization for filtering comparison
            rankings_name = clean_name.lower()
            rankings_name = (
                rankings_name.replace(".", "").replace("'", "").replace("-", "")
            )
            rankings_name = (
                rankings_name.replace("jr", "")
                .replace("sr", "")
                .replace("iii", "")
                .replace("ii", "")
            )
            rankings_name = " ".join(rankings_name.split()).strip()

            # Create composite key for available player: "name|team"
            player_team = player.get("team", "").upper()
            available_composite_key = (
                f"{rankings_name}|{player_team}" if player_team else rankings_name
            )

            # Check if player is drafted using flexible team matching
            is_drafted = False

            # First check exact composite key match (for backwards compatibility)
            if available_composite_key in drafted_players:
                is_drafted = True
            # Then check name-only match (for cases where team info might be missing)
            elif rankings_name in drafted_players:
                is_drafted = True
            # Finally, check for team abbreviation variations (e.g., SF vs SFO)
            elif player_team:
                for drafted_key in drafted_players:
                    if "|" in drafted_key:
                        drafted_name, drafted_team = drafted_key.split("|", 1)
                        if drafted_name == rankings_name:
                            # Check if teams are compatible using substring matching
                            # This handles cases like SF/SFO, GB/GBP, NO/NOS, NE/NEP, TB/TBB
                            if (
                                drafted_team in player_team
                                or player_team in drafted_team
                                or (
                                    len(drafted_team) >= 2
                                    and len(player_team) >= 2
                                    and drafted_team[:2] == player_team[:2]
                                )
                            ):
                                is_drafted = True
                                break

            # Special debug logging for Jahmyr Gibbs
            if "jahmyr" in rankings_name.lower() and "gibbs" in rankings_name.lower():
                logger.info(
                    f"GIBBS_DEBUG: Original='{player['name']}' Clean='{clean_name}' Normalized='{rankings_name}' Team='{player_team}' CompositeKey='{available_composite_key}'"
                )
                logger.info(
                    f"GIBBS_DEBUG: Checking against drafted_players: {sorted(drafted_players)}"
                )
                logger.info(
                    f"GIBBS_DEBUG: is_drafted={is_drafted} (composite_check={available_composite_key in drafted_players}, name_check={rankings_name in drafted_players})"
                )

            if not is_drafted:
                # Update the player object with the cleaned name
                player_copy = player.copy()
                player_copy["name"] = clean_name
                available_players.append(player_copy)
            else:
                logger.info(
                    f"Filtered out drafted player: {player['name']} -> '{clean_name}' (key: '{available_composite_key}')"
                )

        logger.info(
            f"Found {len(available_players)} available players after filtering drafted"
        )

        # Calculate positional scarcity and value metrics
        analyzed_players = []
        position_counts = {}

        # Count available players by position
        for player in available_players:
            pos = player["position"]
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Analyze each available player
        for player in available_players:
            pos = player["position"]
            avg_rank = player.get("average_rank", 999)
            avg_score = player.get("average_score", 0)

            # Calculate positional scarcity based on realistic fantasy value curves
            position_depth = position_counts.get(pos, 0)

            # Calculate positional rank among available players for this position
            same_pos_players = [p for p in available_players if p["position"] == pos]
            same_pos_players.sort(key=lambda p: p.get("average_rank", 999))
            pos_rank = next(
                (
                    i + 1
                    for i, p in enumerate(same_pos_players)
                    if p["name"] == player["name"]
                ),
                999,
            )

            # Position-specific scarcity based on real fantasy value curves
            if pos == "QB":
                # Only top 10 QBs worth drafting, massive drop-off after top 5
                if pos_rank <= 5:
                    scarcity_multiplier = 1.8  # Elite QB tier
                elif pos_rank <= 10:
                    scarcity_multiplier = 1.4  # QB1 tier
                elif pos_rank <= 20 and avg_score > 60:  # High upside rookies/breakouts
                    scarcity_multiplier = 1.1  # Upside plays
                else:
                    scarcity_multiplier = 0.8  # Likely undraftable

            elif pos == "RB":
                # Top 5 highly desirable, steep drop after ~30
                if pos_rank <= 5:
                    scarcity_multiplier = 1.6  # Elite RB tier
                elif pos_rank <= 15:
                    scarcity_multiplier = 1.3  # RB1/2 tier
                elif pos_rank <= 30:
                    scarcity_multiplier = 1.1  # Solid RB3/flex
                else:
                    scarcity_multiplier = 0.9  # Pedestrian/handcuff tier

            elif pos == "WR":
                # Deeper position, more even value distribution
                if pos_rank <= 10:
                    scarcity_multiplier = 1.4  # Elite WR tier
                elif pos_rank <= 25:
                    scarcity_multiplier = 1.2  # WR1/2 tier
                elif pos_rank <= 50:
                    scarcity_multiplier = 1.0  # Solid WR3/flex
                else:
                    scarcity_multiplier = 0.95  # Depth/bye week filler

            elif pos == "TE":
                # Very top-heavy position, huge drop after elite tier
                if pos_rank <= 3:
                    scarcity_multiplier = 2.0  # Elite TE (Kelce, Andrews tier)
                elif pos_rank <= 8:
                    scarcity_multiplier = 1.3  # TE1 tier
                elif pos_rank <= 15:
                    scarcity_multiplier = 1.0  # Streaming tier
                else:
                    scarcity_multiplier = 0.8  # Waiver wire fodder

            elif pos in ["K", "DST"]:
                # Don't draft until late rounds regardless of scarcity
                # Apply penalty for drafting too early
                if avg_rank < 150:  # Being drafted too early
                    scarcity_multiplier = 0.3  # Heavy penalty
                elif avg_rank < 200:  # Late round targets
                    scarcity_multiplier = 0.8  # Slight penalty
                else:
                    scarcity_multiplier = 1.0  # Appropriate timing
            else:
                scarcity_multiplier = 1.0

            # Bye week conflict analysis
            player_bye_week = player.get("bye_week", 0)
            bye_week_penalty = 1.0
            bye_week_conflicts_found = []

            if analysis_team and player_bye_week > 0:
                # Check for bye week conflicts with current roster
                conflicts_this_week = bye_week_conflicts.get(player_bye_week, {})

                # Define minimum roster requirements per position for bye weeks
                min_requirements = {
                    "QB": 1,  # Need 1 starting QB
                    "RB": 2,  # Need 2 starting RBs
                    "WR": 2,  # Need 2 starting WRs (could flex a 3rd)
                    "TE": 1,  # Need 1 starting TE
                    "K": 1,  # Need 1 starting K
                    "DST": 1,  # Need 1 starting DST
                }

                # Check if adding this player would create problematic conflicts
                position_conflicts = conflicts_this_week.get(pos, [])
                current_at_position = len(current_roster.get(pos, []))

                # Calculate conflict severity
                if pos in min_requirements:
                    min_needed = min_requirements[pos]
                    players_on_bye = len(position_conflicts)

                    # If we already have players on bye this week at this position
                    if players_on_bye > 0:
                        total_after_draft = current_at_position + 1
                        players_on_bye_after = players_on_bye + 1

                        # For skill positions (RB/WR), consider FLEX eligibility
                        if pos in ["RB", "WR"]:
                            # Check cross-position conflicts for FLEX consideration
                            rb_conflicts = len(conflicts_this_week.get("RB", []))
                            wr_conflicts = len(conflicts_this_week.get("WR", []))
                            total_skill_conflicts = rb_conflicts + wr_conflicts
                            if pos == "RB":
                                total_skill_conflicts += 1  # Adding this RB
                            else:  # WR
                                total_skill_conflicts += 1  # Adding this WR

                            total_skill_players = (
                                len(current_roster.get("RB", []))
                                + len(current_roster.get("WR", []))
                                + 1
                            )

                            # Need at least 3 skill players not on bye (2 RB + 2 WR + 1 FLEX)
                            if total_skill_conflicts >= total_skill_players - 2:
                                bye_week_penalty = 0.7  # Moderate penalty
                                bye_week_conflicts_found.append(
                                    f"FLEX conflict on bye week {player_bye_week}"
                                )
                            elif total_skill_conflicts >= total_skill_players - 3:
                                bye_week_penalty = 0.85  # Light penalty
                                bye_week_conflicts_found.append(
                                    f"Potential FLEX issue on bye week {player_bye_week}"
                                )
                        else:
                            # For non-skill positions, direct conflict check
                            if players_on_bye_after >= total_after_draft:
                                bye_week_penalty = (
                                    0.5  # Heavy penalty - complete positional shutdown
                                )
                                bye_week_conflicts_found.append(
                                    f"Complete {pos} bye week conflict on week {player_bye_week}"
                                )
                            elif players_on_bye_after >= min_needed:
                                bye_week_penalty = (
                                    0.75  # Moderate penalty - starter conflict
                                )
                                bye_week_conflicts_found.append(
                                    f"{pos} starter conflict on bye week {player_bye_week}"
                                )

                # Bonus for filling bye week gaps
                if (
                    player_bye_week not in bye_week_conflicts
                    or pos not in bye_week_conflicts.get(player_bye_week, {})
                ):
                    # This player helps with bye week diversity
                    if (
                        current_at_position < min_requirements.get(pos, 1) * 2
                    ):  # Still building depth
                        bye_week_penalty = 1.05  # Small bonus for bye week diversity

            # Value over replacement calculation
            # Lower average rank is better, so invert for value calculation
            rank_value = max(0, 200 - avg_rank) if avg_rank < 200 else 0

            # Combine ranking value with scarcity and bye week considerations
            overall_value = (rank_value * scarcity_multiplier * bye_week_penalty) + (
                avg_score * 0.1
            )

            # Tier analysis based on average rank
            if avg_rank <= 12:
                tier = "Elite"
                tier_rank = 1
            elif avg_rank <= 36:
                tier = "Tier 1"
                tier_rank = 2
            elif avg_rank <= 60:
                tier = "Tier 2"
                tier_rank = 3
            elif avg_rank <= 100:
                tier = "Tier 3"
                tier_rank = 4
            elif avg_rank <= 150:
                tier = "Tier 4"
                tier_rank = 5
            else:
                tier = "Deep"
                tier_rank = 6

            analyzed_player = {
                "name": player["name"],
                "position": pos,
                "team": player["team"],
                "bye_week": player["bye_week"],
                "rank": player.get("rank", avg_rank),
                "score": player.get("score", avg_score),
                "average_rank": avg_rank,
                "average_score": avg_score,
                "commentary": player.get("commentary"),
                # Value analysis
                "value_metrics": {
                    "overall_value": round(overall_value, 2),
                    "rank_value": round(rank_value, 2),
                    "scarcity_multiplier": round(scarcity_multiplier, 2),
                    "tier": tier,
                    "tier_rank": tier_rank,
                    "positional_rank": pos_rank,
                    "position_depth": position_depth,
                },
                # Scarcity analysis
                "scarcity_analysis": {
                    "position_scarcity": (
                        "High"
                        if scarcity_multiplier > 1.3
                        else "Medium" if scarcity_multiplier > 1.1 else "Low"
                    ),
                    "available_at_position": position_depth,
                    "position_rank": pos_rank,
                    "is_positional_run": pos_rank <= 5
                    and position_depth < 20,  # Top 5 at shallow position
                },
                # Bye week analysis
                "bye_week_analysis": {
                    "bye_week": player_bye_week,
                    "bye_week_penalty": round(bye_week_penalty, 3),
                    "conflict_severity": (
                        "High"
                        if bye_week_penalty <= 0.6
                        else (
                            "Medium"
                            if bye_week_penalty <= 0.8
                            else "Low" if bye_week_penalty < 1.0 else "None"
                        )
                    ),
                    "conflicts_found": bye_week_conflicts_found,
                    "helps_bye_diversity": bye_week_penalty > 1.0,
                },
            }

            analyzed_players.append(analyzed_player)

        # Sort by overall value (descending)
        analyzed_players.sort(
            key=lambda p: p["value_metrics"]["overall_value"], reverse=True
        )

        # Apply limit
        if limit > 0:
            analyzed_players = analyzed_players[:limit]

        # Generate analysis summary - calculate current round from picks and teams
        # But respect existing current_round in draft_state if provided (for tests)
        existing_round = draft_state.get("draft_state", {}).get("current_round")
        if existing_round:
            current_round = existing_round
            logger.info(
                f"Using existing current_round from draft_state: {current_round}"
            )
        else:
            total_picks = len(draft_state.get("picks", []))
            teams = draft_state.get("teams", [])
            total_teams = len(teams) if teams else 10
            current_pick = total_picks + 1
            current_round = ((current_pick - 1) // total_teams) + 1
            logger.info(
                f"Calculated current round: pick {current_pick}, round {current_round}, {total_teams} teams"
            )

        # Determine round strategy
        draft_rules = draft_state.get("draft_state", {}).get("draft_rules", {})
        auction_rounds = draft_rules.get("auction_rounds", [1, 2, 3])
        keeper_round = draft_rules.get("keeper_round", 4)

        if current_round in auction_rounds:
            round_type = "auction"
            strategy_note = "Focus on elite talent and positional scarcity. Target players you specifically want."
        elif current_round == keeper_round:
            round_type = "keeper"
            strategy_note = (
                "Limited participation. Good opportunity for value if you're drafting."
            )
        else:
            round_type = "snake"
            strategy_note = (
                "Traditional snake draft. Consider positional needs and upcoming picks."
            )

        # Position breakdown
        position_breakdown = {}
        for player in analyzed_players:
            pos = player["position"]
            if pos not in position_breakdown:
                position_breakdown[pos] = {
                    "count": 0,
                    "best_available": None,
                    "scarcity_level": "Low",
                }

            position_breakdown[pos]["count"] += 1
            if position_breakdown[pos]["best_available"] is None:
                position_breakdown[pos]["best_available"] = {
                    "name": player["name"],
                    "rank": player["average_rank"],
                    "value": player["value_metrics"]["overall_value"],
                }

            # Update scarcity level based on best player at position
            if player == analyzed_players[0]:  # First player in value order
                scarcity = player["scarcity_analysis"]["position_scarcity"]
                position_breakdown[pos]["scarcity_level"] = scarcity

        # Analyze bye week landscape for recommendations
        bye_week_summary = {}
        problematic_bye_weeks = []

        if analysis_team:
            # Identify problematic bye weeks
            for bye_week, conflicts in bye_week_conflicts.items():
                total_conflicts = sum(len(players) for players in conflicts.values())
                if total_conflicts >= 2:  # 2+ players on same bye week
                    problematic_bye_weeks.append(bye_week)
                    bye_week_summary[bye_week] = {
                        "total_players": total_conflicts,
                        "positions_affected": list(conflicts.keys()),
                        "severity": "High" if total_conflicts >= 3 else "Medium",
                    }

        return {
            "success": True,
            "analysis": {
                "total_available": len(available_players),
                "analyzed_count": len(analyzed_players),
                "current_round": current_round,
                "round_type": round_type,
                "strategy_note": strategy_note,
                "team_analyzed": (
                    analysis_team.get("team_name")
                    if analysis_team
                    else "General (no specific team)"
                ),
            },
            "players": analyzed_players,
            "position_breakdown": position_breakdown,
            "bye_week_analysis": {
                "current_conflicts": bye_week_summary,
                "problematic_weeks": problematic_bye_weeks,
                "roster_summary": {
                    pos: len(players)
                    for pos, players in current_roster.items()
                    if players
                },
            },
            "filters": {"position_filter": position_filter, "limit": limit},
            "recommendations": {
                "high_value_targets": [
                    p
                    for p in analyzed_players[:5]
                    if p["value_metrics"]["overall_value"] > 50
                ],
                "scarcity_picks": [
                    p
                    for p in analyzed_players
                    if p["scarcity_analysis"]["position_scarcity"] == "High"
                ][:3],
                "tier_breaks": [
                    p for p in analyzed_players if p["value_metrics"]["tier_rank"] <= 2
                ][:5],
                "bye_week_safe": [
                    p
                    for p in analyzed_players
                    if p["bye_week_analysis"]["conflict_severity"] == "None"
                ][:5],
                "bye_week_helpers": [
                    p
                    for p in analyzed_players
                    if p["bye_week_analysis"]["helps_bye_diversity"]
                ][:3],
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing available players: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "analysis_failed",
            "troubleshooting": {
                "problem": f"Failed to analyze available players: {str(e)}",
                "next_steps": [
                    "1. Verify draft_state contains valid picks data",
                    "2. Check that player rankings are available",
                    "3. Ensure network connection for fetching rankings",
                    "4. Verify position filter is valid if specified",
                ],
            },
        }


async def suggest_draft_pick(
    draft_state: Dict[str, Any],
    team_name: str,
    strategy: str = "balanced",
    consider_bye_weeks: bool = True,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Suggest the best draft pick based on team needs, strategy, and roster construction.

    Args:
        draft_state: Current draft state including roster and available players
        team_name: Name of the team to provide suggestions for
        strategy: Draft strategy ("balanced", "best_available", "upside", "safe")
        consider_bye_weeks: Whether to consider bye week conflicts (default: True)

    Returns:
        Dict containing recommended pick, alternatives, reasoning, and strategic analysis
    """
    logger.info(
        f"Generating draft pick suggestion with strategy: {strategy}, consider_bye_weeks: {consider_bye_weeks}"
    )

    try:
        # Validate strategy
        valid_strategies = ["balanced", "best_available", "upside", "safe"]
        if strategy not in valid_strategies:
            return {
                "success": False,
                "error": f"Invalid strategy: {strategy}. Valid strategies: {', '.join(valid_strategies)}",
            }

        # Get comprehensive player analysis
        available_analysis = await analyze_available_players(
            draft_state, limit=50, force_refresh=force_refresh
        )

        if not available_analysis.get("success"):
            return {
                "success": False,
                "error": "Failed to analyze available players for draft suggestion",
                "analysis_error": available_analysis.get("error"),
            }

        available_players = available_analysis["players"]
        if not available_players:
            return {
                "success": False,
                "error": "No available players found for draft suggestion",
            }

        # Find the specified team
        teams = draft_state.get("teams", [])
        analysis_team = None

        for team in teams:
            if team.get("team_name") == team_name:
                analysis_team = team
                logger.info(f"Found team for draft suggestion: {team_name}")
                break

        if not analysis_team:
            return {
                "success": False,
                "error": f"Team '{team_name}' not found in draft data. Available teams: {[t.get('team_name') for t in teams]}",
            }

        roster_analysis = _analyze_roster_needs(draft_state, analysis_team)

        # Calculate current round from picks and teams (same logic as analyze_available_players)
        # But respect existing current_round in draft_state if provided (for tests)
        existing_round = draft_state.get("draft_state", {}).get("current_round")
        if existing_round:
            current_round = existing_round
        else:
            total_picks = len(draft_state.get("picks", []))
            teams = draft_state.get("teams", [])
            total_teams = len(teams) if teams else 10
            current_pick = total_picks + 1
            current_round = ((current_pick - 1) // total_teams) + 1

        # Apply strategy-specific scoring
        strategy_weighted_players = []

        for player in available_players:
            base_value = player["value_metrics"]["overall_value"]
            position = player["position"]

            # Strategy-specific multipliers
            strategy_multiplier = _calculate_strategy_multiplier(
                player, roster_analysis, strategy, current_round
            )

            # Bye week consideration
            bye_week_factor = 1.0
            if consider_bye_weeks:
                bye_week_factor = player["bye_week_analysis"]["bye_week_penalty"]

            # Roster need factor
            position_need_factor = (
                roster_analysis["position_needs"]
                .get(position, {})
                .get("urgency_multiplier", 1.0)
            )

            # Final weighted score
            final_score = (
                base_value
                * strategy_multiplier
                * bye_week_factor
                * position_need_factor
            )

            strategy_weighted_players.append(
                {
                    **player,
                    "strategy_score": round(final_score, 2),
                    "strategy_multiplier": round(strategy_multiplier, 2),
                    "position_need_factor": round(position_need_factor, 2),
                    "final_reasoning": [],
                }
            )

        # Sort by strategy-weighted score
        strategy_weighted_players.sort(key=lambda p: p["strategy_score"], reverse=True)

        # Generate recommendations
        top_pick = strategy_weighted_players[0] if strategy_weighted_players else None
        alternatives = (
            strategy_weighted_players[1:4] if len(strategy_weighted_players) > 1 else []
        )

        # Generate detailed reasoning for top pick
        if top_pick:
            reasoning = _generate_pick_reasoning(
                top_pick, roster_analysis, strategy, current_round, consider_bye_weeks
            )
            top_pick["detailed_reasoning"] = reasoning

        # Generate alternative reasoning
        for alt in alternatives:
            alt_reasoning = _generate_pick_reasoning(
                alt,
                roster_analysis,
                strategy,
                current_round,
                consider_bye_weeks,
                is_alternative=True,
            )
            alt["detailed_reasoning"] = alt_reasoning

        # Round-specific strategic guidance
        draft_rules = draft_state.get("draft_state", {}).get("draft_rules", {})
        round_guidance = _get_round_specific_guidance(
            current_round, draft_rules, strategy
        )

        # Position-specific recommendations
        position_recs = _get_position_specific_recommendations(
            available_players, roster_analysis, strategy
        )

        return {
            "success": True,
            "recommendation": {
                "primary_pick": top_pick,
                "alternatives": alternatives,
                "strategy_used": strategy,
                "consider_bye_weeks": consider_bye_weeks,
            },
            "analysis": {
                "current_round": current_round,
                "round_type": available_analysis["analysis"]["round_type"],
                "total_options_analyzed": len(available_players),
                "team_analyzed": (
                    analysis_team.get("team_name")
                    if analysis_team
                    else "General (no specific team)"
                ),
            },
            "roster_analysis": roster_analysis,
            "strategic_guidance": {
                "round_guidance": round_guidance,
                "position_recommendations": position_recs,
                "bye_week_considerations": available_analysis["bye_week_analysis"],
            },
            "confidence_factors": {
                "high_confidence": (
                    top_pick["strategy_score"] > 50 if top_pick else False
                ),
                "clear_best_pick": (
                    (top_pick["strategy_score"] - alternatives[0]["strategy_score"])
                    > 10
                    if top_pick and alternatives
                    else False
                ),
                "positional_need_urgent": any(
                    need["urgency"] == "Critical"
                    for need in roster_analysis["position_needs"].values()
                ),
                "bye_week_conflicts": len(
                    available_analysis["bye_week_analysis"]["problematic_weeks"]
                )
                > 0,
            },
        }

    except Exception as e:
        logger.error(f"Error generating draft pick suggestion: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "suggestion_failed",
            "troubleshooting": {
                "problem": f"Failed to generate draft pick suggestion: {str(e)}",
                "next_steps": [
                    "1. Verify draft_state contains valid data",
                    "2. Check that available players analysis is working",
                    "3. Ensure strategy parameter is valid",
                    "4. Verify current team information is available",
                ],
            },
        }


def _analyze_roster_needs(
    draft_state: Dict[str, Any], current_team: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze current roster composition and identify needs"""

    # Standard roster requirements
    roster_requirements = {
        "QB": {"starters": 1, "recommended_depth": 2, "max_useful": 3},
        "RB": {
            "starters": 2,
            "recommended_depth": 4,
            "max_useful": 6,
        },  # 2 starters + FLEX
        "WR": {
            "starters": 2,
            "recommended_depth": 4,
            "max_useful": 6,
        },  # 2 starters + FLEX
        "TE": {"starters": 1, "recommended_depth": 2, "max_useful": 3},
        "K": {"starters": 1, "recommended_depth": 1, "max_useful": 2},
        "DST": {"starters": 1, "recommended_depth": 1, "max_useful": 2},
    }

    current_roster = {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": []}

    # Count current roster by position
    if current_team:
        team_name = current_team.get("team_name")
        picks = draft_state.get("picks", [])

        for pick in picks:
            # Handle both "team" and "column_team" fields (column_team from sheets data)
            pick_team = pick.get("column_team") or pick.get("team")
            if pick_team == team_name:
                position = pick.get("position", "").upper()
                if position in current_roster:
                    current_roster[position].append(pick)

    # Analyze needs for each position
    position_needs = {}
    for position, requirements in roster_requirements.items():
        current_count = len(current_roster[position])
        starters_needed = max(0, requirements["starters"] - current_count)
        depth_needed = max(0, requirements["recommended_depth"] - current_count)

        # Determine urgency
        if current_count == 0 and requirements["starters"] > 0:
            urgency = "Critical"
            urgency_multiplier = 2.0
        elif starters_needed > 0:
            urgency = "High"
            urgency_multiplier = 1.5
        elif depth_needed > 0:
            urgency = "Medium"
            urgency_multiplier = 1.2
        elif current_count < requirements["max_useful"]:
            urgency = "Low"
            urgency_multiplier = 1.0
        else:
            urgency = "None"
            urgency_multiplier = 0.8  # Already have enough

        position_needs[position] = {
            "current_count": current_count,
            "starters_needed": starters_needed,
            "depth_needed": depth_needed,
            "urgency": urgency,
            "urgency_multiplier": urgency_multiplier,
            "current_players": [p.get("player_name") or p.get("player", "") for p in current_roster[position]],
        }

    return {
        "position_needs": position_needs,
        "current_roster": current_roster,
        "roster_balance_score": _calculate_roster_balance_score(
            current_roster, roster_requirements
        ),
    }


def _calculate_roster_balance_score(current_roster: Dict, requirements: Dict) -> float:
    """Calculate how balanced the current roster is (0-100)"""
    total_score = 0
    total_positions = 0

    for position, reqs in requirements.items():
        current_count = len(current_roster[position])
        optimal_count = reqs["recommended_depth"]

        # Score based on how close to optimal depth
        if current_count >= optimal_count:
            position_score = 100
        else:
            position_score = (current_count / optimal_count) * 100

        # Weight by position importance (starters need more weight)
        weight = reqs["starters"] * 2 + 1  # QB=3, RB=5, WR=5, TE=3, K=2, DST=2

        total_score += position_score * weight
        total_positions += weight

    return round(total_score / total_positions, 1) if total_positions > 0 else 0


def _calculate_strategy_multiplier(
    player: Dict, roster_analysis: Dict, strategy: str, current_round: int
) -> float:
    """Calculate strategy-specific multiplier for a player"""

    position = player["position"]
    tier_rank = player["value_metrics"]["tier_rank"]
    scarcity = player["scarcity_analysis"]["position_scarcity"]
    avg_rank = player["average_rank"]

    if strategy == "best_available":
        # Pure value play - highest ranked available
        if tier_rank <= 2:  # Elite/Tier 1
            return 1.8
        elif tier_rank <= 3:  # Tier 2
            return 1.4
        else:
            return 1.0

    elif strategy == "balanced":
        # Balance value with roster needs
        position_urgency = (
            roster_analysis["position_needs"].get(position, {}).get("urgency", "None")
        )

        if position_urgency == "Critical":
            return 1.6  # Must fill starter spots
        elif position_urgency == "High" and tier_rank <= 3:
            return 1.4  # Good value at needed position
        elif tier_rank <= 2:  # Elite talent
            return 1.3  # Always valuable
        elif position_urgency in ["Medium", "High"]:
            return 1.1  # Slight boost for roster needs
        else:
            return 1.0

    elif strategy == "upside":
        # Target high ceiling players, especially early in draft
        if current_round <= 5:  # Early rounds - still want elite talent
            if tier_rank <= 2:
                return 1.5
            elif scarcity == "High" and tier_rank <= 3:
                return 1.3  # Scarce position talent
            else:
                return 1.0
        else:  # Later rounds - swing for upside
            if avg_rank > 100 and player.get(
                "commentary"
            ):  # Sleeper pick with analysis
                return 1.4
            elif scarcity == "High":  # Positional upside
                return 1.2
            else:
                return 1.0

    elif strategy == "safe":
        # Target consistent, reliable players
        if tier_rank <= 3 and scarcity != "High":  # Avoid risky positions
            return 1.4
        elif position in ["RB", "WR"] and tier_rank <= 4:  # Safe skill positions
            return 1.2
        elif position in ["K", "DST"]:  # Don't reach for safe K/DST
            return 0.7
        else:
            return 1.0

    return 1.0


def _generate_pick_reasoning(
    player: Dict,
    roster_analysis: Dict,
    strategy: str,
    current_round: int,
    consider_bye_weeks: bool,
    is_alternative: bool = False,
) -> List[str]:
    """Generate detailed reasoning for a pick recommendation"""

    reasoning = []
    position = player["position"]
    name = player["name"]
    tier = player["value_metrics"]["tier"]
    avg_rank = player["average_rank"]
    strategy_score = player["strategy_score"]

    # Lead with recommendation type
    if is_alternative:
        reasoning.append(
            f"Alternative option: {name} ({position}) offers different strategic value"
        )
    else:
        reasoning.append(
            f"Primary recommendation: {name} ({position}) - Rank {avg_rank:.0f}"
        )

    # Value reasoning
    if tier in ["Elite", "Tier 1"]:
        reasoning.append(
            f"Excellent value - {tier} player still available at this pick"
        )
    elif tier == "Tier 2":
        reasoning.append(f"Good value - Solid {tier} option with reliable production")

    # Position need reasoning
    position_need = roster_analysis["position_needs"].get(position, {})
    urgency = position_need.get("urgency", "None")
    current_count = position_need.get("current_count", 0)

    if urgency == "Critical":
        reasoning.append(
            f"Critical need - You have {current_count} {position}s and need starters"
        )
    elif urgency == "High":
        reasoning.append(
            f"Important need - Helps fill starting lineup depth at {position}"
        )
    elif urgency == "Medium":
        reasoning.append(f"Depth play - Adds valuable {position} depth to your roster")

    # Strategy-specific reasoning
    if strategy == "best_available":
        reasoning.append("Best available player regardless of position needs")
    elif strategy == "balanced":
        if urgency in ["Critical", "High"]:
            reasoning.append("Perfect balance of value and roster need")
        else:
            reasoning.append("Best available player with roster construction in mind")
    elif strategy == "upside":
        if current_round <= 5:
            reasoning.append("High-ceiling player with league-winning potential")
        else:
            reasoning.append("Upside play - Could outperform ADP significantly")
    elif strategy == "safe":
        reasoning.append("Reliable, consistent production with low bust risk")

    # Scarcity reasoning
    scarcity = player["scarcity_analysis"]["position_scarcity"]
    pos_rank = player["value_metrics"]["positional_rank"]

    if scarcity == "High":
        reasoning.append(
            f"Positional scarcity - Only {pos_rank} quality {position}s left available"
        )
    elif position in ["TE", "QB"] and pos_rank <= 8:
        reasoning.append(
            f"Position timing - Good value for {position}{pos_rank} at this draft stage"
        )

    # Bye week reasoning
    if consider_bye_weeks:
        bye_week_severity = player["bye_week_analysis"]["conflict_severity"]
        bye_week = player["bye_week_analysis"]["bye_week"]

        if bye_week_severity == "High":
            reasoning.append(
                f"⚠️ Bye week concern - Week {bye_week} creates roster conflicts"
            )
        elif (
            bye_week_severity == "None"
            and player["bye_week_analysis"]["helps_bye_diversity"]
        ):
            reasoning.append(
                f"✓ Bye week help - Week {bye_week} improves roster flexibility"
            )

    # Final strategic note
    if strategy_score > 60:
        reasoning.append("Strong overall fit for your team and strategy")
    elif strategy_score > 40:
        reasoning.append("Solid pick that addresses multiple factors")
    else:
        reasoning.append("Reasonable option given current board state")

    return reasoning


def _get_round_specific_guidance(
    current_round: int, draft_rules: Dict, strategy: str
) -> Dict[str, Any]:
    """Provide round-specific strategic guidance"""

    auction_rounds = draft_rules.get("auction_rounds", [1, 2, 3])
    keeper_round = draft_rules.get("keeper_round", 4)

    if current_round in auction_rounds:
        return {
            "round_type": "auction",
            "key_focus": "Target specific players you want",
            "strategy_notes": [
                "Focus on elite talent and positional scarcity",
                "Don't worry about traditional draft value",
                "Target players that fit your long-term roster construction",
                "Consider which positions will be thin in snake rounds",
            ],
        }
    elif current_round == keeper_round:
        return {
            "round_type": "keeper",
            "key_focus": "Value opportunity if drafting",
            "strategy_notes": [
                "Limited participation creates value opportunities",
                "Good chance for above-ADP picks",
                "Fill gaps not covered by your keeper",
                "Consider positions that will be scarce later",
            ],
        }
    elif current_round <= 6:
        return {
            "round_type": "early_snake",
            "key_focus": "Secure elite talent and fill critical needs",
            "strategy_notes": [
                "Priority on RB/WR scarcity positions",
                "Avoid QB/TE/K/DST unless elite tier",
                "Build foundation with consistent producers",
                "Consider positional runs and timing",
            ],
        }
    elif current_round <= 12:
        return {
            "round_type": "mid_snake",
            "key_focus": "Balance starters and depth",
            "strategy_notes": [
                "Fill remaining starter needs",
                "Begin building bench depth",
                "Consider QB/TE if not addressed",
                "Target high-upside players in deeper positions",
            ],
        }
    else:
        return {
            "round_type": "late_snake",
            "key_focus": "Depth, upside, and late-round value",
            "strategy_notes": [
                "Target handcuffs and lottery tickets",
                "Fill K/DST if not done yet",
                "Look for breakout candidates",
                "Consider stashing injured players",
            ],
        }


def _get_position_specific_recommendations(
    available_players: List[Dict], roster_analysis: Dict, strategy: str
) -> Dict[str, Any]:
    """Get position-specific recommendations"""

    recommendations = {}

    for position in ["QB", "RB", "WR", "TE", "K", "DST"]:
        pos_players = [p for p in available_players if p["position"] == position][:3]
        position_need = roster_analysis["position_needs"].get(position, {})

        if pos_players:
            recommendations[position] = {
                "urgency": position_need.get("urgency", "None"),
                "current_count": position_need.get("current_count", 0),
                "top_available": [
                    {
                        "name": p["name"],
                        "rank": p["average_rank"],
                        "tier": p["value_metrics"]["tier"],
                        "value": p["value_metrics"]["overall_value"],
                    }
                    for p in pos_players
                ],
                "recommendation": _get_position_timing_rec(
                    position, position_need, pos_players, strategy
                ),
            }

    return recommendations


def _get_position_timing_rec(
    position: str, position_need: Dict, available_players: List[Dict], strategy: str
) -> str:
    """Get timing recommendation for a specific position"""

    urgency = position_need.get("urgency", "None")
    current_count = position_need.get("current_count", 0)
    best_available = available_players[0] if available_players else None

    if not best_available:
        return f"No quality {position}s available"

    best_tier = best_available["value_metrics"]["tier"]
    best_rank = best_available["average_rank"]

    if urgency == "Critical":
        return f"Draft now - Critical need and {best_available['name']} ({best_tier}) available"
    elif urgency == "High" and best_tier in ["Elite", "Tier 1", "Tier 2"]:
        return f"Strong consideration - {best_available['name']} fills need with good value"
    elif position in ["K", "DST"]:
        if best_rank < 150:
            return "Wait - Don't reach for K/DST this early"
        else:
            return f"Reasonable timing for {best_available['name']}"
    elif position == "QB" and current_count == 0:
        if best_tier in ["Elite", "Tier 1"]:
            return f"Consider now - {best_available['name']} is elite QB talent"
        elif best_rank > 100:
            return "Can wait - QB depth still available later"
        else:
            return f"Solid timing for {best_available['name']}"
    elif position == "TE" and current_count == 0:
        if best_tier in ["Elite", "Tier 1"]:
            return f"Consider now - Elite TE {best_available['name']} available"
        else:
            return "Can wait - TE streaming options available"
    else:
        if urgency in ["Medium", "High"]:
            return (
                f"Good depth option - {best_available['name']} adds roster flexibility"
            )
        else:
            return f"Optional - {best_available['name']} available if value aligns"


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
