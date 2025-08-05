#!/usr/bin/env python3
"""
Test for the drafted player filtering fix - specifically testing team abbreviation normalization.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.tools import analyze_available_players
from src.models.test_data import (
    DraftData,
    Pick,
    Team,
    DraftStateInfo,
    create_basic_pick
)


class TestDraftedPlayerFilteringFix:
    """Test the fix for drafted player filtering with team abbreviations."""

    @pytest.mark.asyncio
    async def test_team_abbreviation_filtering(self):
        """Test that players with team abbreviations in rankings are properly filtered out when drafted."""

        # Mock rankings data that includes team abbreviations (like real rankings might)
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Jahmyr Gibbs (DET)",  # This player is drafted but has team info
                        "position": "RB",
                        "team": "DET",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    },
                    {
                        "name": "Bijan Robinson (ATL)",
                        "position": "RB",
                        "team": "ATL",
                        "rank": 2,
                        "score": 94,
                        "bye_week": 12,
                    },
                    {
                        "name": "A.J. Brown (PHI)",  # This player is drafted with punctuation
                        "position": "WR",
                        "team": "PHI",
                        "rank": 3,
                        "score": 93,
                        "bye_week": 7,
                    },
                    {
                        "name": "Marvin Harrison Jr. (ARI)",  # This player is drafted with suffix
                        "position": "WR",
                        "team": "ARI",
                        "rank": 4,
                        "score": 92,
                        "bye_week": 14,
                    },
                    {
                        "name": "Amon-Ra St. Brown (DET)",  # Available player - not drafted
                        "position": "WR",
                        "team": "DET",
                        "rank": 5,
                        "score": 91,
                        "bye_week": 8,
                    },
                ]
            },
        }

        # Draft state where some players are drafted (without team abbreviations)
        picks = [
            create_basic_pick(1, 1, "Team A", "Jahmyr Gibbs", "RB"),
            create_basic_pick(2, 1, "Team B", "A.J. Brown", "WR"),
            create_basic_pick(3, 1, "Team C", "Marvin Harrison Jr.", "WR"),
        ]
        
        teams = [
            Team(team_name="Team A", owner="Owner A"),
            Team(team_name="Team B", owner="Owner B"),
            Team(team_name="Team C", owner="Owner C"),
        ]
        
        draft_data = DraftData(
            picks=picks,
            teams=teams,
            draft_state=DraftStateInfo(
                total_picks=3,
                total_teams=3,
                current_round=1,
                completed_rounds=0,
            )
        )
        draft_state = draft_data.to_dict()

        # Mock the get_player_rankings function
        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            # Analyze available players
            result = await analyze_available_players(
                draft_state=draft_state,
                position_filter=None,  # Get all positions
                limit=10,
                force_refresh=False,
            )

        # Verify the result
        assert result["success"] is True
        available_players = result["players"]

        # Extract player names from available players
        available_names = [player["name"] for player in available_players]

        # Drafted players should NOT appear in available players
        # These are the drafted players (normalized names should match)
        drafted_players = ["Jahmyr Gibbs", "A.J. Brown", "Marvin Harrison Jr."]

        for drafted_player in drafted_players:
            # Check that no available player matches this drafted player
            for available_name in available_names:
                # Apply same normalization logic to check
                def normalize(name):
                    norm = name.lower()
                    if "(" in norm:
                        norm = norm.split("(")[0]
                    norm = norm.replace(".", "").replace("'", "").replace("-", "")
                    norm = norm.replace("jr", "").replace("sr", "")
                    return " ".join(norm.split()).strip()

                drafted_norm = normalize(drafted_player)
                available_norm = normalize(available_name)

                assert (
                    drafted_norm != available_norm
                ), f"Drafted player '{drafted_player}' (normalized: '{drafted_norm}') found in available players as '{available_name}' (normalized: '{available_norm}')"

        # Available players should include only non-drafted players
        # "Amon-Ra St. Brown" should be available, and "Bijan Robinson" should be available
        expected_available = ["Bijan Robinson", "Amon-Ra St. Brown"]
        found_available = []

        for expected in expected_available:
            for available_name in available_names:
                if expected.lower().replace("-", "").replace(
                    ".", ""
                ) in available_name.lower().replace("-", "").replace(".", ""):
                    found_available.append(expected)
                    break

        assert (
            len(found_available) == 2
        ), f"Expected to find available players {expected_available}, but found {found_available}"

    @pytest.mark.asyncio
    async def test_exact_normalization_bug_scenario(self):
        """Test the exact scenario that was causing the bug."""

        # This is the exact scenario: drafted player without team, rankings with team
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Jahmyr Gibbs (DET)",  # Rankings include team
                        "position": "RB",
                        "team": "DET",
                        "rank": 1,
                        "score": 95,
                        "bye_week": 8,
                    }
                ]
            },
        }

        draft_state = {
            "picks": [
                {
                    "pick_number": 1,
                    "player": "Jahmyr Gibbs",
                    "position": "RB",
                    "team": "Team A",
                },  # Drafted without team
            ],
            "teams": [{"team_name": "Team A", "owner": "Owner A"}],
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state,
                position_filter="RB",
                limit=5,
                force_refresh=False,
            )

        # The bug was that Jahmyr Gibbs would appear in available players
        # With the fix, he should NOT appear
        assert result["success"] is True
        available_players = result["players"]

        # No players should be available since the only player in rankings is drafted
        assert (
            len(available_players) == 0
        ), f"Expected 0 available players, but found {len(available_players)}: {[p['name'] for p in available_players]}"
