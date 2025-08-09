#!/usr/bin/env python3
"""
Fantasy Football Draft Assistant MCP Server

This server provides fantasy football data tools including player rankings,
draft progress tracking, player information, and available player lists.
Analysis and recommendations are handled by the MCP client.
"""

import json
import logging

# Configure logging to stderr only (stdout is for MCP protocol)
import sys

# Configure logging to both stderr and file
# Create logs directory if it doesn't exist
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.config import DEFAULT_SHEET_ID, DEFAULT_SHEET_RANGE, LOG_LEVEL
from src.tools.available_players import get_available_players
from src.tools.draft_progress import read_draft_progress
from src.tools.player_info import get_player_info
from src.tools.player_rankings import get_player_rankings
from src.tools.team_roster import get_team_roster

logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(
            logs_dir / "fantasy_football_mcp.log", mode="a", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("fantasy-football-mcp")

# Create FastMCP server instance
mcp = FastMCP("Fantasy Football Draft Assistant")


@mcp.tool()
async def get_player_rankings_tool(
    position: str = None, force_refresh: bool = False
) -> str:
    """
    Get player rankings by position with caching support.

    Args:
        position: Position filter (QB, RB, WR, TE, K, DST). If None, returns all positions.
        force_refresh: If True, ignore cache and fetch fresh data from FantasySharks

    Returns:
        JSON string with player rankings data
    """
    logger.info(
        f"get_player_rankings called with position={position}, force_refresh={force_refresh}"
    )

    try:
        result = await get_player_rankings(position, force_refresh)
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
    """
    Read current draft progress from Google Sheets.

    Args:
        sheet_id: Google Sheets ID from the URL
        sheet_range: Range to read from the sheet
        force_refresh: If True, ignore cache and fetch fresh data from Google Sheets

    Returns:
        JSON string with current draft state and picks
    """
    logger.info(
        f"read_draft_progress called with sheet_id={sheet_id}, range={sheet_range}, force_refresh={force_refresh}"
    )

    try:
        result = await read_draft_progress(sheet_id, sheet_range, force_refresh)
        # Check if result is a Pydantic model or a dict (for error responses)
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json(indent=2)
        else:
            # Fallback for error responses or other dict formats
            return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in read_draft_progress: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def get_available_players_tool(position: str, limit: int) -> str:
    """
    Get a list of top undrafted players at a position.

    Args:
        position: Position to filter (QB, RB, WR, TE, K, DST)
        limit: Maximum number of players to return

    Returns:
        JSON string with list of available players
    """
    logger.info(f"get_available_players called with position={position}, limit={limit}")

    try:
        result = await get_available_players(position, limit)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_available_players: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def get_player_info_tool(
    last_name: str,
    first_name: str = None,
    team: str = None,
    position: str = None,
) -> str:
    """
    Get detailed information for a specific player.

    Args:
        last_name: Player's last name
        first_name: Player's first name (optional)
        team: Team abbreviation (optional)
        position: Position filter (optional)

    Returns:
        JSON string with player information
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


@mcp.tool()
async def get_team_roster_tool(owner_name: str) -> str:
    """
    Get all drafted players for a specific owner.

    Args:
        owner_name: Name of the team owner to get roster for

    Returns:
        JSON string with owner's name and list of Player objects
    """
    logger.info(f"get_team_roster called with owner_name={owner_name}")

    try:
        result = await get_team_roster(owner_name)

        # Convert Player objects to dicts using Pydantic serialization
        if result.get("success") and "players" in result:
            serialized_players = [
                player.model_dump(mode="json") for player in result["players"]
            ]
            result["players"] = serialized_players

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_team_roster: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


def main():
    """Run the MCP server."""
    logger.info("Starting Fantasy Football Draft Assistant MCP Server...")
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
