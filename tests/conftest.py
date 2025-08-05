"""
Shared pytest fixtures for all tests.
"""

import json
from pathlib import Path
import pytest
from src.models.test_data import DraftData, Pick, Team, DraftStateInfo


@pytest.fixture
def draft_progress_data():
    """Load draft progress test data from JSON fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "draft_progress_fixture.json"
    with open(fixture_path) as f:
        data = json.load(f)
    
    # Convert JSON data to dataclasses
    picks = [Pick(**pick_data) for pick_data in data["picks"]]
    teams = [Team(**team_data) for team_data in data["teams"]]
    current_team = Team(**data["current_team"])
    draft_state = DraftStateInfo(**data["draft_state"])
    
    draft_data = DraftData(
        picks=picks,
        draft_state=draft_state,
        teams=teams,
        current_team=current_team
    )
    
    # Add extra fields that aren't part of standard dataclass
    result = draft_data.to_dict()
    result["current_pick"] = 3
    result["available_players"] = []
    
    return result


@pytest.fixture
def sample_pick_rb():
    """A sample RB pick for testing."""
    return Pick.builder() \
        .pick_number(1) \
        .round(1) \
        .team("Test Team") \
        .player("Christian McCaffrey") \
        .position("RB") \
        .bye_week(7) \
        .build()


@pytest.fixture
def sample_pick_wr():
    """A sample WR pick for testing."""
    return Pick.builder() \
        .pick_number(2) \
        .round(1) \
        .team("Test Team") \
        .player("Tyreek Hill") \
        .position("WR") \
        .bye_week(10) \
        .build()