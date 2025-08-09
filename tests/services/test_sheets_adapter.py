"""Tests for the sheets data adapter."""

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.player_simple import Player
from src.services.sheets_adapter import SheetsAdapter


class TestSheetsAdapter:
    def test_convert_sheets_data_to_draft_state(self):
        """Test converting sheets data format to simplified DraftState."""
        # Create mock data in the format that read_draft_progress returns
        sheets_data = {
            "success": True,
            "teams": [
                {"team_name": "Team Scooby", "owner": "Buffy", "team_number": 1},
                {"team_name": "Team Mystery", "owner": "Willow", "team_number": 2},
                {"team_name": "Team Slayer", "owner": "Xander", "team_number": 3},
            ],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Christian McCaffrey",
                    "position": "RB",
                    "column_team": "Team Scooby",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "player_name": "Tyreek Hill",
                    "position": "WR",
                    "column_team": "Team Mystery",
                },
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        assert isinstance(draft_state, DraftState)
        assert len(draft_state.teams) == 3
        assert len(draft_state.picks) == 2

        # Check teams
        assert draft_state.teams[0]["owner"] == "Buffy"
        assert draft_state.teams[0]["team_name"] == "Team Scooby"
        assert draft_state.teams[1]["owner"] == "Willow"
        assert draft_state.teams[1]["team_name"] == "Team Mystery"

        # Check picks
        first_pick = draft_state.picks[0]
        assert isinstance(first_pick, DraftPick)
        assert first_pick.owner == "Buffy"  # Should map from column_team to owner
        assert isinstance(first_pick.player, Player)
        assert first_pick.player.name == "Christian McCaffrey"
        assert first_pick.player.position == "RB"

        second_pick = draft_state.picks[1]
        assert second_pick.owner == "Willow"
        assert second_pick.player.name == "Tyreek Hill"
        assert second_pick.player.position == "WR"

    def test_convert_empty_sheets_data(self):
        """Test converting empty sheets data."""
        sheets_data = {"success": True, "teams": [], "picks": []}

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        assert isinstance(draft_state, DraftState)
        assert draft_state.teams == []
        assert draft_state.picks == []

    def test_convert_failed_sheets_data(self):
        """Test handling failed sheets data."""
        sheets_data = {"success": False, "error": "Sheet not found"}

        adapter = SheetsAdapter()

        with pytest.raises(ValueError):
            adapter.convert_to_draft_state(sheets_data)

    def test_team_name_to_owner_mapping(self):
        """Test mapping from team name to owner."""
        sheets_data = {
            "success": True,
            "teams": [
                {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
                {"team_name": "Willow's Warriors", "owner": "Willow", "team_number": 2},
            ],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Josh Allen",
                    "position": "QB",
                    "column_team": "Sunnydale Slayers",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "player_name": "Lamar Jackson",
                    "position": "QB",
                    "column_team": "Willow's Warriors",
                },
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        # Should correctly map team names to owners
        assert draft_state.picks[0].owner == "Buffy"
        assert draft_state.picks[1].owner == "Willow"

    def test_player_creation_with_minimal_data(self):
        """Test creating player with minimal sheets data."""
        sheets_data = {
            "success": True,
            "teams": [{"team_name": "Test Team", "owner": "Buffy", "team_number": 1}],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Unknown Player",
                    "position": "RB",
                    "column_team": "Test Team",
                }
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        player = draft_state.picks[0].player
        assert player.name == "Unknown Player"
        assert player.position == "RB"
        # Should have default values for missing data
        assert player.team == "UNK"  # Default for unknown team (no team in name)
        assert player.bye_week == 1  # Default bye week
        assert player.ranking == 999  # Default ranking for unknown
        assert player.projected_points == 0.0  # Default projection

    def test_missing_column_team_handling(self):
        """Test handling picks without column_team mapping."""
        sheets_data = {
            "success": True,
            "teams": [{"team_name": "Test Team", "owner": "Buffy", "team_number": 1}],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Josh Allen",
                    "position": "QB",
                    # Missing column_team
                }
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        # Should handle missing column_team gracefully
        assert len(draft_state.picks) == 1
        # Owner should be "Unknown" or similar default
        assert draft_state.picks[0].owner == "Unknown"

    def test_duplicate_team_names_handling(self):
        """Test handling duplicate team names."""
        sheets_data = {
            "success": True,
            "teams": [
                {"team_name": "Team Alpha", "owner": "Buffy", "team_number": 1},
                {
                    "team_name": "Team Alpha",
                    "owner": "Willow",
                    "team_number": 2,
                },  # Duplicate name
            ],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Josh Allen",
                    "position": "QB",
                    "column_team": "Team Alpha",
                }
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        # Should handle duplicate names (might map to first match)
        assert len(draft_state.picks) == 1
        # Should map to one of the owners (first match is typical)
        assert draft_state.picks[0].owner in ["Buffy", "Willow"]

    def test_extract_player_info(self):
        """Test player name and team extraction from composite names."""
        adapter = SheetsAdapter()

        # Test team abbreviation extraction
        name, team = adapter._extract_player_info("Josh Allen   BUF")
        assert name == "Josh Allen"
        assert team == "BUF"

        name, team = adapter._extract_player_info("Lamar Jackson   BAL")
        assert name == "Lamar Jackson"
        assert team == "BAL"

        name, team = adapter._extract_player_info("Patrick Mahomes II   KC")
        assert name == "Patrick Mahomes II"
        assert team == "KC"

        name, team = adapter._extract_player_info("Amon-Ra St. Brown   DET")
        assert name == "Amon-Ra St. Brown"
        assert team == "DET"

        # Test names without team abbreviations
        name, team = adapter._extract_player_info("Josh Allen")
        assert name == "Josh Allen"
        assert team == "UNK"

        name, team = adapter._extract_player_info("Christian McCaffrey")
        assert name == "Christian McCaffrey"
        assert team == "UNK"

        # Test hyphen separators (new format)
        name, team = adapter._extract_player_info("Kendrick Bourne - NE")
        assert name == "Kendrick Bourne"
        assert team == "NE"

        name, team = adapter._extract_player_info("Ka'imi Fairbairn - HOU")
        assert name == "Ka'imi Fairbairn"
        assert team == "HOU"

        name, team = adapter._extract_player_info("Romeo Doubs - GB")
        assert name == "Romeo Doubs"
        assert team == "GB"

        # Test variations of hyphen format
        name, team = adapter._extract_player_info("Player Name  -  LAR")
        assert name == "Player Name"
        assert team == "LAR"

        name, team = adapter._extract_player_info("Player Name-SF")
        assert name == "Player Name"
        assert team == "SF"

        # Test edge cases
        name, team = adapter._extract_player_info("  Player   Name   SF  ")
        assert name == "Player   Name"
        assert team == "SF"

        name, team = adapter._extract_player_info("Name")
        assert name == "Name"
        assert team == "UNK"

    def test_extract_player_info_logging(self, caplog):
        """Test that team extraction failures are logged as errors."""
        import logging

        adapter = SheetsAdapter()

        # Set log level to capture error logs
        with caplog.at_level(logging.ERROR):
            name, team = adapter._extract_player_info("Player Name Without Team")

            # Should return UNK team
            assert name == "Player Name Without Team"
            assert team == "UNK"

            # Should log an error
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "ERROR"
            assert "Unable to extract NFL team" in caplog.records[0].message
            assert "Player Name Without Team" in caplog.records[0].message
            assert "UNK" in caplog.records[0].message

    def test_convert_with_composite_player_names(self):
        """Test that composite player names are cleaned during conversion."""
        sheets_data = {
            "success": True,
            "teams": [
                {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
                {"team_name": "Willow's Witches", "owner": "Willow", "team_number": 2},
            ],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Josh Allen   BUF",  # Composite name with team
                    "position": "QB",
                    "column_team": "Sunnydale Slayers",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "player_name": "Lamar Jackson   BAL",  # Another composite name
                    "position": "QB",
                    "column_team": "Willow's Witches",
                },
            ],
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(sheets_data)

        # Verify player names were cleaned and teams were extracted
        assert draft_state.picks[0].player.name == "Josh Allen"  # Name cleaned
        assert draft_state.picks[0].player.team == "BUF"  # Team extracted
        assert draft_state.picks[1].player.name == "Lamar Jackson"  # Name cleaned
        assert draft_state.picks[1].player.team == "BAL"  # Team extracted

        # Verify other data is preserved
        assert draft_state.picks[0].player.position == "QB"
        assert draft_state.picks[0].owner == "Buffy"
        assert draft_state.picks[1].player.position == "QB"
        assert draft_state.picks[1].owner == "Willow"
