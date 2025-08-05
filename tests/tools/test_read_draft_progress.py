from unittest.mock import AsyncMock, patch

import pytest

from src.tools import read_draft_progress


class TestReadDraftProgress:
    @pytest.mark.asyncio
    async def test_read_draft_progress_with_google_sheets_provider(self):
        """Test read_draft_progress with real Google Sheets provider (mocked)"""

        # Mock the Google Sheets provider to return test data
        mock_provider = AsyncMock()
        mock_service = AsyncMock()

        # Mock draft data
        mock_draft_data = {
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "pick_in_round": 1,
                    "team": "Cock N Bulls",
                    "owner": "Levi",
                    "player_name": "Isiah Pacheco   KC",
                    "position": "RB",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "pick_in_round": 2,
                    "team": "Jodi's Broncos",
                    "owner": "Jodi",
                    "player_name": "Derrick Henry   BAL",
                    "position": "RB",
                },
            ],
            "current_pick": 3,
            "teams": [
                {
                    "team_number": 1,
                    "owner": "Levi",
                    "team_name": "Cock N Bulls",
                    "player_col": 1,
                    "position_col": 2,
                },
                {
                    "team_number": 2,
                    "owner": "Jodi",
                    "team_name": "Jodi's Broncos",
                    "player_col": 3,
                    "position_col": 4,
                },
            ],
            "current_team": {
                "team_number": 3,
                "owner": "Scott",
                "team_name": "Royal Chiefs",
                "player_col": 5,
                "position_col": 6,
            },
            "draft_state": {
                "total_picks": 2,
                "total_teams": 10,
                "completed_rounds": 1,
                "current_round": 1,
            },
            "available_players": [],
        }

        mock_service.read_draft_data.return_value = mock_draft_data

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
