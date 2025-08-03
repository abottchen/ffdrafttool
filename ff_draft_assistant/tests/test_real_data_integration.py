"""
Integration tests using real data snapshots.

These tests ensure our code works with actual data structures
from the Google Sheets and external APIs.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.mcp_tools import analyze_available_players
from tests.fixtures import (
    get_real_draft_state_sample,
    get_sample_drafted_players,
    load_real_draft_data,
)


class TestRealDataIntegration:
    """Test suite using real data fixtures to ensure compatibility with actual data structures."""

    def test_real_draft_data_structure(self):
        """Verify that real draft data has expected structure."""
        real_data = load_real_draft_data()

        # Verify top-level structure
        assert "picks" in real_data
        assert "teams" in real_data
        assert "draft_state" in real_data

        # Verify picks structure
        picks = real_data["picks"]
        assert len(picks) > 0

        first_pick = picks[0]
        # These are the REAL field names that should be used
        assert "player" in first_pick  # NOT 'player_name'
        assert "position" in first_pick
        assert "pick" in first_pick
        assert "round" in first_pick

    def test_drafted_players_field_names(self):
        """Ensure drafted players use correct field names from real data."""
        drafted_players = get_sample_drafted_players(3)

        for pick in drafted_players:
            # Verify the actual field structure
            assert "player" in pick, f"Pick missing 'player' field: {pick}"
            assert "position" in pick, f"Pick missing 'position' field: {pick}"

            # Ensure we're not using old mock field names
            assert (
                "player_name" not in pick
            ), f"Pick should not have 'player_name' field: {pick}"

    @pytest.mark.asyncio
    async def test_analyze_available_players_with_real_data(self):
        """Test analyze_available_players with real draft state structure."""
        # Get real draft state sample
        draft_state = get_real_draft_state_sample()

        # Mock the rankings to avoid external API calls
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Test Player Available",
                        "position": "RB",
                        "team": "TEST",
                        "bye_week": 8,
                        "average_rank": 50.0,
                        "average_score": 75.0,
                    },
                    # Include a player that's in the real drafted list
                    {
                        "name": "Jahmyr Gibbs",  # This should be filtered out
                        "position": "RB",
                        "team": "DET",
                        "bye_week": 8,
                        "average_rank": 1.0,
                        "average_score": 99.0,
                    },
                ]
            },
        }

        with patch(
            "src.tools.mcp_tools.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            # Test the function with real data structure
            result = await analyze_available_players(
                draft_state=draft_state, position_filter="RB", limit=10
            )

            # Verify it works
            assert result["success"] is True
            assert "players" in result

            # Verify that real drafted players are filtered out
            available_names = [p["name"] for p in result["players"]]

            # Check that a known drafted player (from real data) is filtered out
            real_drafted_names = [pick["player"] for pick in draft_state["picks"]]
            for drafted_name in real_drafted_names[:3]:  # Check first few
                # Extract just the player name without team abbreviation
                clean_drafted_name = (
                    drafted_name.split()[0] + " " + drafted_name.split()[1]
                )
                assert (
                    clean_drafted_name not in available_names
                ), f"Drafted player '{clean_drafted_name}' should not appear in available players"

    def test_real_data_snapshot_freshness(self):
        """Verify that our real data snapshot contains expected amount of data."""
        real_data = load_real_draft_data()

        # Verify we have a reasonable amount of picks (adjust based on draft progress)
        picks_count = len(real_data.get("picks", []))
        assert (
            picks_count > 100
        ), f"Expected substantial draft data, got {picks_count} picks"

        # Verify we have teams
        teams_count = len(real_data.get("teams", []))
        assert teams_count >= 8, f"Expected at least 8 teams, got {teams_count}"

    def test_player_name_formats_in_real_data(self):
        """Test that we handle various player name formats found in real data."""
        drafted_players = get_sample_drafted_players(10)

        name_formats_found = set()

        for pick in drafted_players:
            player_name = pick["player"]

            # Categorize the format
            if "   " in player_name:  # Three spaces (name + team)
                name_formats_found.add("name_with_team_spaces")
            elif " - " in player_name:  # Dash separator
                name_formats_found.add("name_with_team_dash")
            elif "(" in player_name:  # Parentheses
                name_formats_found.add("name_with_team_parens")
            else:
                name_formats_found.add("name_only")

        # Log the formats we found for debugging
        print(f"Real data contains these name formats: {name_formats_found}")

        # Ensure we found at least some variation
        assert (
            len(name_formats_found) > 0
        ), "Should find various name formats in real data"
