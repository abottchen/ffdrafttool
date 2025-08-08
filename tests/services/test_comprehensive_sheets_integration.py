"""Comprehensive integration tests using real Google Sheets data format."""

from pathlib import Path

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.player_simple import Player
from src.services.sheets_adapter import SheetsAdapter
from src.services.sheets_service import SheetsService
from tests.fixtures.csv_sheets_provider import CSVSheetsProvider


class TestComprehensiveSheetsIntegration:
    @pytest.fixture
    def csv_fixture_path(self):
        """Path to the CSV fixture with real sheet format."""
        return Path(__file__).parent.parent / "fixtures" / "draft_data.csv"

    @pytest.fixture
    def csv_provider(self, csv_fixture_path):
        """CSV provider using real sheet format fixture."""
        return CSVSheetsProvider(str(csv_fixture_path))

    @pytest.mark.asyncio
    async def test_complete_pipeline_csv_to_draft_state(self, csv_provider):
        """Test complete pipeline: CSV fixture → SheetsService → Adapter → DraftState."""

        # Create sheets service with CSV provider (simulates real Google Sheets)
        sheets_service = SheetsService(csv_provider)

        # Process through the actual SheetsService.read_draft_data logic
        # This tests the real sheet parsing code with real data format
        processed_data = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )

        # Verify the sheets service processed the data correctly
        assert "teams" in processed_data
        assert "picks" in processed_data
        assert len(processed_data["teams"]) == 10  # Should detect 10 teams from fixture
        assert len(processed_data["picks"]) > 0  # Should have draft picks

        # The SheetsService doesn't return a 'success' field, but if we got here it worked
        # Add success field for adapter compatibility
        processed_data["success"] = True

        # Convert using sheets adapter
        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(processed_data)

        # Verify complete pipeline worked
        assert isinstance(draft_state, DraftState)
        assert len(draft_state.teams) == 10
        assert len(draft_state.picks) > 0

        # Verify team structure with Buffy character names
        team_owners = {team["owner"] for team in draft_state.teams}
        expected_owners = {
            "Buffy",
            "Willow",
            "Xander",
            "Giles",
            "Anya",
            "Tara",
            "Spike",
            "Dawn",
            "Joyce",
            "Riley",
        }
        assert team_owners == expected_owners

        # Verify team names
        buffy_team = next(t for t in draft_state.teams if t["owner"] == "Buffy")
        assert buffy_team["team_name"] == "Sunnydale Slayers"

        willow_team = next(t for t in draft_state.teams if t["owner"] == "Willow")
        assert willow_team["team_name"] == "Willow's Witches"

    @pytest.mark.asyncio
    async def test_pick_data_accuracy_with_real_format(self, csv_provider):
        """Test that picks are correctly parsed from real sheet format."""

        sheets_service = SheetsService(csv_provider)
        processed_data = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )

        # Add success field for adapter compatibility
        processed_data["success"] = True

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(processed_data)

        # CRITICAL TEST: Verify specific players from CSV fixture make it to final draft state
        # This test would have caught the field name mismatch bug

        # Find Buffy's first pick (Round 1, Pick 1 from CSV fixture)
        round_1_picks = [
            p for p in draft_state.picks if hasattr(p, "round") and p.round == 1
        ]
        if not round_1_picks:  # If picks don't have round info, get by owner order
            buffy_picks = [p for p in draft_state.picks if p.owner == "Buffy"]
            assert len(buffy_picks) > 0, "Should have picks for Buffy"
            first_buffy_pick = buffy_picks[0]
        else:
            # Find pick 1 (should be Buffy's)
            first_pick = min(
                round_1_picks, key=lambda p: getattr(p, "pick_number", 0) or 0
            )
            first_buffy_pick = first_pick

        # VERIFY: Isiah Pacheco made it from CSV to final draft state
        assert (
            "Isiah Pacheco" in first_buffy_pick.player.name
        ), f"Expected 'Isiah Pacheco' in first pick, got '{first_buffy_pick.player.name}'"
        assert (
            first_buffy_pick.player.position == "RB"
        ), f"Expected RB position, got '{first_buffy_pick.player.position}'"
        assert (
            first_buffy_pick.owner == "Buffy"
        ), f"Expected Buffy as owner, got '{first_buffy_pick.owner}'"

        # Find Willow's first pick (Round 1, Pick 2 from CSV fixture)
        willow_picks = [p for p in draft_state.picks if p.owner == "Willow"]
        assert len(willow_picks) > 0, "Should have picks for Willow"
        first_willow_pick = willow_picks[0]

        # VERIFY: Derrick Henry made it from CSV to final draft state
        assert (
            "Derrick Henry" in first_willow_pick.player.name
        ), f"Expected 'Derrick Henry' in Willow's first pick, got '{first_willow_pick.player.name}'"
        assert (
            first_willow_pick.player.position == "RB"
        ), f"Expected RB position, got '{first_willow_pick.player.position}'"

        # VERIFY: More picks to ensure the pattern holds
        xander_picks = [p for p in draft_state.picks if p.owner == "Xander"]
        if xander_picks:
            first_xander_pick = xander_picks[0]
            assert (
                "Patrick Mahomes" in first_xander_pick.player.name
            ), f"Expected 'Patrick Mahomes' in Xander's first pick, got '{first_xander_pick.player.name}'"
            assert (
                first_xander_pick.player.position == "QB"
            ), f"Expected QB position, got '{first_xander_pick.player.position}'"

    @pytest.mark.asyncio
    async def test_end_to_end_csv_to_final_players(self, csv_provider):
        """CRITICAL TEST: Verify specific players flow from CSV fixture to final draft state.

        This test ensures adapter field mapping is correct and would catch bugs like
        player_name vs player field mismatches that cause 'Unknown Player' defaults.
        """
        sheets_service = SheetsService(csv_provider)
        processed_data = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )
        processed_data["success"] = True

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(processed_data)

        # Test data from CSV fixture:
        # Round 1: Buffy picks Isiah Pacheco KC (RB), Willow picks Derrick Henry BAL (RB), etc.

        expected_first_round = [
            ("Buffy", "Isiah Pacheco", "RB"),  # Pick 1
            ("Willow", "Derrick Henry", "RB"),  # Pick 2
            ("Xander", "Patrick Mahomes", "QB"),  # Pick 3
            ("Giles", "Amon-Ra St. Brown", "WR"),  # Pick 4
            ("Anya", "Tyreek Hill", "WR"),  # Pick 5
        ]

        # Get all picks sorted by the order they appear in the draft_state
        all_picks = list(draft_state.picks)

        for i, (
            expected_owner,
            expected_player_partial,
            expected_position,
        ) in enumerate(expected_first_round):
            assert i < len(all_picks), f"Missing pick {i+1} in draft state"

            actual_pick = all_picks[i]

            # CRITICAL ASSERTIONS that would catch field mapping bugs:
            assert (
                expected_player_partial in actual_pick.player.name
            ), f"Pick {i+1}: Expected '{expected_player_partial}' in player name, got '{actual_pick.player.name}'"
            assert (
                actual_pick.player.position == expected_position
            ), f"Pick {i+1}: Expected position '{expected_position}', got '{actual_pick.player.position}'"
            assert (
                actual_pick.owner == expected_owner
            ), f"Pick {i+1}: Expected owner '{expected_owner}', got '{actual_pick.owner}'"

            # Ensure we're not getting default values that indicate field mapping failure
            assert (
                actual_pick.player.name != "Unknown Player"
            ), f"Pick {i+1}: Got default 'Unknown Player' - indicates field mapping bug"
            assert (
                actual_pick.player.team != "UNK"
                or "Unknown" not in actual_pick.player.name
            ), f"Pick {i+1}: Multiple default values suggest field mapping problems"

        # Check that players have reasonable data
        expected_owners = {
            "Buffy",
            "Willow",
            "Xander",
            "Giles",
            "Anya",
            "Tara",
            "Spike",
            "Dawn",
            "Joyce",
            "Riley",
        }

        for pick in draft_state.picks[:5]:  # Check first 5 picks
            assert isinstance(pick, DraftPick)
            assert isinstance(pick.player, Player)
            assert pick.player.name != ""  # Should have actual player name
            assert pick.player.position in [
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
                "DST",
            ]  # Valid position
            assert pick.owner in expected_owners  # Valid owner

    @pytest.mark.asyncio
    async def test_sheets_service_processes_real_format_correctly(self, csv_provider):
        """Test that SheetsService correctly processes the team-column format."""

        sheets_service = SheetsService(csv_provider)

        # This tests the core sheets processing logic
        processed_data = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )

        # SheetsService doesn't return 'success', but if we got data it worked
        assert len(processed_data.get("teams", [])) > 0  # Should have teams data

        # Check teams structure
        teams = processed_data["teams"]
        assert len(teams) == 10

        # Each team should have proper structure
        for team in teams:
            assert "team_name" in team
            assert "owner" in team
            assert "team_number" in team
            assert team["team_name"] != ""
            assert team["owner"] != ""
            assert isinstance(team["team_number"], int)

        # Check picks structure
        picks = processed_data["picks"]
        assert len(picks) > 0

        # Each pick should have proper structure with correct field names
        for i, pick in enumerate(picks[:5]):  # Check first 5 picks
            assert "pick_number" in pick, f"Pick {i+1} missing pick_number field"
            assert "round" in pick, f"Pick {i+1} missing round field"
            assert "player_name" in pick, f"Pick {i+1} missing player_name field"
            assert "position" in pick, f"Pick {i+1} missing position field"
            assert "column_team" in pick, f"Pick {i+1} missing column_team field"

            # Verify the field contains actual data, not defaults
            assert (
                pick["player_name"] != "Unknown Player"
            ), f"Pick {i+1} has default player name"
            assert pick["player_name"].strip(), f"Pick {i+1} has empty player name"

    @pytest.mark.asyncio
    async def test_error_handling_with_malformed_csv(self):
        """Test error handling when CSV fixture is malformed."""

        # Create a temporary malformed CSV
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("invalid,csv,format\n")
            temp_path = f.name

        try:
            csv_provider = CSVSheetsProvider(temp_path)
            sheets_service = SheetsService(csv_provider)

            # This should handle the malformed data gracefully
            processed_data = await sheets_service.read_draft_data(
                "bad_sheet", "Draft!A1:V24", force_refresh=True
            )

            # The service should still return a response, even if data is minimal
            # SheetsService.read_draft_data doesn't return 'success' field, but should return standard structure
            assert "teams" in processed_data
            assert "picks" in processed_data
            # Should have minimal empty data for malformed input
            assert isinstance(processed_data["teams"], list)
            assert isinstance(processed_data["picks"], list)

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    def test_csv_provider_loads_fixture_correctly(self, csv_provider):
        """Test that CSV provider correctly loads the fixture data."""

        # Should be able to create provider without errors
        assert csv_provider is not None
        assert csv_provider.get_row_count() > 4  # Should have header rows + data rows

    @pytest.mark.asyncio
    async def test_csv_provider_returns_expected_format(self, csv_provider):
        """Test CSV provider returns data in expected Google Sheets format."""

        raw_data = await csv_provider.read_range("test_id", "Draft!A1:V24")

        assert isinstance(raw_data, list)
        assert len(raw_data) > 4  # Title, owners, teams, headers, + data

        # Check structure matches expected Google Sheets format
        title_row = raw_data[0]
        assert "Fantasy Draft" in title_row[0]  # Title in first cell

        owners_row = raw_data[1]
        assert "Buffy" in owners_row  # Should contain our test owners
        assert "Willow" in owners_row

        teams_row = raw_data[2]
        assert "Sunnydale Slayers" in teams_row  # Should contain team names

        headers_row = raw_data[3]
        assert "Player" in headers_row  # Should have Player/Pos headers
        assert "Pos" in headers_row
