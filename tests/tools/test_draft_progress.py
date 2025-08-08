"""Tests for draft progress tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.tools.draft_progress import read_draft_progress


class TestDraftProgress:
    """Test draft progress functionality."""

    @pytest.fixture
    def mock_processed_data(self):
        """Mock processed data from sheets service."""
        return {
            "teams": [
                {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
                {"team_name": "Willow's Witches", "owner": "Willow", "team_number": 2},
            ],
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "column_team": 1,
                    "player": "Josh Allen",
                    "position": "QB",
                    "team": "BUF",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "column_team": 2,
                    "player": "Christian McCaffrey",
                    "position": "RB",
                    "team": "SF",
                },
            ],
        }

    @pytest.fixture
    def mock_draft_state(self):
        """Mock simplified draft state after adapter conversion."""
        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
            {"team_name": "Willow's Witches", "owner": "Willow", "team_number": 2},
        ]

        picks = [
            DraftPick(
                owner="Buffy",
                player=Player(
                    name="Josh Allen",
                    team="BUF",
                    position="QB",
                    bye_week=12,
                    ranking=1,
                    projected_points=99.0,
                    injury_status=InjuryStatus.HEALTHY,
                ),
            ),
            DraftPick(
                owner="Willow",
                player=Player(
                    name="Christian McCaffrey",
                    team="SF",
                    position="RB",
                    bye_week=9,
                    ranking=2,
                    projected_points=98.0,
                    injury_status=InjuryStatus.HEALTHY,
                ),
            ),
        ]

        return DraftState(teams=teams, picks=picks)

    @pytest.mark.asyncio
    async def test_read_draft_progress_success(
        self, mock_processed_data, mock_draft_state
    ):
        """Test successful draft progress read."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = mock_processed_data
                mock_service_class.return_value = mock_service

                with patch(
                    "src.services.sheets_adapter.SheetsAdapter"
                ) as mock_adapter_class:
                    mock_adapter = MagicMock()
                    mock_adapter.convert_to_draft_state.return_value = mock_draft_state
                    mock_adapter_class.return_value = mock_adapter

                    result = await read_draft_progress("test_sheet_id")

                    # Should return success
                    assert result["success"] is True
                    assert result["sheet_id"] == "test_sheet_id"
                    assert result["total_teams"] == 2
                    assert result["total_picks"] == 2

                    # Check teams data
                    teams = result["teams"]
                    assert len(teams) == 2
                    assert teams[0]["team_name"] == "Sunnydale Slayers"
                    assert teams[0]["owner"] == "Buffy"
                    assert teams[1]["owner"] == "Willow"

                    # Check picks data
                    picks = result["picks"]
                    assert len(picks) == 2

                    # Verify first pick
                    pick1 = picks[0]
                    assert pick1["owner"] == "Buffy"
                    assert pick1["player"]["name"] == "Josh Allen"
                    assert pick1["player"]["position"] == "QB"
                    assert pick1["player"]["team"] == "BUF"
                    assert pick1["player"]["injury_status"] == "HEALTHY"

                    # Verify second pick
                    pick2 = picks[1]
                    assert pick2["owner"] == "Willow"
                    assert pick2["player"]["name"] == "Christian McCaffrey"
                    assert pick2["player"]["position"] == "RB"

    @pytest.mark.asyncio
    async def test_read_draft_progress_missing_dependencies(self):
        """Test handling of missing Google Sheets dependencies."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider_class.side_effect = ImportError(
                "google-api-python-client not found"
            )

            result = await read_draft_progress("test_sheet_id")

            assert result["success"] is False
            assert result["error_type"] == "missing_dependencies"
            assert "Google Sheets API not available" in result["error"]
            assert "troubleshooting" in result
            assert "pip install" in result["troubleshooting"]["solution"]

    @pytest.mark.asyncio
    async def test_read_draft_progress_missing_credentials(self):
        """Test handling of missing credentials."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider_class.side_effect = FileNotFoundError(
                "credentials.json not found"
            )

            result = await read_draft_progress("test_sheet_id")

            assert result["success"] is False
            assert result["error_type"] == "missing_credentials"
            assert "credentials not configured" in result["error"]
            assert (
                "console.developers.google.com"
                in result["troubleshooting"]["next_steps"][0]
            )

    @pytest.mark.asyncio
    async def test_read_draft_progress_permission_error(self, mock_processed_data):
        """Test handling of permission errors."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.side_effect = Exception(
                    "403 Forbidden - Permission denied"
                )
                mock_service_class.return_value = mock_service

                result = await read_draft_progress("test_sheet_id")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "403 Forbidden" in result["error"]
                assert "check permissions" in result["troubleshooting"]["solution"]
                assert (
                    "shared with your Google account"
                    in result["troubleshooting"]["next_steps"][0]
                )

    @pytest.mark.asyncio
    async def test_read_draft_progress_not_found_error(self):
        """Test handling of sheet not found errors."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.side_effect = Exception(
                    "404 Not Found - Sheet not found"
                )
                mock_service_class.return_value = mock_service

                result = await read_draft_progress("invalid_sheet_id")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "404 Not Found" in result["error"]
                assert (
                    "check sheet ID and range" in result["troubleshooting"]["solution"]
                )
                assert (
                    "Verify the Google Sheet ID"
                    in result["troubleshooting"]["next_steps"][0]
                )

    @pytest.mark.asyncio
    async def test_read_draft_progress_authentication_error(self):
        """Test handling of authentication errors."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.side_effect = Exception(
                    "Authentication failed - invalid credentials"
                )
                mock_service_class.return_value = mock_service

                result = await read_draft_progress("test_sheet_id")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "Authentication failed" in result["error"]
                assert "refresh credentials" in result["troubleshooting"]["solution"]
                assert "Delete token.json" in result["troubleshooting"]["next_steps"][0]

    @pytest.mark.asyncio
    async def test_read_draft_progress_with_custom_range(
        self, mock_processed_data, mock_draft_state
    ):
        """Test reading draft progress with custom sheet range."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = mock_processed_data
                mock_service_class.return_value = mock_service

                with patch(
                    "src.services.sheets_adapter.SheetsAdapter"
                ) as mock_adapter_class:
                    mock_adapter = MagicMock()
                    mock_adapter.convert_to_draft_state.return_value = mock_draft_state
                    mock_adapter_class.return_value = mock_adapter

                    result = await read_draft_progress(
                        "test_sheet_id", sheet_range="CustomRange!A1:Z30"
                    )

                    assert result["success"] is True
                    assert result["sheet_id"] == "test_sheet_id"

                    # Verify the custom range was passed to the service
                    mock_service.read_draft_data.assert_called_once_with(
                        "test_sheet_id", "CustomRange!A1:Z30", False
                    )

    @pytest.mark.asyncio
    async def test_read_draft_progress_force_refresh(
        self, mock_processed_data, mock_draft_state
    ):
        """Test reading draft progress with force refresh."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = mock_processed_data
                mock_service_class.return_value = mock_service

                with patch(
                    "src.services.sheets_adapter.SheetsAdapter"
                ) as mock_adapter_class:
                    mock_adapter = MagicMock()
                    mock_adapter.convert_to_draft_state.return_value = mock_draft_state
                    mock_adapter_class.return_value = mock_adapter

                    result = await read_draft_progress(
                        "test_sheet_id", force_refresh=True
                    )

                    assert result["success"] is True

                    # Verify force_refresh was passed to the service
                    mock_service.read_draft_data.assert_called_once_with(
                        "test_sheet_id", "Draft!A1:V24", True
                    )

    @pytest.mark.asyncio
    async def test_read_draft_progress_adapter_error(self, mock_processed_data):
        """Test handling of adapter conversion errors."""

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = mock_processed_data
                mock_service_class.return_value = mock_service

                with patch(
                    "src.services.sheets_adapter.SheetsAdapter"
                ) as mock_adapter_class:
                    mock_adapter = MagicMock()
                    mock_adapter.convert_to_draft_state.side_effect = Exception(
                        "Conversion failed"
                    )
                    mock_adapter_class.return_value = mock_adapter

                    result = await read_draft_progress("test_sheet_id")

                    assert result["success"] is False
                    assert result["error_type"] == "sheet_access_failed"
                    assert "Conversion failed" in result["error"]

    @pytest.mark.asyncio
    async def test_read_draft_progress_empty_data(self, mock_draft_state):
        """Test handling of empty draft data."""

        # Create empty data
        empty_processed_data = {"teams": [], "picks": []}
        empty_draft_state = DraftState(teams=[], picks=[])

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = empty_processed_data
                mock_service_class.return_value = mock_service

                with patch(
                    "src.services.sheets_adapter.SheetsAdapter"
                ) as mock_adapter_class:
                    mock_adapter = MagicMock()
                    mock_adapter.convert_to_draft_state.return_value = empty_draft_state
                    mock_adapter_class.return_value = mock_adapter

                    result = await read_draft_progress("test_sheet_id")

                    assert result["success"] is True
                    assert result["total_teams"] == 0
                    assert result["total_picks"] == 0
                    assert len(result["teams"]) == 0
                    assert len(result["picks"]) == 0

    @pytest.mark.asyncio
    async def test_read_draft_progress_with_composite_names(self):
        """Test that composite player names with team abbreviations are properly handled."""
        
        # Mock data with composite names (like what comes from Google Sheets)
        composite_processed_data = {
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

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            with patch("src.tools.draft_progress.SheetsService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.read_draft_data.return_value = composite_processed_data
                mock_service_class.return_value = mock_service

                # Use real adapter (not mocked) to test actual team extraction
                result = await read_draft_progress("test_sheet_id")

                # Should return success
                assert result["success"] is True
                assert result["total_picks"] == 2

                # Check that player names were cleaned and teams were extracted
                picks = result["picks"]
                assert len(picks) == 2

                # Verify first pick - name cleaned, team extracted
                pick1 = picks[0]
                assert pick1["owner"] == "Buffy"
                assert pick1["player"]["name"] == "Josh Allen"  # Team suffix removed
                assert pick1["player"]["team"] == "BUF"  # Team extracted from name
                assert pick1["player"]["position"] == "QB"

                # Verify second pick - name cleaned, team extracted
                pick2 = picks[1]
                assert pick2["owner"] == "Willow"
                assert pick2["player"]["name"] == "Lamar Jackson"  # Team suffix removed
                assert pick2["player"]["team"] == "BAL"  # Team extracted from name
                assert pick2["player"]["position"] == "QB"
