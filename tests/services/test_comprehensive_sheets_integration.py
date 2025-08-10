"""Comprehensive integration tests using real Google Sheets data format."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.player_simple import Player
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

    @pytest.fixture(autouse=True)
    def mock_config_for_dan_format(self):
        """Mock configuration to use Dan format for tests."""
        mock_config = {
            "draft": {
                "formats": {
                    "dan": {"sheet_name": "Draft", "sheet_range": "Draft!A1:V24"}
                }
            }
        }

        with (
            patch("src.config.DRAFT_FORMAT", "dan"),
            patch("src.config._config", mock_config),
            patch("src.services.draft_state_cache.DRAFT_FORMAT", "dan"),
            patch("src.services.draft_state_cache._config", mock_config),
            patch("src.services.sheets_service.DRAFT_FORMAT", "dan"),
        ):
            yield

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

        # SheetsService now returns DraftState object directly
        assert isinstance(processed_data, DraftState)
        assert len(processed_data.teams) == 10  # Should detect 10 teams from fixture
        assert len(processed_data.picks) > 0  # Should have draft picks

        # No adapter needed anymore - processed_data is already a DraftState
        draft_state = processed_data

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
        draft_state = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )

        # SheetsService now returns DraftState directly (no adapter needed)
        assert isinstance(draft_state, DraftState)

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
            first_buffy_pick.player.team == "KC"
        ), f"Expected KC team, got '{first_buffy_pick.player.team}'"
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
        assert (
            first_willow_pick.player.team == "BAL"
        ), f"Expected BAL team, got '{first_willow_pick.player.team}'"

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
            assert (
                first_xander_pick.player.team == "KC"
            ), f"Expected KC team, got '{first_xander_pick.player.team}'"

    @pytest.mark.asyncio
    async def test_end_to_end_csv_to_final_players(self, csv_provider):
        """CRITICAL TEST: Verify specific players flow from CSV fixture to final draft state.

        This test ensures adapter field mapping is correct and would catch bugs like
        player_name vs player field mismatches that cause 'Unknown Player' defaults.
        """
        sheets_service = SheetsService(csv_provider)
        draft_state = await sheets_service.read_draft_data(
            "fixture_sheet_id", "Draft!A1:V24", force_refresh=True
        )

        # SheetsService now returns DraftState directly (no adapter needed)
        assert isinstance(draft_state, DraftState)

        # Test data from CSV fixture:
        # Round 1: Buffy picks Isiah Pacheco KC (RB), Willow picks Derrick Henry BAL (RB), etc.

        expected_first_round = [
            ("Buffy", "Isiah Pacheco", "RB", "KC"),  # Pick 1
            ("Willow", "Derrick Henry", "RB", "BAL"),  # Pick 2
            ("Xander", "Patrick Mahomes", "QB", "KC"),  # Pick 3
            ("Giles", "Amon-Ra St. Brown", "WR", "DET"),  # Pick 4
            ("Anya", "Tyreek Hill", "WR", "MIA"),  # Pick 5
        ]

        # Get all picks sorted by the order they appear in the draft_state
        all_picks = list(draft_state.picks)

        for i, (
            expected_owner,
            expected_player_partial,
            expected_position,
            expected_team,
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
                actual_pick.player.team == expected_team
            ), f"Pick {i+1}: Expected team '{expected_team}', got '{actual_pick.player.team}'"
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

        # SheetsService now returns DraftState object directly
        assert isinstance(processed_data, DraftState)
        assert len(processed_data.teams) > 0  # Should have teams data

        # Check teams structure
        teams = processed_data.teams
        assert len(teams) == 10

        # Each team should have proper structure
        for team in teams:
            assert "team_name" in team
            assert "owner" in team
            assert team["team_name"] != ""
            assert team["owner"] != ""

        # Check picks structure
        picks = processed_data.picks
        assert len(picks) > 0

        # Each pick should have proper DraftPick structure
        for i, pick in enumerate(picks[:5]):  # Check first 5 picks
            assert isinstance(pick, DraftPick), f"Pick {i+1} should be DraftPick object"
            assert hasattr(pick, "player"), f"Pick {i+1} missing player field"
            assert hasattr(pick, "owner"), f"Pick {i+1} missing owner field"
            assert isinstance(
                pick.player, Player
            ), f"Pick {i+1} player should be Player object"

            # Verify the player contains actual data, not defaults
            assert (
                pick.player.name != "Unknown Player"
            ), f"Pick {i+1} has default player name"
            assert pick.player.name.strip(), f"Pick {i+1} has empty player name"
            assert pick.owner.strip(), f"Pick {i+1} has empty owner name"

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

            # The service should still return a DraftState, even if data is minimal
            assert isinstance(processed_data, DraftState)
            # Should have minimal empty data for malformed input
            assert isinstance(processed_data.teams, list)
            assert isinstance(processed_data.picks, list)

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
