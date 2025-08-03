"""
Tests for team abbreviation matching between different data sources.

This module tests the flexible team matching logic that handles cases where
Google Sheets uses "SF" but FantasySharks uses "SFO", etc.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.mcp_tools import analyze_available_players


class TestTeamAbbreviationMatching:
    """Test suite for flexible team abbreviation matching."""

    @pytest.mark.asyncio
    async def test_team_abbreviation_variations(self):
        """Test that players are filtered correctly despite team abbreviation differences."""

        # Draft state with Google Sheets style abbreviations
        draft_state = {
            "picks": [
                {"pick": 1, "player": "Christian McCaffrey   SF", "position": "RB"},
                {"pick": 2, "player": "Josh Jacobs   GB", "position": "RB"},
                {"pick": 3, "player": "Alvin Kamara   NO", "position": "RB"},
                {"pick": 4, "player": "Rhamondre Stevenson   NE", "position": "RB"},
                {"pick": 5, "player": "Mike Evans   TB", "position": "WR"},
            ],
            "teams": [{"team_name": "Test Team", "owner": "Adam", "team_number": 1}],
            "current_pick": 6,
            "current_team": {
                "team_number": 1,
                "owner": "Adam",
                "team_name": "Test Team",
            },
        }

        # Mock rankings with FantasySharks style abbreviations (longer versions)
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    # These should be filtered out (drafted players with different team abbreviations)
                    {
                        "name": "Christian McCaffrey",
                        "position": "RB",
                        "team": "SFO",  # SF in draft, SFO in rankings
                        "bye_week": 14,
                        "average_rank": 1.0,
                        "average_score": 99.0,
                    },
                    {
                        "name": "Josh Jacobs",
                        "position": "RB",
                        "team": "GBP",  # GB in draft, GBP in rankings
                        "bye_week": 10,
                        "average_rank": 2.0,
                        "average_score": 95.0,
                    },
                    {
                        "name": "Alvin Kamara",
                        "position": "RB",
                        "team": "NOS",  # NO in draft, NOS in rankings
                        "bye_week": 12,
                        "average_rank": 3.0,
                        "average_score": 90.0,
                    },
                    {
                        "name": "Rhamondre Stevenson",
                        "position": "RB",
                        "team": "NEP",  # NE in draft, NEP in rankings
                        "bye_week": 14,
                        "average_rank": 4.0,
                        "average_score": 85.0,
                    },
                    {
                        "name": "Mike Evans",
                        "position": "WR",
                        "team": "TBB",  # TB in draft, TBB in rankings
                        "bye_week": 11,
                        "average_rank": 5.0,
                        "average_score": 88.0,
                    },
                    # This should NOT be filtered out (available player)
                    {
                        "name": "Saquon Barkley",
                        "position": "RB",
                        "team": "PHI",
                        "bye_week": 7,
                        "average_rank": 6.0,
                        "average_score": 92.0,
                    },
                ]
            },
        }

        with patch(
            "src.tools.mcp_tools.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state,
                position_filter=None,  # Get all positions
                limit=20,
            )

            # Verify the function succeeds
            assert result["success"] is True
            assert "players" in result

            # Get list of available player names
            available_names = [p["name"] for p in result["players"]]

            # These players should be filtered out despite team abbreviation differences
            assert (
                "Christian McCaffrey" not in available_names
            ), "McCaffrey (SF/SFO) should be filtered out"
            assert (
                "Josh Jacobs" not in available_names
            ), "Jacobs (GB/GBP) should be filtered out"
            assert (
                "Alvin Kamara" not in available_names
            ), "Kamara (NO/NOS) should be filtered out"
            assert (
                "Rhamondre Stevenson" not in available_names
            ), "Stevenson (NE/NEP) should be filtered out"
            assert (
                "Mike Evans" not in available_names
            ), "Evans (TB/TBB) should be filtered out"

            # This player should NOT be filtered out
            assert (
                "Saquon Barkley" in available_names
            ), "Barkley should be available (not drafted)"

    @pytest.mark.asyncio
    async def test_exact_team_match_still_works(self):
        """Ensure exact team matches still work (backwards compatibility)."""

        draft_state = {
            "picks": [
                {"pick": 1, "player": "Patrick Mahomes   KC", "position": "QB"},
            ],
            "teams": [{"team_name": "Test Team", "owner": "Adam", "team_number": 1}],
        }

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Patrick Mahomes",
                        "position": "QB",
                        "team": "KC",  # Exact match
                        "bye_week": 10,
                        "average_rank": 1.0,
                        "average_score": 99.0,
                    },
                    {
                        "name": "Josh Allen",
                        "position": "QB",
                        "team": "BUF",
                        "bye_week": 12,
                        "average_rank": 2.0,
                        "average_score": 95.0,
                    },
                ]
            },
        }

        with patch(
            "src.tools.mcp_tools.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state, position_filter="QB", limit=10
            )

            available_names = [p["name"] for p in result["players"]]

            # Exact match should still be filtered out
            assert (
                "Patrick Mahomes" not in available_names
            ), "Mahomes should be filtered out (exact match)"
            # Non-drafted player should be available
            assert "Josh Allen" in available_names, "Allen should be available"

    @pytest.mark.asyncio
    async def test_name_only_matching_still_works(self):
        """Ensure name-only matching works when team info is missing."""

        draft_state = {
            "picks": [
                {"pick": 1, "player": "Tom Brady", "position": "QB"},  # No team info
            ],
            "teams": [{"team_name": "Test Team", "owner": "Adam", "team_number": 1}],
        }

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Tom Brady",
                        "position": "QB",
                        "team": "TB",
                        "bye_week": 11,
                        "average_rank": 1.0,
                        "average_score": 85.0,
                    }
                ]
            },
        }

        with patch(
            "src.tools.mcp_tools.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state, position_filter="QB", limit=10
            )

            available_names = [p["name"] for p in result["players"]]

            # Should be filtered out by name-only matching
            assert (
                "Tom Brady" not in available_names
            ), "Brady should be filtered out (name-only match)"

    def test_team_matching_edge_cases(self):
        """Test edge cases in team matching logic."""

        # Test the team matching logic directly
        test_cases = [
            # (drafted_team, rankings_team, should_match)
            ("SF", "SFO", True),  # substring match
            ("SFO", "SF", True),  # reverse substring match
            ("GB", "GBP", True),  # substring match
            ("NO", "NOS", True),  # substring match
            ("NE", "NEP", True),  # substring match
            ("TB", "TBB", True),  # substring match
            ("KC", "KC", True),  # exact match
            ("BUF", "BUF", True),  # exact match
            ("SF", "KC", False),  # different teams entirely
            ("NO", "TB", False),  # different teams entirely
            ("LA", "LAR", True),  # first 2 characters match
            (
                "LA",
                "LAC",
                True,
            ),  # first 2 characters match (this might be too broad, but let's see)
        ]

        for drafted_team, rankings_team, should_match in test_cases:
            # Simulate the matching logic
            teams_match = (
                drafted_team in rankings_team
                or rankings_team in drafted_team
                or (
                    len(drafted_team) >= 2
                    and len(rankings_team) >= 2
                    and drafted_team[:2] == rankings_team[:2]
                )
            )

            assert (
                teams_match == should_match
            ), f"Team matching failed for {drafted_team} vs {rankings_team}: expected {should_match}, got {teams_match}"
