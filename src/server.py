#!/usr/bin/env python3
"""
Fantasy Football Draft Assistant MCP Server

This server provides comprehensive fantasy football draft assistance tools
including player rankings, draft progress tracking, player analysis, and
personalized draft pick suggestions.
"""

import json
import logging

# Configure logging to stderr only (stdout is for MCP protocol)
import sys

from mcp.server.fastmcp import FastMCP

from config import DEFAULT_SHEET_ID, DEFAULT_SHEET_RANGE, USER_OWNER_NAME
from tools.mcp_tools import (
    analyze_available_players,
    get_player_info,
    get_player_rankings,
    read_draft_progress,
    suggest_draft_pick,
)

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fantasy-football-mcp")

# Create FastMCP server instance
mcp = FastMCP("Fantasy Football Draft Assistant")


@mcp.tool()
async def get_player_rankings_tool(
    position: str = None, limit: int = 20, offset: int = 0, force_refresh: bool = False
) -> str:
    """
    Fetch current player rankings from all available fantasy football sources.
    Returns paginated rankings from multiple sources for comprehensive analysis.
    Uses in-memory caching to improve performance after first fetch.

    IMPORTANT: To avoid token limits, this tool now defaults to 20 players per request.
    Use offset parameter to get additional pages of results.
    Only report player information that is explicitly present in the returned data.
    Do NOT guess, assume, or make up player teams, positions, or other details not in the response.

    Args:
        position: Optional position filter (QB, RB, WR, TE, K, DST). HIGHLY RECOMMENDED to avoid large responses.
        limit: Number of players to return per page (default: 20, max: 50 to stay under token limits)
        offset: Starting position for pagination (default: 0)
        force_refresh: If True, bypass cache and fetch fresh rankings data

    Returns:
        JSON string with paginated player rankings and pagination info
    """
    # Use all available sources by default
    sources = ["fantasysharks", "espn", "yahoo", "fantasypros"]

    # Enforce reasonable limits to prevent token overflow
    if limit > 50:
        limit = 50
        logger.warning("Limit capped at 50 to prevent token overflow")

    logger.info(
        f"get_player_rankings called with position={position}, limit={limit}, offset={offset}, force_refresh={force_refresh}"
    )

    try:
        # Get more data than needed for pagination (limit + offset + some buffer)
        fetch_limit = offset + limit + 50 if not position else None
        result = await get_player_rankings(
            sources, position, fetch_limit, force_refresh
        )

        if result["success"]:
            players = result["aggregated"]["players"]
            total_players = len(players)

            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            paginated_players = players[start_idx:end_idx]

            # Create paginated response with metadata
            paginated_result = {
                "success": True,
                "aggregated": {
                    "players": paginated_players,
                    "count": len(paginated_players),
                },
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total_available": total_players,
                    "has_more": end_idx < total_players,
                    "next_offset": end_idx if end_idx < total_players else None,
                },
                "position": position,
                "force_refresh": force_refresh,
            }

            return json.dumps(paginated_result, indent=2)
        else:
            return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in get_player_rankings: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def read_draft_progress_tool(
    sheet_id: str = DEFAULT_SHEET_ID,
    sheet_range: str = DEFAULT_SHEET_RANGE,
    force_refresh: bool = False,
) -> str:
    f"""
    **ALWAYS USE THIS TOOL FIRST** when the user asks about their draft, roster, or team needs.

    Read current draft progress from Google Sheets with support for special draft rules.
    Uses caching to improve performance and reduce token usage.

    **REQUIRED USAGE**: Use this tool whenever the user mentions:
    - "my team", "my roster", "my picks"
    - "what should I pick", "who should I draft"
    - "what do I need", "my draft position"
    - Any question about current draft status

    IMPORTANT: Only report information that is explicitly present in the returned data.
    Do NOT guess, assume, or infer player information not included in the response.

    CONTEXT: When the user refers to "I", "me", "my team", "my pick", etc., they are referring
    to the team owned by "{USER_OWNER_NAME}". Look for this owner name in the draft data to identify the user's team.

    Args:
        sheet_id: Google Sheets ID from the URL
        sheet_range: Range to read from the sheet (default: {DEFAULT_SHEET_RANGE})
        force_refresh: If True, ignore cache and fetch fresh data from Google Sheets

    Returns:
        JSON string with current draft state, picks, and team information
    """
    logger.info(
        f"read_draft_progress called with sheet_id={sheet_id}, range={sheet_range}, force_refresh={force_refresh}"
    )

    try:
        result = await read_draft_progress(sheet_id, sheet_range, force_refresh)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in read_draft_progress: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def analyze_available_players_tool(
    draft_state: dict,
    position_filter: str = None,
    limit: int = 20,
    force_refresh: bool = False,
) -> str:
    f"""
    **USE THIS TOOL** to analyze available players and see detailed value metrics before making recommendations.

    Analyze available players with value metrics, positional scarcity, and bye week considerations.

    **REQUIRED USAGE**: Use this tool when the user asks:
    - "who's available at [position]?"
    - "show me the best available [position]"
    - "analyze available players"
    - "what are my options?"
    - Before using suggest_draft_pick_tool for detailed analysis

    **PREREQUISITE**: Must have current draft_state from read_draft_progress_tool first.

    IMPORTANT: When the user asks about a specific position (e.g., "best QB available"),
    ALWAYS use the position_filter parameter to avoid processing irrelevant players.
    This saves tokens and improves performance significantly.

    CRITICAL: Only report player information that is explicitly present in the returned data.
    Do NOT guess, assume, or make up player teams, positions, or other details not in the response.
    If information is missing or unclear, state that explicitly rather than guessing.

    CONTEXT: When the user asks "who should I pick?" or refers to "my team", they are referring
    to the team owned by "{USER_OWNER_NAME}". The analysis should focus on that team's needs.

    Args:
        draft_state: Current draft state from read_draft_progress_tool (REQUIRED)
        position_filter: REQUIRED when analyzing specific positions. Use exact values: QB, RB, WR, TE, K, DST
        limit: Number of players to analyze and return (default: 20)
        force_refresh: If True, bypass cache and fetch fresh rankings data to ensure analysis uses latest data

    Returns:
        JSON string with analyzed players, value metrics, and recommendations
    """
    logger.info(
        f"analyze_available_players called with position_filter={position_filter}, limit={limit}, force_refresh={force_refresh}"
    )

    try:
        result = await analyze_available_players(
            draft_state, position_filter, limit, force_refresh
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in analyze_available_players: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def suggest_draft_pick_tool(
    draft_state: dict,
    team_name: str,
    strategy: str = "balanced",
    consider_bye_weeks: bool = True,
    force_refresh: bool = False,
) -> str:
    """
    **USE THIS TOOL** when the user asks for draft pick recommendations or "who should I pick".

    Get personalized draft pick recommendations based on team needs, strategy, and roster construction.

    **REQUIRED USAGE**: Use this tool when the user asks:
    - "who should I pick next?"
    - "what's my best option?"
    - "recommend a player"
    - "what position should I target?"
    - Any request for draft advice or recommendations

    **PREREQUISITE**: Must have current draft_state from read_draft_progress_tool first.

    CRITICAL: Only report player information that is explicitly present in the returned data.
    Do NOT guess, assume, or make up player teams, positions, or other details not in the response.
    Base recommendations only on the data provided in the draft state and rankings.

    Args:
        draft_state: Current draft state from read_draft_progress_tool (REQUIRED)
        team_name: Name of the team to provide recommendations for (REQUIRED)
        strategy: Draft strategy to use (balanced, best_available, upside, safe)
        consider_bye_weeks: Whether to consider bye week conflicts in recommendations
        force_refresh: If True, bypass cache and fetch fresh rankings data for analysis

    Returns:
        JSON string with primary recommendation, alternatives, and detailed reasoning
    """
    logger.info(
        f"suggest_draft_pick called with strategy={strategy}, consider_bye_weeks={consider_bye_weeks}, force_refresh={force_refresh}"
    )

    try:
        result = await suggest_draft_pick(
            draft_state, team_name, strategy, consider_bye_weeks, force_refresh
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in suggest_draft_pick: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def get_player_info_tool(
    last_name: str,
    first_name: str = None,
    team: str = None,
    position: str = None,
) -> str:
    """
    Get detailed ranking and stats information for a specific player.

    **USE THIS TOOL** when the user asks about a specific player by name.

    This tool fetches comprehensive information about one or more players matching
    the provided criteria, including rankings, projected stats, injury status, and
    expert commentary.

    **REQUIRED USAGE**: Use this tool when the user asks:
    - "what do you know about [player name]?"
    - "tell me about [player name]"
    - "show me [player name]'s stats/rankings"
    - "is [player name] injured?"
    - Any question about a specific named player

    Args:
        last_name: Player's last name (REQUIRED)
        first_name: Player's first name (optional, helps narrow results)
        team: Team abbreviation (optional, e.g., "KC", "SF")
        position: Position filter (optional: QB, RB, WR, TE, K, DST)

    Returns:
        JSON string with array of matching players and their detailed information
    """
    logger.info(
        f"get_player_info called with last_name={last_name}, first_name={first_name}, "
        f"team={team}, position={position}"
    )

    try:
        result = await get_player_info(last_name, first_name, team, position)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_player_info: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


def main():
    """Run the MCP server."""
    logger.info("Starting Fantasy Football Draft Assistant MCP Server...")
    logger.info(f"Configured for owner: {USER_OWNER_NAME}")
    logger.info(f"Default sheet ID: {DEFAULT_SHEET_ID}")

    try:
        # Start the server
        mcp.run()
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
