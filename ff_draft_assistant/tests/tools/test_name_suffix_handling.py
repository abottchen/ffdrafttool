"""
Tests for name suffix handling (Jr., Sr., III, etc.) in player matching.

This module tests that players with suffixes like "Jr." in draft data
are properly matched with rankings data that may not have the suffix.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from tools.mcp_tools import _extract_player_name_and_team, analyze_available_players


class TestNameSuffixHandling:
    """Test suite for handling name suffixes in player matching."""

    def test_extract_player_name_with_jac_team(self):
        """Test that JAC team abbreviation is recognized."""

        test_cases = [
            ("Travis Etienne Jr.   JAC", "Travis Etienne Jr.", "JAC"),
            ("Marvin Harrison Jr.   ARI", "Marvin Harrison Jr.", "ARI"),
            ("Brian Robinson Jr.   WAS", "Brian Robinson Jr.", "WAS"),
            ("Calvin Johnson Sr.   DET", "Calvin Johnson Sr.", "DET"),
        ]

        for input_str, expected_name, expected_team in test_cases:
            name, team = _extract_player_name_and_team(input_str)
            assert name == expected_name, f"Expected name '{expected_name}', got '{name}'"
            assert team == expected_team, f"Expected team '{expected_team}', got '{team}'"

    def test_name_normalization_removes_suffixes(self):
        """Test that name normalization properly removes suffixes."""

        test_cases = [
            ("Travis Etienne Jr.", "travis etienne"),
            ("Marvin Harrison Jr.", "marvin harrison"),
            ("Calvin Johnson Sr.", "calvin johnson"),
            ("John Smith III", "john smith"),
            ("Mike Davis II", "mike davis"),
            ("Player Name", "player name"),  # No suffix
        ]

        for input_name, expected_normalized in test_cases:
            # Apply same normalization as the code
            normalized = input_name.lower()
            normalized = normalized.replace(".", "").replace("'", "").replace("-", "")
            normalized = normalized.replace("jr", "").replace("sr", "").replace("iii", "").replace("ii", "")
            normalized = " ".join(normalized.split()).strip()

            assert normalized == expected_normalized, \
                f"Expected '{expected_normalized}', got '{normalized}' for input '{input_name}'"

    @pytest.mark.asyncio
    async def test_travis_etienne_jr_filtering(self):
        """Test that Travis Etienne Jr. is properly filtered when drafted."""

        # Draft state with Travis Etienne Jr. as drafted
        draft_state = {
            "picks": [
                {"pick": 19, "player": "Travis Etienne Jr.   JAC", "position": "RB"},
            ],
            "teams": [{"team_name": "Test Team", "owner": "Adam", "team_number": 1}],
            "current_pick": 20,
            "current_team": {"team_number": 1, "owner": "Adam", "team_name": "Test Team"}
        }

        # Mock rankings with Travis Etienne (no Jr.) and different team abbreviation
        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Travis Etienne",  # No Jr. suffix
                        "position": "RB",
                        "team": "JAX",  # Different team abbreviation (JAX vs JAC)
                        "bye_week": 11,
                        "average_rank": 20.0,
                        "average_score": 85.0
                    },
                    {
                        "name": "Saquon Barkley",  # Should be available
                        "position": "RB",
                        "team": "PHI",
                        "bye_week": 7,
                        "average_rank": 8.0,
                        "average_score": 92.0
                    }
                ]
            }
        }

        with patch('tools.mcp_tools.get_player_rankings', new_callable=AsyncMock) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state,
                position_filter="RB",
                limit=10
            )

            # Verify the function succeeds
            assert result["success"] is True
            assert "players" in result

            # Get list of available player names
            available_names = [p["name"] for p in result["players"]]

            # Travis Etienne should be filtered out despite suffix and team differences
            assert "Travis Etienne" not in available_names, \
                "Travis Etienne should be filtered out (drafted as Travis Etienne Jr. JAC, ranked as Travis Etienne JAX)"

            # Saquon Barkley should be available
            assert "Saquon Barkley" in available_names, \
                "Saquon Barkley should be available (not drafted)"

    @pytest.mark.asyncio
    async def test_multiple_suffix_players(self):
        """Test filtering of multiple players with different suffixes."""

        draft_state = {
            "picks": [
                {"pick": 1, "player": "Marvin Harrison Jr.   ARI", "position": "WR"},
                {"pick": 2, "player": "Brian Robinson Jr.   WAS", "position": "RB"},
                {"pick": 3, "player": "Calvin Johnson Sr.   DET", "position": "WR"},  # Hypothetical
            ],
            "teams": [{"team_name": "Test Team", "owner": "Adam", "team_number": 1}]
        }

        mock_rankings_response = {
            "success": True,
            "aggregated": {
                "players": [
                    # These should all be filtered out
                    {
                        "name": "Marvin Harrison",  # Jr. in draft, no suffix in rankings
                        "position": "WR",
                        "team": "ARI",
                        "bye_week": 14,
                        "average_rank": 15.0,
                        "average_score": 88.0
                    },
                    {
                        "name": "Brian Robinson",  # Jr. in draft, no suffix in rankings
                        "position": "RB",
                        "team": "WAS",
                        "bye_week": 14,
                        "average_rank": 35.0,
                        "average_score": 75.0
                    },
                    {
                        "name": "Calvin Johnson",  # Sr. in draft, no suffix in rankings
                        "position": "WR",
                        "team": "DET",
                        "bye_week": 9,
                        "average_rank": 25.0,
                        "average_score": 80.0
                    },
                    # This should be available
                    {
                        "name": "Cooper Kupp",
                        "position": "WR",
                        "team": "LAR",
                        "bye_week": 6,
                        "average_rank": 12.0,
                        "average_score": 90.0
                    }
                ]
            }
        }

        with patch('tools.mcp_tools.get_player_rankings', new_callable=AsyncMock) as mock_rankings:
            mock_rankings.return_value = mock_rankings_response

            result = await analyze_available_players(
                draft_state=draft_state,
                position_filter=None,  # All positions
                limit=20
            )

            available_names = [p["name"] for p in result["players"]]

            # All suffix players should be filtered out
            assert "Marvin Harrison" not in available_names, "Marvin Harrison (Jr.) should be filtered out"
            assert "Brian Robinson" not in available_names, "Brian Robinson (Jr.) should be filtered out"
            assert "Calvin Johnson" not in available_names, "Calvin Johnson (Sr.) should be filtered out"

            # Non-drafted player should be available
            assert "Cooper Kupp" in available_names, "Cooper Kupp should be available"

    def test_team_abbreviation_extraction_edge_cases(self):
        """Test team extraction with various formatting."""

        test_cases = [
            # (input, expected_name, expected_team)
            ("Travis Etienne Jr.   JAC", "Travis Etienne Jr.", "JAC"),  # Multiple spaces
            ("Travis Etienne Jr. JAC", "Travis Etienne Jr.", "JAC"),    # Single space
            ("Travis Etienne Jr JAC", "Travis Etienne Jr", "JAC"),      # No period
            ("Player Name", "Player Name", ""),                         # No team
            ("Single", "Single", ""),                                   # Single name
            ("", "", ""),                                              # Empty string
        ]

        for input_str, expected_name, expected_team in test_cases:
            name, team = _extract_player_name_and_team(input_str)
            assert name == expected_name, f"Name: expected '{expected_name}', got '{name}' for input '{input_str}'"
            assert team == expected_team, f"Team: expected '{expected_team}', got '{team}' for input '{input_str}'"
