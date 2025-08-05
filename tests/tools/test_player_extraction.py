#!/usr/bin/env python3
"""
Test the _extract_player_name_and_team function.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from tools.analyze_players import _extract_player_name_and_team


class TestPlayerExtraction:
    """Test player name and team extraction from draft data format."""

    def test_player_with_team(self):
        """Test extracting player with team abbreviation."""
        result = _extract_player_name_and_team("Jahmyr Gibbs DET")
        assert result == ("Jahmyr Gibbs", "DET")

    def test_player_with_three_letter_team(self):
        """Test extracting player with 3-letter team abbreviation."""
        result = _extract_player_name_and_team("Saquon Barkley NYG")
        assert result == ("Saquon Barkley", "NYG")

    def test_player_without_team(self):
        """Test extracting player without team information."""
        result = _extract_player_name_and_team("Player Name")
        assert result == ("Player Name", "")

    def test_player_with_middle_name(self):
        """Test extracting player with middle name and team."""
        result = _extract_player_name_and_team("Calvin Johnson Jr DET")
        assert result == ("Calvin Johnson Jr", "DET")

    def test_empty_string(self):
        """Test handling empty string."""
        result = _extract_player_name_and_team("")
        assert result == ("", "")

    def test_none_input(self):
        """Test handling None input."""
        result = _extract_player_name_and_team(None)
        assert result == ("", "")

    def test_single_word(self):
        """Test handling single word input."""
        result = _extract_player_name_and_team("Cher")
        assert result == ("Cher", "")

    def test_lowercase_team_extracted(self):
        """Test that lowercase team abbreviations are properly extracted."""
        result = _extract_player_name_and_team("Player Name det")
        assert result == ("Player Name", "DET")

    def test_invalid_team_not_extracted(self):
        """Test that invalid team abbreviations are not extracted."""
        result = _extract_player_name_and_team("Player Name FAKE")
        assert result == ("Player Name FAKE", "")

    def test_case_insensitive_team_extraction(self):
        """Test that team extraction is case insensitive."""
        result = _extract_player_name_and_team("Player Name nfL")
        assert result == ("Player Name nfL", "")  # NFL is not a valid team

        result = _extract_player_name_and_team("Player Name gb")
        assert result == ("Player Name", "GB")

    def test_all_nfl_teams_recognized(self):
        """Test that all current NFL team abbreviations are recognized."""
        nfl_teams = [
            "ARI",
            "ATL",
            "BAL",
            "BUF",
            "CAR",
            "CHI",
            "CIN",
            "CLE",
            "DAL",
            "DEN",
            "DET",
            "GB",
            "HOU",
            "IND",
            "JAX",
            "KC",
            "LAC",
            "LAR",
            "LV",
            "MIA",
            "MIN",
            "NE",
            "NO",
            "NYG",
            "NYJ",
            "PHI",
            "PIT",
            "SEA",
            "SF",
            "TB",
            "TEN",
            "WAS",
        ]

        for team in nfl_teams:
            result = _extract_player_name_and_team(f"Test Player {team}")
            assert result == ("Test Player", team), f"Failed for team {team}"
