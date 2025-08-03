"""
Draft state caching service to reduce redundant Google Sheets reads.

This module provides caching functionality to store draft state and only
fetch incremental updates from Google Sheets, reducing token usage and
improving performance.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DraftCache:
    """Manages cached draft state to minimize redundant sheet reads based on completed rounds."""

    def __init__(self):
        """
        Initialize the draft cache.

        The cache tracks completed rounds and only re-reads data from the first incomplete round onwards.
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        # Track completed rounds per sheet - starts at 0 when MCP server starts
        self._completed_rounds: Dict[str, int] = {}

    def _get_cache_key(self, sheet_id: str, sheet_range: str) -> str:
        """Generate a unique cache key for a sheet/range combination."""
        return f"{sheet_id}:{sheet_range}"

    def _determine_completed_rounds(self, draft_state: Dict[str, Any]) -> int:
        """
        Determine how many rounds are fully completed based on draft state.

        A round is considered completed when all teams have made their picks for that round.
        """
        picks = draft_state.get('picks', [])
        if not picks:
            return 0

        # Get total number of teams
        teams = draft_state.get('teams', [])
        total_teams = len(teams) if teams else 10  # Default to 10 if not specified

        # Count picks per round
        round_counts = {}
        for pick in picks:
            round_num = pick.get('round', 1)
            round_counts[round_num] = round_counts.get(round_num, 0) + 1

        # Find the highest round where all teams have picked
        completed_rounds = 0
        for round_num in sorted(round_counts.keys()):
            if round_counts[round_num] >= total_teams:
                completed_rounds = round_num
            else:
                break

        return completed_rounds

    def get_cached_state(self, sheet_id: str, sheet_range: str) -> Optional[Dict[str, Any]]:
        """
        Get cached draft state if available.

        Returns:
            Cached draft state dict or None if not available
        """
        cache_key = self._get_cache_key(sheet_id, sheet_range)
        cache_entry = self._cache.get(cache_key)

        if cache_entry:
            completed_rounds = self._completed_rounds.get(sheet_id, 0)
            logger.info(f"Cache hit for {cache_key}, completed rounds: {completed_rounds}")
            return cache_entry['draft_state']

        logger.info(f"Cache miss for {cache_key}")
        return None

    def update_cache(self, sheet_id: str, sheet_range: str, draft_state: Dict[str, Any]) -> None:
        """
        Update the cache with new draft state and determine completed rounds.

        Args:
            sheet_id: Google Sheet ID
            sheet_range: Range being cached
            draft_state: Complete draft state to cache
        """
        cache_key = self._get_cache_key(sheet_id, sheet_range)

        # Determine how many rounds are fully completed
        completed_rounds = self._determine_completed_rounds(draft_state)
        self._completed_rounds[sheet_id] = completed_rounds

        # Cache the full draft state
        picks = draft_state.get('picks', [])
        self._cache[cache_key] = {
            'timestamp': datetime.now(),
            'draft_state': draft_state,
            'completed_rounds': completed_rounds,
            'total_picks': len(picks)
        }

        logger.info(f"Cache updated for {cache_key}, completed rounds: {completed_rounds}, total picks: {len(picks)}")

    def should_use_incremental_read(self, sheet_id: str, sheet_range: str, force_full_refresh: bool = False) -> Tuple[bool, int]:
        """
        Determine if we can use incremental reading and from which round.

        Args:
            sheet_id: Google Sheet ID
            sheet_range: Range to check
            force_full_refresh: If True, force full read of entire sheet

        Returns:
            Tuple of (use_incremental, first_round_to_read)
            - use_incremental: True if we have cached data and can read incrementally
            - first_round_to_read: Round number to start reading from (1-based)
        """
        if force_full_refresh:
            logger.info(f"Force refresh requested for {sheet_id}, reading full sheet")
            self._completed_rounds[sheet_id] = 0  # Reset completed rounds
            return False, 1

        completed_rounds = self._completed_rounds.get(sheet_id, 0)
        cache_key = self._get_cache_key(sheet_id, sheet_range)

        if completed_rounds == 0 or cache_key not in self._cache:
            logger.info(f"No completed rounds cached for {sheet_id}, reading full sheet")
            return False, 1

        # Read from the first incomplete round
        first_round_to_read = completed_rounds + 1
        logger.info(f"Incremental read for {sheet_id}: {completed_rounds} rounds completed, reading from round {first_round_to_read}")
        return True, first_round_to_read

    def get_incremental_range(self, sheet_id: str, sheet_range: str, first_round_to_read: int) -> str:
        """
        Calculate the Google Sheets range to read starting from a specific round.

        Args:
            sheet_id: Google Sheet ID (for logging)
            sheet_range: Original full range (e.g., "Draft!A1:V24")
            first_round_to_read: Round number to start reading from (1-based)

        Returns:
            Modified range string for incremental read
        """
        # Parse the original range
        parts = sheet_range.split('!')
        if len(parts) != 2:
            return sheet_range  # Fallback to full range

        sheet_name = parts[0]
        range_part = parts[1]

        # Extract column range (e.g., A1:V24 -> A:V)
        if ':' in range_part:
            start_cell, end_cell = range_part.split(':')
            start_col = ''.join(c for c in start_cell if c.isalpha())
            end_col = ''.join(c for c in end_cell if c.isalpha())

            # Calculate starting row (round N starts at row N+4, since header rows take up 1-4)
            start_row = first_round_to_read + 4
            end_row = 24  # Assuming max 20 rounds + 4 header rows

            # Create incremental range
            incremental_range = f"{sheet_name}!{start_col}{start_row}:{end_col}{end_row}"
            logger.info(f"Incremental range for {sheet_id}: {incremental_range}")
            return incremental_range

        return sheet_range  # Fallback to full range

    def merge_incremental_data(self, sheet_id: str, cached_state: Dict[str, Any],
                             new_picks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge incremental draft picks with cached state.

        Args:
            sheet_id: Google Sheet ID
            cached_state: Previously cached draft state
            new_picks: New picks from the incremental read

        Returns:
            Updated draft state with new picks merged in
        """
        logger.info(f"Merging {len(new_picks)} new picks with cached state")

        # Start with cached state
        updated_state = cached_state.copy()
        existing_picks = updated_state.get('picks', [])

        # Create a set of existing pick numbers to avoid duplicates
        existing_pick_numbers = {pick.get('pick_number', 0) for pick in existing_picks}

        # Add new picks that aren't already in the cache
        new_picks_added = 0
        for pick in new_picks:
            pick_number = pick.get('pick_number', 0)
            if pick_number not in existing_pick_numbers:
                existing_picks.append(pick)
                new_picks_added += 1

        # Sort picks by pick number to maintain order
        existing_picks.sort(key=lambda p: p.get('pick_number', 0))
        updated_state['picks'] = existing_picks

        # Update completed rounds based on new state
        completed_rounds = self._determine_completed_rounds(updated_state)
        self._completed_rounds[sheet_id] = completed_rounds

        logger.info(f"Merged {new_picks_added} new picks, now {len(existing_picks)} total picks, {completed_rounds} completed rounds")
        return updated_state

    def clear_cache(self, sheet_id: Optional[str] = None, sheet_range: Optional[str] = None) -> None:
        """
        Clear cache entries.

        Args:
            sheet_id: Clear only this sheet's cache (optional)
            sheet_range: Clear only this specific range (optional)
        """
        if sheet_id and sheet_range:
            cache_key = self._get_cache_key(sheet_id, sheet_range)
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"Cleared cache for {cache_key}")
        elif sheet_id:
            # Clear all entries for this sheet
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{sheet_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared all cache entries for sheet {sheet_id}")
        else:
            # Clear entire cache
            self._cache.clear()
            logger.info("Cleared entire draft cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache state."""
        return {
            'entries': len(self._cache),
            'sheets': list(set(k.split(':')[0] for k in self._cache.keys())),
            'completed_rounds_per_sheet': self._completed_rounds.copy(),
            'total_picks_cached': sum(
                entry.get('total_picks', 0)
                for entry in self._cache.values()
            )
        }

    def get_completed_rounds(self, sheet_id: str) -> int:
        """Get the number of completed rounds for a specific sheet."""
        return self._completed_rounds.get(sheet_id, 0)
