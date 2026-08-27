"""Tests for the auction state tool."""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.auction_state import get_auction_state

DRAFT_STATE = {
    "nominated": {
        "player_id": 4427366,
        "current_bid": 34,
        "current_bidder_id": 2,
        "nominating_owner_id": 1,
    },
    "teams": [
        {"owner_id": 1, "budget_remaining": 168, "max_bid": 154, "picks": []},
        {"owner_id": 2, "budget_remaining": 111, "max_bid": 97, "picks": []},
    ],
    "next_to_nominate": 1,
    "up_next": 2,
    "version": 33,
}

PLAYERS = [
    {
        "id": 4427366,
        "first_name": "Breece",
        "last_name": "Hall",
        "team": "NYJ",
        "position": "RB",
    }
]

OWNERS = {
    1: {"id": 1, "owner_name": "Buffy", "team_name": "Sunnydale Slayers"},
    2: {"id": 2, "owner_name": "Willow", "team_name": "Dark Phoenix Rising"},
}


def _patched_api(draft_state=None, players=None):
    """Patch TrackerAPIService so the tool talks to fixtures, not the network."""
    api = AsyncMock()
    api.get_draft_state.return_value = (
        DRAFT_STATE if draft_state is None else draft_state
    )
    api.get_all_players.return_value = PLAYERS if players is None else players

    async def owner_side_effect(owner_id):
        return OWNERS[owner_id]

    api.get_owner_info.side_effect = owner_side_effect
    return patch("src.tools.auction_state.TrackerAPIService", return_value=api)


@pytest.mark.asyncio
async def test_auction_state_reports_each_team_budget_by_owner_name():
    """Budgets and max bids come back keyed to owner names, not owner IDs."""
    with patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"), _patched_api():
        result = await get_auction_state()

    assert result["success"] is True
    teams = {team["owner"]: team for team in result["teams"]}
    assert teams["Buffy"]["budget_remaining"] == 168
    assert teams["Buffy"]["max_bid"] == 154
    assert teams["Buffy"]["team_name"] == "Sunnydale Slayers"
    assert teams["Willow"]["budget_remaining"] == 111
    assert teams["Willow"]["max_bid"] == 97


@pytest.mark.asyncio
async def test_auction_state_resolves_nomination_order_to_owner_names():
    """next_to_nominate/up_next are owner IDs in the API and names in the tool."""
    with patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"), _patched_api():
        result = await get_auction_state()

    assert result["next_to_nominate"] == "Buffy"
    assert result["up_next"] == "Willow"


@pytest.mark.asyncio
async def test_auction_state_resolves_active_nomination():
    """The live nomination names the player and the owner holding the high bid."""
    with patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"), _patched_api():
        result = await get_auction_state()

    nominated = result["nominated"]
    assert nominated["player"]["name"] == "Breece Hall"
    assert nominated["player"]["position"] == "RB"
    assert nominated["player"]["team"] == "NYJ"
    assert nominated["current_bid"] == 34
    assert nominated["current_bidder"] == "Willow"
    assert nominated["nominating_owner"] == "Buffy"


@pytest.mark.asyncio
async def test_auction_state_reports_no_nomination_between_players():
    """Between nominations the tracker sends null; the tool reports None, not an error."""
    idle = dict(DRAFT_STATE, nominated=None)
    with (
        patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"),
        _patched_api(draft_state=idle),
    ):
        result = await get_auction_state()

    assert result["success"] is True
    assert result["nominated"] is None


@pytest.mark.asyncio
async def test_auction_state_normalizes_nominated_jaguar_team():
    """A nominated Jaguar is reported as JAC so it matches the rankings data."""
    jaguar = [
        {
            "id": 4427366,
            "first_name": "Brian",
            "last_name": "Thomas Jr.",
            "team": "JAX",
            "position": "WR",
        }
    ]
    with (
        patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"),
        _patched_api(players=jaguar),
    ):
        result = await get_auction_state()

    assert result["nominated"]["player"]["team"] == "JAC"


@pytest.mark.asyncio
async def test_auction_state_rejects_non_auction_format():
    """Dan's draft is a snake format with no budgets - the tool must refuse it."""
    with patch("src.tools.auction_state.DRAFT_FORMAT", "dan"):
        result = await get_auction_state()

    assert result["success"] is False
    assert result["error_type"] == "unsupported_format"


@pytest.mark.asyncio
async def test_auction_state_reports_api_failure():
    """A tracker that is down returns a structured error, not an exception."""
    api = AsyncMock()
    api.get_draft_state.side_effect = ConnectionError("tracker is not running")

    with (
        patch("src.tools.auction_state.DRAFT_FORMAT", "tracker"),
        patch("src.tools.auction_state.TrackerAPIService", return_value=api),
    ):
        result = await get_auction_state()

    assert result["success"] is False
    assert result["error_type"] == "api_access_failed"
    assert "tracker is not running" in result["error"]
