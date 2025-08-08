"""Integration tests for sheets service + adapter workflow."""

import pytest

from src.models.draft_state_simple import DraftState
from src.models.player_simple import Player
from src.services.sheets_adapter import SheetsAdapter
from tests.test_helpers import MockSheetsProvider


class TestSheetsIntegration:
    def test_mock_sheets_to_draft_state_workflow(self):
        """Test complete workflow from MockSheetsProvider to DraftState."""
        # Create mock provider with draft data
        provider = MockSheetsProvider()

        # Override mock data with more realistic draft data
        provider.mock_data["test_sheet_123"]["Draft!A1:V24"] = [
            ["Pick", "Team", "Player", "Position", "Owner"],  # Header
            ["1", "Sunnydale Slayers", "Christian McCaffrey", "RB", "Buffy"],
            ["2", "Willow's Warriors", "Tyreek Hill", "WR", "Willow"],
            ["3", "Xander's Crew", "Justin Jefferson", "WR", "Xander"],
        ]

        # Simulate the format that would be returned by read_draft_progress
        mock_sheets_data = {
            "success": True,
            "teams": [
                {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
                {"team_name": "Willow's Warriors", "owner": "Willow", "team_number": 2},
                {"team_name": "Xander's Crew", "owner": "Xander", "team_number": 3},
            ],
            "picks": [
                {
                    "pick": 1,
                    "round": 1,
                    "player": "Christian McCaffrey",
                    "position": "RB",
                    "column_team": "Sunnydale Slayers",
                },
                {
                    "pick": 2,
                    "round": 1,
                    "player": "Tyreek Hill",
                    "position": "WR",
                    "column_team": "Willow's Warriors",
                },
                {
                    "pick": 3,
                    "round": 1,
                    "player": "Justin Jefferson",
                    "position": "WR",
                    "column_team": "Xander's Crew",
                },
            ],
        }

        # Convert using adapter
        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(mock_sheets_data)

        # Verify complete conversion
        assert isinstance(draft_state, DraftState)
        assert len(draft_state.teams) == 3
        assert len(draft_state.picks) == 3

        # Verify teams
        buffy_team = next(t for t in draft_state.teams if t["owner"] == "Buffy")
        assert buffy_team["team_name"] == "Sunnydale Slayers"

        # Verify picks and players
        christian_pick = draft_state.picks[0]
        assert christian_pick.owner == "Buffy"
        assert isinstance(christian_pick.player, Player)
        assert christian_pick.player.name == "Christian McCaffrey"
        assert christian_pick.player.position == "RB"

        tyreek_pick = draft_state.picks[1]
        assert tyreek_pick.owner == "Willow"
        assert tyreek_pick.player.name == "Tyreek Hill"
        assert tyreek_pick.player.position == "WR"

    @pytest.mark.asyncio
    async def test_sheets_provider_to_adapter_integration(self):
        """Test integration between sheets provider and adapter."""
        provider = MockSheetsProvider()

        # Read raw data from provider
        raw_data = await provider.read_range("test_sheet_123", "Draft!A1:V24")

        assert len(raw_data) > 0
        assert raw_data[0] == ["Pick", "Team", "Player", "Position"]  # Header row

        # This shows the data format that would need to be processed
        # by the sheets service before being passed to the adapter
        assert raw_data[1] == ["1", "Team Alpha", "Christian McCaffrey", "RB"]

    def test_adapter_handles_real_sheets_format(self):
        """Test adapter with data format that matches real Google Sheets output."""
        # This simulates the actual format returned by read_draft_progress
        real_format_data = {
            "success": True,
            "sheet_id": "1BvF-4Q_example_sheet_id",
            "current_pick": 4,
            "current_round": 1,
            "total_picks": 3,
            "teams": [
                {"team_name": "The Chosen Ones", "owner": "Buffy", "team_number": 1},
                {"team_name": "Wiccan Warriors", "owner": "Willow", "team_number": 2},
            ],
            "picks": [
                {
                    "pick": 1,
                    "round": 1,
                    "player": "Josh Allen",
                    "position": "QB",
                    "column_team": "The Chosen Ones",
                },
                {
                    "pick": 2,
                    "round": 1,
                    "player": "Christian McCaffrey",
                    "position": "RB",
                    "column_team": "Wiccan Warriors",
                },
                {
                    "pick": 3,
                    "round": 1,
                    "player": "Tyreek Hill",
                    "position": "WR",
                    "column_team": "The Chosen Ones",
                },
            ],
            "draft_state": {
                "picks": [],  # This gets populated but we don't need it
                "teams": [],
                "current_pick": 4,
                "current_team": "Wiccan Warriors",
            },
        }

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(real_format_data)

        # Should work with full real format
        assert isinstance(draft_state, DraftState)
        assert len(draft_state.picks) == 3
        assert len(draft_state.teams) == 2

        # Check specific mappings
        josh_pick = next(p for p in draft_state.picks if p.player.name == "Josh Allen")
        assert josh_pick.owner == "Buffy"

        cmc_pick = next(
            p for p in draft_state.picks if p.player.name == "Christian McCaffrey"
        )
        assert cmc_pick.owner == "Willow"

    def test_error_propagation_through_workflow(self):
        """Test that errors propagate correctly through the workflow."""
        # Test with failed sheets data
        failed_sheets_data = {
            "success": False,
            "error": "Sheet not found",
            "error_type": "sheet_not_found",
        }

        adapter = SheetsAdapter()

        # Should raise ValueError for failed sheets data
        with pytest.raises(ValueError) as exc_info:
            adapter.convert_to_draft_state(failed_sheets_data)

        assert "Sheet not found" in str(exc_info.value)
