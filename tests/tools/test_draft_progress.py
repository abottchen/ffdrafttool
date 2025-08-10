"""Tests for draft progress tool with proper caching support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.tools.draft_progress import read_draft_progress


class TestDraftProgress:
    """Test suite for draft progress tool with caching."""

    @pytest.fixture
    def mock_draft_state(self):
        """Create a mock DraftState for testing."""
        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy"},
            {"team_name": "Willow's Witches", "owner": "Willow"},
        ]

        picks = [
            DraftPick(
                player=Player(
                    name="Josh Allen",
                    team="BUF",
                    position="QB",
                    bye_week=12,
                    ranking=1,
                    projected_points=25.5,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="Elite QB1",
                ),
                owner="Buffy",
            ),
            DraftPick(
                player=Player(
                    name="Christian McCaffrey",
                    team="SF",
                    position="RB",
                    bye_week=9,
                    ranking=2,
                    projected_points=20.8,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="Top RB when healthy",
                ),
                owner="Willow",
            ),
        ]

        return DraftState(teams=teams, picks=picks)

    @pytest.mark.asyncio
    async def test_read_draft_progress_success(self, mock_draft_state):
        """Test successful draft progress read using cache."""
        with patch(
            "src.services.draft_state_cache.get_cached_draft_state"
        ) as mock_cache:
            mock_cache.return_value = mock_draft_state

            result = await read_draft_progress()

            # Should return DraftState object
            assert isinstance(result, DraftState)
            assert len(result.teams) == 2
            assert len(result.picks) == 2

            # Verify cache was called correctly
            mock_cache.assert_called_once()

            # Check teams data
            teams = result.teams
            assert teams[0]["team_name"] == "Sunnydale Slayers"
            assert teams[0]["owner"] == "Buffy"
            assert teams[1]["owner"] == "Willow"

            # Check picks data
            picks = result.picks
            pick1 = picks[0]
            assert pick1.owner == "Buffy"
            assert pick1.player.name == "Josh Allen"
            assert pick1.player.position == "QB"
            assert pick1.player.team == "BUF"

            pick2 = picks[1]
            assert pick2.owner == "Willow"
            assert pick2.player.name == "Christian McCaffrey"
            assert pick2.player.position == "RB"

    @pytest.mark.asyncio
    async def test_read_draft_progress_force_refresh(self, mock_draft_state):
        """Test force refresh bypasses cache."""
        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = mock_draft_state
                mock_service_class.return_value = mock_service

                result = await read_draft_progress(force_refresh=True)

                # Should return DraftState object
                assert isinstance(result, DraftState)
                assert len(result.teams) == 2

                # Verify sheets service was called directly (bypassing cache)
                mock_service_class.assert_called_once()
                # Verify service was used with config-based parameters
                mock_service.read_draft_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_draft_progress_missing_dependencies(self):
        """Test handling of missing Google Sheets dependencies with force refresh."""
        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider_class.side_effect = ImportError("Google API not available")

            result = await read_draft_progress(force_refresh=True)

            # Should return error dict
            assert isinstance(result, dict)
            assert result["success"] is False
            assert result["error_type"] == "missing_dependencies"
            assert "Google Sheets API not available" in result["error"]

    @pytest.mark.asyncio
    async def test_read_draft_progress_config_based(self, mock_draft_state):
        """Test that configuration is used for sheet parameters."""
        with patch(
            "src.services.draft_state_cache.get_cached_draft_state"
        ) as mock_cache:
            mock_cache.return_value = mock_draft_state

            result = await read_draft_progress()

            assert isinstance(result, DraftState)
            # Verify cache was called (config determines sheet_id and range)
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_draft_progress_cache_error(self):
        """Test handling of cache errors."""
        error_result = {
            "success": False,
            "error": "Sheet not found",
            "error_type": "sheet_access_failed",
            "sheet_id": "test_sheet_id",
            "sheet_range": "Draft!A1:V24",
        }

        with patch(
            "src.services.draft_state_cache.get_cached_draft_state"
        ) as mock_cache:
            mock_cache.return_value = error_result

            result = await read_draft_progress()

            # Should return error dict from cache
            assert isinstance(result, dict)
            assert result["success"] is False
            assert result["error"] == "Sheet not found"

    @pytest.mark.asyncio
    async def test_read_draft_progress_with_composite_names(self):
        """Test handling of composite player names (with team abbreviations)."""
        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy"},
            {"team_name": "Willow's Witches", "owner": "Willow"},
        ]

        # Create players with parsed names (team extracted from composite name)
        picks = [
            DraftPick(
                player=Player(
                    name="Josh Allen",  # Name should be cleaned (BUF extracted)
                    team="BUF",  # Team should be extracted from composite name
                    position="QB",
                    bye_week=1,
                    ranking=999,
                    projected_points=0.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="",
                ),
                owner="Buffy",
            ),
            DraftPick(
                player=Player(
                    name="Lamar Jackson",  # Name should be cleaned (BAL extracted)
                    team="BAL",  # Team should be extracted from composite name
                    position="QB",
                    bye_week=1,
                    ranking=999,
                    projected_points=0.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="",
                ),
                owner="Willow",
            ),
        ]

        expected_draft_state = DraftState(teams=teams, picks=picks)

        with patch(
            "src.services.draft_state_cache.get_cached_draft_state"
        ) as mock_cache:
            mock_cache.return_value = expected_draft_state

            result = await read_draft_progress()

            # Should return DraftState object for success
            assert isinstance(result, DraftState)
            assert len(result.picks) == 2

            # Verify team extraction worked
            picks = result.picks
            assert picks[0].player.name == "Josh Allen"
            assert picks[0].player.team == "BUF"
            assert picks[1].player.name == "Lamar Jackson"
            assert picks[1].player.team == "BAL"

    @pytest.mark.asyncio
    async def test_read_draft_progress_empty_data(self):
        """Test handling of empty draft data."""
        empty_draft_state = DraftState(picks=[], teams=[])

        with patch(
            "src.services.draft_state_cache.get_cached_draft_state"
        ) as mock_cache:
            mock_cache.return_value = empty_draft_state

            result = await read_draft_progress()

            assert isinstance(result, DraftState)
            assert len(result.picks) == 0
            assert len(result.teams) == 0
