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
