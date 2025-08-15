"""Tests for the tracker draft parser."""

from unittest.mock import AsyncMock, patch

import pytest

from src.models.draft_state_simple import DraftState
from src.services.tracker_draft_parser import TrackerDraftParser


@pytest.fixture
def mock_draft_state_response():
    """Mock response from /api/v1/draft-state endpoint."""
    return {
        "teams": [
            {
                "owner_id": 1,
                "budget_remaining": 168,
                "picks": [
                    {"pick_id": 1, "player_id": 4427366, "owner_id": 1, "price": 13},
                    {"pick_id": 2, "player_id": 4426515, "owner_id": 1, "price": 12},
                ],
            },
            {
                "owner_id": 2,
                "budget_remaining": 111,
                "picks": [
                    {"pick_id": 3, "player_id": 3117251, "owner_id": 2, "price": 56},
                ],
            },
        ],
        "next_to_nominate": 1,
        "version": 33,
    }


@pytest.fixture
def mock_players_response():
    """Mock response from /api/v1/players endpoint."""
    return [
        {
            "id": 4427366,
            "first_name": "Breece",
            "last_name": "Hall",
            "team": "NYJ",
            "position": "RB",
        },
        {
            "id": 4426515,
            "first_name": "Justin",
            "last_name": "Jefferson",
            "team": "MIN",
            "position": "WR",
        },
        {
            "id": 3117251,
            "first_name": "CeeDee",
            "last_name": "Lamb",
            "team": "DAL",
            "position": "WR",
        },
    ]


@pytest.fixture
def mock_owner_responses():
    """Mock responses from /api/v1/owners/{id} endpoint."""
    return {
        1: {"id": 1, "owner_name": "Buffy", "team_name": "Sunnydale Slayers"},
        2: {"id": 2, "owner_name": "Willow", "team_name": "Dark Phoenix Rising"},
    }


@pytest.mark.asyncio
async def test_tracker_parser_parse_draft_data(
    mock_draft_state_response, mock_players_response, mock_owner_responses
):
    """Test that tracker parser correctly fetches and parses API data."""
    parser = TrackerDraftParser()

    # Mock the API service methods
    with patch.object(
        parser.api_service, "get_draft_state", new_callable=AsyncMock
    ) as mock_get_draft:
        with patch.object(
            parser.api_service, "get_all_players", new_callable=AsyncMock
        ) as mock_get_players:
            with patch.object(
                parser.api_service, "get_owner_info", new_callable=AsyncMock
            ) as mock_get_owner:

                # Set up mock return values
                mock_get_draft.return_value = mock_draft_state_response
                mock_get_players.return_value = mock_players_response

                # Mock owner info calls
                async def owner_side_effect(owner_id):
                    return mock_owner_responses[owner_id]

                mock_get_owner.side_effect = owner_side_effect

                # Parse the data
                result = await parser.parse_draft_data([], None)

                # Verify result is a DraftState
                assert isinstance(result, DraftState)

                # Check teams
                assert len(result.teams) == 2
                assert result.teams[0]["owner"] == "Buffy"
                assert result.teams[0]["team"] == "Sunnydale Slayers"
                assert result.teams[1]["owner"] == "Willow"
                assert result.teams[1]["team"] == "Dark Phoenix Rising"

                # Check picks
                assert len(result.picks) == 3

                # First pick (Breece Hall)
                assert result.picks[0].player.name == "Breece Hall"
                assert result.picks[0].player.team == "NYJ"
                assert result.picks[0].player.position == "RB"
                assert result.picks[0].owner == "Buffy"

                # Second pick (Justin Jefferson)
                assert result.picks[1].player.name == "Justin Jefferson"
                assert result.picks[1].player.team == "MIN"
                assert result.picks[1].player.position == "WR"
                assert result.picks[1].owner == "Buffy"

                # Third pick (CeeDee Lamb)
                assert result.picks[2].player.name == "CeeDee Lamb"
                assert result.picks[2].player.team == "DAL"
                assert result.picks[2].player.position == "WR"
                assert result.picks[2].owner == "Willow"

                # Verify API calls were made
                mock_get_draft.assert_called_once()
                mock_get_players.assert_called_once()
                assert mock_get_owner.call_count == 2  # Called for each unique owner


@pytest.mark.asyncio
async def test_tracker_parser_empty_draft():
    """Test that tracker parser handles empty draft state gracefully."""
    parser = TrackerDraftParser()

    with patch.object(
        parser.api_service, "get_draft_state", new_callable=AsyncMock
    ) as mock_get_draft:
        with patch.object(
            parser.api_service, "get_all_players", new_callable=AsyncMock
        ) as mock_get_players:

            # Empty draft state
            mock_get_draft.return_value = {"teams": [], "next_to_nominate": None}
            mock_get_players.return_value = []

            result = await parser.parse_draft_data([], None)

            assert isinstance(result, DraftState)
            assert len(result.teams) == 0
            assert len(result.picks) == 0


@pytest.mark.asyncio
async def test_tracker_parser_missing_player():
    """Test that tracker parser handles missing players gracefully."""
    parser = TrackerDraftParser()

    draft_state = {
        "teams": [
            {
                "owner_id": 1,
                "picks": [
                    {
                        "pick_id": 1,
                        "player_id": 999999,
                        "owner_id": 1,
                    },  # Non-existent player
                ],
            }
        ]
    }

    with patch.object(
        parser.api_service, "get_draft_state", new_callable=AsyncMock
    ) as mock_get_draft:
        with patch.object(
            parser.api_service, "get_all_players", new_callable=AsyncMock
        ) as mock_get_players:
            with patch.object(
                parser.api_service, "get_owner_info", new_callable=AsyncMock
            ) as mock_get_owner:

                mock_get_draft.return_value = draft_state
                mock_get_players.return_value = []  # No players
                mock_get_owner.return_value = {
                    "id": 1,
                    "owner_name": "Spike",
                    "team_name": "Big Bad Vamps",
                }

                result = await parser.parse_draft_data([], None)

                # Should have team but no picks since player wasn't found
                assert len(result.teams) == 1
                assert len(result.picks) == 0


@pytest.mark.asyncio
async def test_tracker_parser_detect_format():
    """Test that tracker parser's detect_format always returns True."""
    parser = TrackerDraftParser()

    # Should always return True since tracker format is explicitly configured
    assert parser.detect_format([])
    assert parser.detect_format([["some", "data"]])


@pytest.mark.asyncio
async def test_tracker_parser_with_custom_base_url():
    """Test that tracker parser can be initialized with custom base URL."""
    custom_url = "http://localhost:9999"
    parser = TrackerDraftParser(base_url=custom_url)

    assert parser.api_service.base_url == custom_url
