#!/usr/bin/env python3
"""
Test that team lookup by owner name works correctly.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.tools import analyze_available_players


class TestOwnerTeamLookup:
    """Test that the tool correctly identifies the user's team by owner name."""

    @pytest.mark.asyncio
    async def test_exact_owner_name_match(self):
        """Test that exact owner name matching works."""

        # Mock rankings response
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Test Player",
                        "position": "QB",
                        "team": "TEST",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    }
                ]
            },
        }

        # Draft state with multiple teams, including one owned by "Adam"
        draft_state = {
            "picks": [],
            "teams": [
                {"team_name": "Niner Nation", "owner": "John Smith"},
                {"team_name": "Lambs", "owner": "Adam"},  # This should be found
                {"team_name": "Eagles", "owner": "Jane Doe"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("src.tools.analyze_players.USER_OWNER_NAME", "Adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=5
                )

        # Should identify "Lambs" as the team being analyzed
        assert result["success"] is True
        assert result["analysis"]["team_analyzed"] == "Lambs"

    @pytest.mark.asyncio
    async def test_partial_owner_name_match(self):
        """Test that partial owner name matching works."""

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Test Player",
                        "position": "QB",
                        "team": "TEST",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    }
                ]
            },
        }

        # Draft state where owner name has extra formatting
        draft_state = {
            "picks": [],
            "teams": [
                {"team_name": "Team One", "owner": "John Smith"},
                {
                    "team_name": "Team Two",
                    "owner": "Adam Johnson",
                },  # Should match "Adam"
                {"team_name": "Team Three", "owner": "Jane Doe"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("src.tools.analyze_players.USER_OWNER_NAME", "Adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=5
                )

        # Should identify "Team Two" as the team being analyzed
        assert result["success"] is True
        assert result["analysis"]["team_analyzed"] == "Team Two"

    @pytest.mark.asyncio
    async def test_no_match_provides_general_analysis(self):
        """Test that when no owner match is found, it provides general analysis instead of picking a random team."""

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Test Player",
                        "position": "QB",
                        "team": "TEST",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    }
                ]
            },
        }

        # Draft state where no team is owned by "Adam"
        draft_state = {
            "picks": [],
            "teams": [
                {
                    "team_name": "First Team",
                    "owner": "John Smith",
                },  # Should fall back to this
                {"team_name": "Second Team", "owner": "Jane Doe"},
                {"team_name": "Third Team", "owner": "Bob Wilson"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("src.tools.analyze_players.USER_OWNER_NAME", "Adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=5
                )

        # Should provide general analysis instead of picking arbitrary team
        assert result["success"] is True
        assert result["analysis"]["team_analyzed"] == "General (no specific team)"

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """Test that owner name matching is case insensitive."""

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Test Player",
                        "position": "QB",
                        "team": "TEST",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    }
                ]
            },
        }

        # Draft state with different case
        draft_state = {
            "picks": [],
            "teams": [
                {"team_name": "Team Alpha", "owner": "john smith"},
                {
                    "team_name": "Team Beta",
                    "owner": "ADAM",
                },  # Should match despite different case
                {"team_name": "Team Gamma", "owner": "Jane Doe"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("src.tools.analyze_players.USER_OWNER_NAME", "adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=5
                )

        # Should match "ADAM" despite case difference
        assert result["success"] is True
        assert result["analysis"]["team_analyzed"] == "Team Beta"
