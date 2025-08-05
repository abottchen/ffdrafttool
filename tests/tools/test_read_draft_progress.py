from unittest.mock import AsyncMock, patch

import pytest

from src.tools import read_draft_progress


class TestReadDraftProgress:
    @pytest.mark.asyncio
    async def test_read_draft_progress_with_google_sheets_provider(self, draft_progress_data):
        """Test read_draft_progress with real Google Sheets provider (mocked)"""

        # Mock the Google Sheets provider to return test data
        mock_provider = AsyncMock()
        mock_service = AsyncMock()

        # Use fixture data instead of manual construction
        mock_service.read_draft_data.return_value = draft_progress_data

        with patch(
            "src.tools.draft_progress.GoogleSheetsProvider", return_value=mock_provider
        ):
            with patch(
                "src.tools.draft_progress.SheetsService", return_value=mock_service
            ):

                result = await read_draft_progress("real_sheet_123", "Draft!A1:D100")

                assert result["success"] is True

                # Verify the new structure - data is at top level and in draft_state
                assert "teams" in result
                assert "picks" in result
                assert "draft_state" in result
                assert "current_pick" in result

                draft_state = result["draft_state"]
                assert "teams" in draft_state
                assert "current_team" in draft_state
                assert len(result["picks"]) == 2

                # Verify pick structure includes new fields (simplified format)
                first_pick = result["picks"][0]
                assert "pick" in first_pick  # Changed from pick_number
                assert "round" in first_pick
                assert "player" in first_pick  # Changed from player_name
                assert "position" in first_pick

                # Verify the service was called correctly with force_refresh parameter
                mock_service.read_draft_data.assert_called_once_with(
                    "real_sheet_123", "Draft!A1:D100", False
                )
