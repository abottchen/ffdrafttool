"""Tests for the tracker API service."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.services.tracker_api_service import TrackerAPIService


@pytest.fixture
def api_service():
    """Create a TrackerAPIService instance."""
    return TrackerAPIService()


@pytest.fixture
def mock_draft_state_json():
    """Mock JSON response from draft-state endpoint."""
    return {
        "teams": [
            {"owner_id": 1, "budget_remaining": 168, "picks": []},
            {"owner_id": 2, "budget_remaining": 200, "picks": []},
        ],
        "next_to_nominate": 1,
        "version": 1,
    }


@pytest.fixture
def mock_owner_json():
    """Mock JSON response from owner endpoint."""
    return {"id": 1, "owner_name": "Giles", "team_name": "The Watchers Council"}


@pytest.fixture
def mock_players_json():
    """Mock JSON response from players endpoint."""
    return [
        {
            "id": 1,
            "first_name": "Patrick",
            "last_name": "Mahomes",
            "team": "KC",
            "position": "QB",
        },
        {
            "id": 2,
            "first_name": "Josh",
            "last_name": "Allen",
            "team": "BUF",
            "position": "QB",
        },
    ]


@pytest.mark.asyncio
async def test_get_draft_state(api_service, mock_draft_state_json):
    """Test fetching draft state from API."""

    with patch(
        "src.services.tracker_api_service.aiohttp.ClientSession"
    ) as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_draft_state_json)
        mock_response.raise_for_status = MagicMock()

        # Create a mock for the get() method that returns an async context manager
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get.return_value = mock_get

        result = await api_service.get_draft_state()

        assert result == mock_draft_state_json
        assert len(result["teams"]) == 2
        mock_session.get.assert_called_once_with(
            "http://localhost:8175/api/v1/draft-state"
        )


@pytest.mark.asyncio
async def test_get_owner_info(api_service, mock_owner_json):
    """Test fetching owner information from API."""

    with patch(
        "src.services.tracker_api_service.aiohttp.ClientSession"
    ) as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_owner_json)
        mock_response.raise_for_status = MagicMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get.return_value = mock_get

        result = await api_service.get_owner_info(1)

        assert result == mock_owner_json
        assert result["owner_name"] == "Giles"
        assert result["team_name"] == "The Watchers Council"
        mock_session.get.assert_called_once_with(
            "http://localhost:8175/api/v1/owners/1"
        )


@pytest.mark.asyncio
async def test_get_all_players(api_service, mock_players_json):
    """Test fetching all players from API."""

    with patch(
        "src.services.tracker_api_service.aiohttp.ClientSession"
    ) as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_players_json)
        mock_response.raise_for_status = MagicMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get.return_value = mock_get

        result = await api_service.get_all_players()

        assert result == mock_players_json
        assert len(result) == 2
        assert result[0]["first_name"] == "Patrick"
        mock_session.get.assert_called_once_with("http://localhost:8175/api/v1/players")


@pytest.mark.asyncio
async def test_custom_base_url():
    """Test that custom base URL is used correctly."""
    custom_url = "http://tracker.example.com:8080"
    api_service = TrackerAPIService(base_url=custom_url)

    with patch(
        "src.services.tracker_api_service.aiohttp.ClientSession"
    ) as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"teams": []})
        mock_response.raise_for_status = MagicMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get.return_value = mock_get

        await api_service.get_draft_state()

        mock_session.get.assert_called_once_with(
            "http://tracker.example.com:8080/api/v1/draft-state"
        )


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test that API errors are properly raised."""
    api_service = TrackerAPIService()

    with patch(
        "src.services.tracker_api_service.aiohttp.ClientSession"
    ) as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=404
            )
        )

        # Make __aenter__ raise the exception when the response tries to check status
        async def raise_error():
            mock_response.raise_for_status()
            return mock_response

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(side_effect=raise_error)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get.return_value = mock_get

        with pytest.raises(aiohttp.ClientResponseError):
            await api_service.get_draft_state()
