"""
Draft state caching with TTL support.
"""

import logging
from typing import Any, Dict, Optional

from cachetools import TTLCache

from src.config import (
    DEFAULT_SHEET_ID,
    DEFAULT_SHEET_RANGE,
    DRAFT_CACHE_MINUTES,
)
from src.services.sheets_service import GoogleSheetsProvider, SheetsService

logger = logging.getLogger(__name__)

# TTL-based cache for draft state
_draft_state_cache: TTLCache = TTLCache(
    maxsize=1, ttl=DRAFT_CACHE_MINUTES * 60  # Convert minutes to seconds
)


async def get_cached_draft_state(
    sheet_id: Optional[str] = None, sheet_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get draft state with caching.

    Args:
        sheet_id: Google Sheets ID (uses default if not provided)
        sheet_range: Range to read (uses default if not provided)

    Returns:
        DraftState object or error dict
    """
    # Use defaults if not provided
    sheet_id = sheet_id or DEFAULT_SHEET_ID
    sheet_range = sheet_range or DEFAULT_SHEET_RANGE

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
