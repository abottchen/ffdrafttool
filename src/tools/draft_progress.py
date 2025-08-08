import logging
from typing import Any, Dict

from src.services.sheets_service import GoogleSheetsProvider, SheetsService

logger = logging.getLogger(__name__)


async def read_draft_progress(
    sheet_id: str, sheet_range: str = "Draft!A1:V24", force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Read draft progress from Google Sheets and return simplified draft state.

    Args:
        sheet_id: Google Sheets ID
        sheet_range: Range to read (e.g., "Draft!A1:V24")
        force_refresh: If True, ignore cache and fetch fresh data from Google Sheets

    Returns:
        Dict containing simplified draft state data
    """
    import time

    start_time = time.time()
    logger.info(f"Reading draft progress from sheet {sheet_id}, range {sheet_range}")

    try:
        # Create Google Sheets provider - fail fast if not available
        try:
            provider = GoogleSheetsProvider()
        except ImportError as e:
            logger.error(f"Google Sheets API dependencies not installed: {e}")
            return {
                "success": False,
                "error": "Google Sheets API not available",
                "error_type": "missing_dependencies",
                "troubleshooting": {
                    "problem": "Google Sheets API dependencies are not installed",
                    "solution": "Install required packages with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
                    "next_steps": [
                        "1. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
                        "2. Set up Google Sheets API credentials using setup_google_sheets.py",
                        "3. Retry reading draft progress",
                    ],
                },
                "sheet_id": sheet_id,
                "sheet_range": sheet_range,
            }
        except FileNotFoundError as e:
            logger.error(f"Google Sheets credentials not found: {e}")
            return {
                "success": False,
                "error": "Google Sheets credentials not configured",
                "error_type": "missing_credentials",
                "troubleshooting": {
                    "problem": "Google Sheets API credentials file (credentials.json) not found",
                    "solution": "Set up Google Sheets API authentication",
                    "next_steps": [
                        "1. Go to https://console.developers.google.com/",
                        "2. Create a project and enable Google Sheets API",
                        "3. Create OAuth 2.0 credentials for desktop application",
                        "4. Download credentials.json to the project directory",
                        "5. Run setup_google_sheets.py to test authentication",
                        "6. Retry reading draft progress",
                    ],
                },
                "sheet_id": sheet_id,
                "sheet_range": sheet_range,
            }

        sheets_service = SheetsService(provider)

        # Read and parse draft data with caching support
        processed_data = await sheets_service.read_draft_data(
            sheet_id, sheet_range, force_refresh
        )

        # Add success field for adapter compatibility
        processed_data["success"] = True

        # Convert to simplified DraftState using adapter
        from src.services.sheets_adapter import SheetsAdapter

        adapter = SheetsAdapter()
        draft_state = adapter.convert_to_draft_state(processed_data)

        logger.info(
            f"read_draft_progress completed in {time.time() - start_time:.2f} seconds"
        )

        # Pass through additional fields from processed_data
        result = {
            "success": True,
            "sheet_id": sheet_id,
            "total_teams": len(draft_state.teams),
            "total_picks": len(draft_state.picks),
            "teams": [
                {"team_name": team["team_name"], "owner": team["owner"]}
                for team in draft_state.teams
            ],
            "picks": [
                {
                    "owner": pick.owner,
                    "player": {
                        "name": pick.player.name,
                        "team": pick.player.team,
                        "position": pick.player.position,
                        "bye_week": pick.player.bye_week,
                        "ranking": pick.player.ranking,
                        "projected_points": pick.player.projected_points,
                        "injury_status": pick.player.injury_status.value,
                        "notes": pick.player.notes,
                    },
                }
                for pick in draft_state.picks
            ],
        }

        # Pass through additional fields if they exist
        if "current_pick" in processed_data:
            result["current_pick"] = processed_data["current_pick"]
        if "current_team" in processed_data:
            result["current_team"] = processed_data["current_team"]

        return result

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error reading draft progress: {error_message}")

        # Provide specific troubleshooting based on error type
        troubleshooting = {
            "problem": f"Failed to read draft data from Google Sheets: {error_message}",
            "next_steps": [
                "1. Verify the Google Sheet ID is correct",
                "2. Ensure the sheet is accessible (shared with your Google account or public)",
                "3. Check that the sheet range exists and contains data",
                "4. Verify your Google Sheets API authentication is working",
            ],
        }

        # Add specific guidance for common errors
        if "403" in error_message or "permission" in error_message.lower():
            troubleshooting["solution"] = "Sheet access denied - check permissions"
            troubleshooting["next_steps"] = [
                "1. Ensure the Google Sheet is shared with your Google account",
                "2. Or make the sheet publicly viewable with link sharing",
                "3. Verify the sheet ID in the URL is correct",
                "4. Check that your Google account has access to the sheet",
            ]
        elif "404" in error_message or "not found" in error_message.lower():
            troubleshooting["solution"] = "Sheet not found - check sheet ID and range"
            troubleshooting["next_steps"] = [
                "1. Verify the Google Sheet ID from the URL",
                "2. Check that the sheet tab name is correct (e.g., 'Draft')",
                "3. Ensure the range exists in the sheet",
                "4. Confirm the sheet hasn't been deleted or moved",
            ]
        elif (
            "authentication" in error_message.lower()
            or "credentials" in error_message.lower()
        ):
            troubleshooting["solution"] = "Authentication failed - refresh credentials"
            troubleshooting["next_steps"] = [
                "1. Delete token.json to force re-authentication",
                "2. Run setup_google_sheets.py to re-authenticate",
                "3. Ensure credentials.json is valid and for the correct project",
                "4. Check that Google Sheets API is enabled in your project",
            ]
        else:
            troubleshooting["solution"] = (
                "Check network connection and sheet accessibility"
            )

        return {
            "success": False,
            "error": error_message,
            "error_type": "sheet_access_failed",
            "troubleshooting": troubleshooting,
            "sheet_id": sheet_id,
            "sheet_range": sheet_range,
        }
