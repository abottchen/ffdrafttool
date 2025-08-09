"""Tests for team abbreviation mapping functionality."""

from src.services.team_mapping import (
    get_all_valid_sheet_teams,
    is_valid_team_abbreviation,
    normalize_team_abbreviation,
)


class TestTeamMapping:
    """Test team abbreviation mapping functionality."""

    def test_rankings_to_sheets_mapping(self):
        """Test mapping from rankings format to sheets format."""
        # Test teams that need mapping
        assert normalize_team_abbreviation("SFO", "rankings") == "SF"
        assert normalize_team_abbreviation("NOS", "rankings") == "NO"
        assert normalize_team_abbreviation("GBP", "rankings") == "GB"
        assert normalize_team_abbreviation("KCC", "rankings") == "KC"
        assert normalize_team_abbreviation("NEP", "rankings") == "NE"
        assert normalize_team_abbreviation("TBB", "rankings") == "TB"
        assert normalize_team_abbreviation("LVR", "rankings") == "LV"

    def test_teams_that_dont_need_mapping(self):
        """Test teams that are the same in both formats."""
        # Teams that are the same in both formats (no mapping needed)
        teams = ["BUF", "BAL", "MIA", "NYJ", "ATL", "CAR", "DET", "HOU"]
        for team in teams:
            assert normalize_team_abbreviation(team, "rankings") == team

    def test_invalid_teams_filtered_out(self):
        """Test that invalid team abbreviations are filtered out."""
        # Teams that should be filtered to UNK (if they appear)
        assert normalize_team_abbreviation("FA", "rankings") == "UNK"

    def test_edge_cases(self):
        """Test edge cases for team normalization."""
        # Empty or None input
        assert normalize_team_abbreviation("", "rankings") == "UNK"
        assert normalize_team_abbreviation("UNK", "rankings") == "UNK"

        # Case insensitive
        assert normalize_team_abbreviation("sfo", "rankings") == "SF"
        assert normalize_team_abbreviation("GbP", "rankings") == "GB"

        # Whitespace handling
        assert normalize_team_abbreviation("  SFO  ", "rankings") == "SF"

    def test_sheets_source_passthrough(self):
        """Test that sheets source data passes through unchanged."""
        # When source is sheets, should pass through unchanged
        assert normalize_team_abbreviation("SF", "sheets") == "SF"
        assert (
            normalize_team_abbreviation("SFO", "sheets") == "SFO"
        )  # No mapping applied
        assert normalize_team_abbreviation("GB", "sheets") == "GB"

    def test_unknown_source_passthrough(self):
        """Test that unknown source passes through unchanged."""
        assert normalize_team_abbreviation("SF", "unknown") == "SF"
        assert normalize_team_abbreviation("SFO", "unknown") == "SFO"

    def test_get_all_valid_sheet_teams(self):
        """Test getting all valid team abbreviations."""
        valid_teams = get_all_valid_sheet_teams()

        # Should include standard teams
        assert "SF" in valid_teams
        assert "GB" in valid_teams
        assert "KC" in valid_teams
        assert "BUF" in valid_teams

        # Should not include invalid teams
        assert "FA" not in valid_teams

        # Should be reasonable number of teams (32 NFL teams)
        assert 30 <= len(valid_teams) <= 35

    def test_is_valid_team_abbreviation(self):
        """Test team abbreviation validation."""
        # Valid teams
        assert is_valid_team_abbreviation("SF") is True
        assert is_valid_team_abbreviation("GB") is True
        assert is_valid_team_abbreviation("KC") is True
        assert is_valid_team_abbreviation("BUF") is True

        # Invalid teams
        assert is_valid_team_abbreviation("FA") is False
        assert is_valid_team_abbreviation("UNK") is False
        assert is_valid_team_abbreviation("") is False

        # Case insensitive
        assert is_valid_team_abbreviation("sf") is True
        assert is_valid_team_abbreviation("Gb") is True

    def test_comprehensive_team_list(self):
        """Test that we have mappings for all major NFL teams."""
        valid_teams = get_all_valid_sheet_teams()

        # Check that we have all 32 NFL teams represented
        expected_teams = {
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
            "JAC",
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
            "SF",
            "SEA",
            "TB",
            "TEN",
            "WAS",
        }

        # All expected teams should be in valid teams
        for team in expected_teams:
            assert team in valid_teams, f"Team {team} not found in valid teams"
