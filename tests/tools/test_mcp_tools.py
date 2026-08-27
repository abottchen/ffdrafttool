from unittest.mock import patch

import pytest

from src.tools import (
    get_player_rankings,
)
from tests.test_fixtures import FixtureFantasySharksScraper


class TestGetPlayerRankings:
    @pytest.mark.asyncio
    async def test_get_player_rankings_success(self):
        # Use fixture scraper to avoid network requests in CI
        with patch(
            "src.tools.player_rankings.FantasySharksScraper",
            FixtureFantasySharksScraper,
        ):
            result = await get_player_rankings(force_refresh=True)

        assert result["success"]
        assert "players" in result
        assert isinstance(result["players"], list)

        # Should have players from fixture
        assert result["players"]
        # Check player structure
        first_player = result["players"][0]
        assert "name" in first_player
        assert "position" in first_player
        assert "team" in first_player
        assert "bye_week" in first_player
        assert "ranking" in first_player
        assert "projected_points" in first_player

    @pytest.mark.asyncio
    async def test_get_player_rankings_with_position_filter(self):
        # Use fixture scraper to avoid network requests in CI
        with patch(
            "src.tools.player_rankings.FantasySharksScraper",
            FixtureFantasySharksScraper,
        ):
            result = await get_player_rankings(position="QB", force_refresh=True)

        assert result["success"]
        assert result["position_filter"] == "QB"

        # Should have players from fixture
        assert result["players"]
        players = result["players"]
        assert all(p["position"] == "QB" for p in players)

        # Verify we have expected fixture data
        assert (
            len(players) >= 3
        )  # Should have Josh Allen, Lamar Jackson, Patrick Mahomes from fixture
        player_names = [p["name"] for p in players]
        assert "Josh Allen" in player_names

    @pytest.mark.asyncio
    async def test_get_player_rankings_invalid_position(self):
        """Test error handling for invalid position"""
        result = await get_player_rankings(position="INVALID")

        assert not result["success"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_player_rankings_force_refresh(self):
        """Test force refresh functionality"""
        result = await get_player_rankings(force_refresh=True)

        # Should still succeed whether data is available or not
        assert "success" in result


# Only testing the simplified player rankings tool.
# The deprecated analyze_available_players and suggest_draft_pick tools
# have been removed as part of the MCP server simplification.


class TestServerToolRegistration:
    """The MCP server must actually expose each tool to clients."""

    @pytest.mark.asyncio
    async def test_auction_state_tool_is_registered(self):
        """get_auction_state is useless to the draft client unless it is registered."""
        from src.server import mcp

        tool_names = {tool.name for tool in await mcp.list_tools()}

        assert "get_auction_state_tool" in tool_names


class TestTeamRosterToolSerialization:
    """The server wrapper must serialize roster entries that carry a price."""

    @pytest.mark.asyncio
    async def test_team_roster_tool_serializes_price(self):
        """Roster entries are dicts now; the wrapper must not re-serialize them."""
        import json

        from src.server import get_team_roster_tool

        roster = {
            "success": True,
            "owner_name": "Buffy",
            "players": [
                {
                    "name": "Josh Allen",
                    "team": "BUF",
                    "position": "QB",
                    "bye_week": 12,
                    "ranking": 1,
                    "projected_points": 99.0,
                    "injury_status": "HEALTHY",
                    "notes": "",
                    "price": 34,
                }
            ],
        }

        with patch("src.server.get_team_roster", return_value=roster):
            payload = json.loads(await get_team_roster_tool("Buffy"))

        assert payload["success"] is True
        assert payload["players"][0]["price"] == 34
        assert payload["players"][0]["name"] == "Josh Allen"
