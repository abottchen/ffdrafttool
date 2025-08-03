from unittest.mock import AsyncMock, patch

import pytest

from src.tools.mcp_tools import read_draft_progress


class TestReadDraftProgress:
    @pytest.mark.asyncio
    async def test_read_draft_progress_missing_dependencies(self):
        """Test read_draft_progress tool fails when Google API dependencies are missing"""

        # Mock the GoogleSheetsProvider to fail with ImportError
        with patch("src.tools.mcp_tools.GoogleSheetsProvider") as mock_google_provider:
            mock_google_provider.side_effect = ImportError(
                "Google API dependencies not available. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

            result = await read_draft_progress("test_sheet_123", "Draft!A1:Z100")

            # Should fail, not fall back to mock
            assert result["success"] is False
            assert result["error_type"] == "missing_dependencies"
            assert "Google Sheets API not available" in result["error"]
            assert result["sheet_id"] == "test_sheet_123"
            assert result["sheet_range"] == "Draft!A1:Z100"

            # Should include troubleshooting guidance
            troubleshooting = result["troubleshooting"]
            assert "problem" in troubleshooting
            assert "solution" in troubleshooting
            assert "next_steps" in troubleshooting
            assert len(troubleshooting["next_steps"]) >= 3

    @pytest.mark.asyncio
    async def test_read_draft_progress_missing_credentials(self):
        """Test read_draft_progress tool fails when credentials are missing"""

        with patch("src.tools.mcp_tools.GoogleSheetsProvider") as mock_google_provider:
            mock_google_provider.side_effect = FileNotFoundError(
                "Google credentials file not found: credentials.json"
            )

            result = await read_draft_progress("test_sheet_123", "Draft!A1:Z100")

            # Should fail with credentials error
            assert result["success"] is False
            assert result["error_type"] == "missing_credentials"
            assert "Google Sheets credentials not configured" in result["error"]

            # Should include specific troubleshooting for credentials
            troubleshooting = result["troubleshooting"]
            assert "credentials.json" in troubleshooting["problem"]
            assert "console.developers.google.com" in troubleshooting["next_steps"][0]

    @pytest.mark.asyncio
    async def test_read_draft_progress_permission_denied(self):
        """Test read_draft_progress handles 403 permission errors properly"""

        # Mock successful provider creation but fail on data access
        mock_provider = AsyncMock()
        mock_service = AsyncMock()
        mock_service.read_draft_data.side_effect = Exception(
            "HTTP 403: Forbidden - Insufficient permissions"
        )

        with patch(
            "src.tools.mcp_tools.GoogleSheetsProvider", return_value=mock_provider
        ):
            with patch("src.tools.mcp_tools.SheetsService", return_value=mock_service):

                result = await read_draft_progress("forbidden_sheet", "Draft!A1:Z100")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "403" in result["error"] or "Forbidden" in result["error"]

                # Should provide specific guidance for permission errors
                troubleshooting = result["troubleshooting"]
                assert "permission" in troubleshooting["solution"].lower()
                assert any(
                    "shared with your Google account" in step
                    for step in troubleshooting["next_steps"]
                )

    @pytest.mark.asyncio
    async def test_read_draft_progress_with_google_sheets_provider(self):
        """Test read_draft_progress with real Google Sheets provider (mocked)"""

        # Mock the Google Sheets provider to return test data
        mock_provider = AsyncMock()
        mock_service = AsyncMock()

        # Mock draft data with the new team-column format structure
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
            "src.tools.mcp_tools.GoogleSheetsProvider", return_value=mock_provider
        ):
            with patch("src.tools.mcp_tools.SheetsService", return_value=mock_service):

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

    @pytest.mark.asyncio
    async def test_read_draft_progress_sheet_not_found(self):
        """Test read_draft_progress handles 404 not found errors properly"""

        mock_provider = AsyncMock()
        mock_service = AsyncMock()
        mock_service.read_draft_data.side_effect = Exception(
            "HTTP 404: Not Found - The requested sheet was not found"
        )

        with patch(
            "src.tools.mcp_tools.GoogleSheetsProvider", return_value=mock_provider
        ):
            with patch("src.tools.mcp_tools.SheetsService", return_value=mock_service):

                result = await read_draft_progress("nonexistent_sheet", "Draft!A1:Z100")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "404" in result["error"] or "Not Found" in result["error"]

                # Should provide specific guidance for not found errors
                troubleshooting = result["troubleshooting"]
                assert "not found" in troubleshooting["solution"].lower()
                assert any(
                    "Google Sheet ID" in step for step in troubleshooting["next_steps"]
                )

    @pytest.mark.asyncio
    async def test_read_draft_progress_authentication_error(self):
        """Test read_draft_progress handles authentication errors properly"""

        mock_provider = AsyncMock()
        mock_service = AsyncMock()
        mock_service.read_draft_data.side_effect = Exception(
            "Authentication failed: Invalid credentials"
        )

        with patch(
            "src.tools.mcp_tools.GoogleSheetsProvider", return_value=mock_provider
        ):
            with patch("src.tools.mcp_tools.SheetsService", return_value=mock_service):

                result = await read_draft_progress("test_sheet", "Draft!A1:Z100")

                assert result["success"] is False
                assert result["error_type"] == "sheet_access_failed"
                assert "authentication" in result["error"].lower()

                # Should provide specific guidance for auth errors
                troubleshooting = result["troubleshooting"]
                assert "authentication" in troubleshooting["solution"].lower()
                assert any(
                    "token.json" in step for step in troubleshooting["next_steps"]
                )
