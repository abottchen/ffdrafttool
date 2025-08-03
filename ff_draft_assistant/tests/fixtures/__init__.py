"""
Test fixtures for fantasy football draft assistant tests.

This module provides utilities for loading real data snapshots to ensure
tests work with actual data structures rather than just mock data.
"""

import json
import os
from typing import Any, Dict


def load_real_draft_data() -> Dict[str, Any]:
    """
    Load a real draft data snapshot for testing.

    Returns:
        Dict containing real draft state data with actual field names and structures
    """
    fixtures_dir = os.path.dirname(__file__)
    fixture_path = os.path.join(fixtures_dir, 'real_draft_data_snapshot.json')

    with open(fixture_path, 'r') as f:
        return json.load(f)

def get_sample_drafted_players(count: int = 5) -> list:
    """
    Get a sample of drafted players from real data for testing.

    Args:
        count: Number of drafted players to return

    Returns:
        List of drafted player picks with real field structure
    """
    real_data = load_real_draft_data()
    picks = real_data.get('picks', [])
    return picks[:count]

def get_real_draft_state_sample() -> Dict[str, Any]:
    """
    Get a sample draft state with real structure for testing.

    Returns:
        Dict containing sample draft state with real field names
    """
    real_data = load_real_draft_data()
    return {
        'picks': real_data.get('picks', [])[:10],  # First 10 picks
        'teams': real_data.get('teams', []),
        'current_pick': real_data.get('current_pick', 1),
        'current_team': real_data.get('draft_state', {}).get('current_team', {})
    }
