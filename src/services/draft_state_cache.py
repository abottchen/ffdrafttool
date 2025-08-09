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
from src.tools.draft_progress import read_draft_progress

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

    # Fetch fresh from Google Sheets
    logger.info(f"Fetching fresh draft state for {cache_key}")
    result = await read_draft_progress(sheet_id, sheet_range)

    # Cache successful results (read_draft_progress now returns DraftState directly)
    if isinstance(result, dict) and result.get("success", False):
        # This is an error dict, don't cache
        return result
    else:
        # It's a DraftState object, cache it
        _draft_state_cache[cache_key] = result
        return result


def clear_draft_state_cache():
    """Clear the draft state cache."""
    _draft_state_cache.clear()
    logger.info("Draft state cache cleared")
