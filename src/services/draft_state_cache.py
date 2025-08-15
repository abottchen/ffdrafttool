"""
Draft state caching with TTL support.
"""

import logging
from typing import Any, Dict

from cachetools import TTLCache

from src.config import (
    DEFAULT_SHEET_ID,
    DRAFT_CACHE_MINUTES,
    DRAFT_FORMAT,
    _config,
)
from src.services.sheets_service import GoogleSheetsProvider, SheetsService, get_parser

logger = logging.getLogger(__name__)

# TTL-based cache for draft state
_draft_state_cache: TTLCache = TTLCache(
    maxsize=1, ttl=DRAFT_CACHE_MINUTES * 60  # Convert minutes to seconds
)


async def get_cached_draft_state() -> Dict[str, Any]:
    """
    Get draft state with caching.

    Returns:
        DraftState object or error dict
    """
    # Special handling for tracker format (uses API instead of sheets)
    if DRAFT_FORMAT == "tracker":
        cache_key = "tracker:api"

        # Check cache first
        if cache_key in _draft_state_cache:
            logger.info("Returning cached draft state for tracker API")
            return _draft_state_cache[cache_key]

        # Fetch fresh from tracker API
        logger.info("Fetching fresh draft state from tracker API")

        try:
            parser = get_parser()
            result = await parser.parse_draft_data([], None)

            # Cache the DraftState object
            _draft_state_cache[cache_key] = result
            return result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error fetching draft state from tracker API: {error_message}"
            )

            return {
                "success": False,
                "error": error_message,
                "error_type": "api_access_failed",
                "source": "tracker_api",
            }

    # Regular sheet-based formats (dan, adam)
    sheet_id = DEFAULT_SHEET_ID

    format_config = _config["draft"]["formats"].get(DRAFT_FORMAT)
    if format_config and "sheet_range" in format_config:
        sheet_range = format_config["sheet_range"]
    else:
        # Fallback to Draft range if format config not found
        sheet_range = "Draft!A1:V24"

    cache_key = f"{sheet_id}:{sheet_range}"

    # Check cache first
    if cache_key in _draft_state_cache:
        logger.info(f"Returning cached draft state for {cache_key}")
        return _draft_state_cache[cache_key]

    # Fetch fresh from Google Sheets using sheets service directly
    logger.info(f"Fetching fresh draft state for {cache_key}")

    try:
        provider = GoogleSheetsProvider()
        sheets_service = SheetsService(provider)
        result = await sheets_service.read_draft_data(
            sheet_id, sheet_range, force_refresh=True
        )

        # Cache the DraftState object
        _draft_state_cache[cache_key] = result
        return result

    except Exception as e:
        # Return error information for client handling
        error_message = str(e)
        logger.error(f"Error fetching fresh draft state: {error_message}")

        error_result = {
            "success": False,
            "error": error_message,
            "error_type": "sheet_access_failed",
            "sheet_id": sheet_id,
            "sheet_range": sheet_range,
        }

        # Don't cache errors
        return error_result


def clear_draft_state_cache():
    """Clear the draft state cache."""
    _draft_state_cache.clear()
    logger.info("Draft state cache cleared")
