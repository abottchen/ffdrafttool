#!/usr/bin/env python3
"""
Test that drafted player filtering works correctly with composite keys.
Specifically testing the issue where "Jahmyr Gibbs DET" in draft data
should be properly filtered from available players.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.tools import analyze_available_players


class TestDraftedPlayerCompositeKeys:
    """Test that drafted player filtering works with composite keys."""

    @pytest.mark.asyncio
    async def test_drafted_player_with_team_filtered_correctly(self):
        """Test that 'Jahmyr Gibbs DET' format is properly filtered from available players."""

        # Mock rankings response that includes Jahmyr Gibbs
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Jahmyr Gibbs",
                        "position": "RB",
                        "team": "DET",
                        "rank": 15,
                        "score": 85,
                        "bye_week": 5,
                        "average_rank": 15,
                        "average_score": 85,
                    },
                    {
                        "name": "Christian McCaffrey",
                        "position": "RB",
                        "team": "SF",
                        "rank": 1,
                        "score": 98,
                        "bye_week": 9,
                        "average_rank": 1,
                        "average_score": 98,
                    },
                ]
            },
        }

        # Draft state where Jahmyr Gibbs has been drafted in "Player Team" format
        draft_state = {
            "picks": [
                {
                    "round": 2,
                    "pick": 15,
                    "team": "Lambs",
                    "player": "Jahmyr Gibbs DET",  # This format should be filtered
                    "position": "RB",
                    "bye_week": 5,
                }
            ],
            "teams": [
                {"team_name": "Lambs", "owner": "Adam"},
                {"team_name": "Eagles", "owner": "Jane"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("config.USER_OWNER_NAME", "Adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=10
                )

        # Should successfully filter out Jahmyr Gibbs
        assert result["success"] is True

        # Check that Jahmyr Gibbs is NOT in the available players
        available_player_names = [p["name"] for p in result["players"]]
        assert "Jahmyr Gibbs" not in available_player_names

        # But Christian McCaffrey should still be available
        assert "Christian McCaffrey" in available_player_names

    @pytest.mark.asyncio
    async def test_same_name_different_teams_handled_correctly(self):
        """Test that players with same name on different teams are handled correctly."""

        # Mock rankings response with two players with same name on different teams
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "NYJ",
                        "rank": 45,
                        "score": 75,
                        "bye_week": 12,
                        "average_rank": 45,
                        "average_score": 75,
                    },
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "PIT",
                        "rank": 95,
                        "score": 55,
                        "bye_week": 9,
                        "average_rank": 95,
                        "average_score": 55,
                    },
                ]
            },
        }

        # Draft state where only the NYJ Mike Williams has been drafted
        draft_state = {
            "picks": [
                {
                    "round": 4,
                    "pick": 45,
                    "team": "Eagles",
                    "player": "Mike Williams NYJ",  # Only NYJ version drafted
                    "position": "WR",
                    "bye_week": 12,
                }
            ],
            "teams": [
                {"team_name": "Lambs", "owner": "Adam"},
                {"team_name": "Eagles", "owner": "Jane"},
            ],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            with patch("config.USER_OWNER_NAME", "Adam"):
                mock_rankings.return_value = mock_rankings_response

                result = await analyze_available_players(
                    draft_state=draft_state, limit=10
                )

        # Should successfully filter correctly
        assert result["success"] is True

        # Check available players
        available_players = result["players"]
        mike_williams_players = [
            p for p in available_players if p["name"] == "Mike Williams"
        ]

        # Should have exactly 1 Mike Williams remaining (the PIT one)
        assert len(mike_williams_players) == 1
        assert mike_williams_players[0]["team"] == "PIT"
