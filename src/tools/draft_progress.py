import logging
from typing import Any, Dict

from src.services.sheets_service import GoogleSheetsProvider, SheetsService

logger = logging.getLogger(__name__)


async def read_draft_progress(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Read draft progress from Google Sheets using cached data when available.

    Args:
        force_refresh: If True, ignore cache and fetch fresh data from Google Sheets

    Returns:
        DraftState object or error dict
    """
    import time

    start_time = time.time()
    logger.info(f"Reading draft progress (force_refresh={force_refresh})")

    if force_refresh:
        # Force refresh bypasses cache and goes directly to sheets service
        try:
            # Get sheet_id and sheet_range from config
            from src.config import DEFAULT_SHEET_ID, DRAFT_FORMAT, _config

            sheet_id = DEFAULT_SHEET_ID
            format_config = _config["draft"]["formats"].get(DRAFT_FORMAT)
            if format_config and "sheet_range" in format_config:
                sheet_range = format_config["sheet_range"]
            else:
                sheet_range = "Draft!A1:V24"

            provider = GoogleSheetsProvider()
            sheets_service = SheetsService(provider)
            result = await sheets_service.read_draft_data(
                sheet_id, sheet_range, force_refresh=True
            )

            logger.info(
                f"read_draft_progress (force refresh) completed in {time.time() - start_time:.2f} seconds"
            )
            return result

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
        except Exception as e:
            logger.error(f"Error in force refresh: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "sheet_access_failed",
                "sheet_id": sheet_id,
                "sheet_range": sheet_range,
            }

    # Use cached version (will fetch fresh if cache miss)
    from src.services.draft_state_cache import get_cached_draft_state

    result = await get_cached_draft_state()

    logger.info(
        f"read_draft_progress (cached) completed in {time.time() - start_time:.2f} seconds"
    )
    return result
