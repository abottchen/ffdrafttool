"""Tests for player info tool."""

from unittest.mock import patch

import pytest

from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.tools.player_info import _search_cached_players, get_player_info


class TestPlayerInfo:
    """Test player info functionality."""

    @pytest.fixture
    def mock_players(self):
        """Mock players for testing."""
        return [
            Player(
                name="Josh Allen",
                team="BUF",
                position="QB",
                bye_week=12,
                ranking=1,
                projected_points=99.0,
                injury_status=InjuryStatus.HEALTHY,
                notes="Elite QB"
            ),
            Player(
                name="Christian McCaffrey",
                team="SF",
                position="RB",
                bye_week=9,
                ranking=2,
                projected_points=98.0,
                injury_status=InjuryStatus.HEALTHY,
                notes="Top RB"
            ),
            Player(
                name="Tyreek Hill",
                team="MIA",
                position="WR",
                bye_week=6,
                ranking=3,
                projected_points=97.0,
                injury_status=InjuryStatus.QUESTIONABLE,
                notes="Speed demon WR"
            )
        ]

    def setup_method(self):
        """Clear any existing cache before tests."""
        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            mock_cache.clear_cache()

    @pytest.mark.asyncio
    async def test_get_player_info_found_in_cache(self, mock_players):
        """Test finding player in cached data."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.return_value = [mock_players[0]]  # Josh Allen

            result = await get_player_info(last_name="Allen")

            assert result["success"] is True
            assert result["count"] == 1
            assert len(result["players"]) == 1

            player = result["players"][0]
            assert player["name"] == "Josh Allen"
            assert player["team"] == "BUF"
            assert player["position"] == "QB"
            assert player["ranking"] == 1
            assert player["injury_status"] == "HEALTHY"

            # Verify search was called correctly
            mock_search.assert_called_with("Allen", None, None, None)

    @pytest.mark.asyncio
    async def test_get_player_info_with_all_filters(self, mock_players):
        """Test searching with all available filters."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.return_value = [mock_players[0]]

            result = await get_player_info(
                last_name="Allen",
                first_name="Josh",
                team="BUF",
                position="QB"
            )

            assert result["success"] is True
            assert result["count"] == 1

            # Verify all search criteria were passed
            mock_search.assert_called_with("Allen", "Josh", "BUF", "QB")

            # Verify search criteria is returned
            criteria = result["search_criteria"]
            assert criteria["last_name"] == "Allen"
            assert criteria["first_name"] == "Josh"
            assert criteria["team"] == "BUF"
            assert criteria["position"] == "QB"

    @pytest.mark.asyncio
    async def test_get_player_info_not_found_with_position(self, mock_players):
        """Test loading position data when player not found but position provided."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            # First call returns empty (not in cache)
            # Second call returns player (after loading position data)
            mock_search.side_effect = [[], [mock_players[0]]]

            with patch('src.tools.player_info.get_player_rankings') as mock_rankings:
                mock_rankings.return_value = {"success": True}

                result = await get_player_info(last_name="Allen", position="QB")

                assert result["success"] is True
                assert result["count"] == 1

                # Verify rankings was called to load QB data
                mock_rankings.assert_called_once_with(position="QB")

                # Verify search was called twice
                assert mock_search.call_count == 2

    @pytest.mark.asyncio
    async def test_get_player_info_not_found_no_position(self):
        """Test error when player not found and no position provided."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.return_value = []  # No players found

            result = await get_player_info(last_name="NonExistent")

            assert result["success"] is False
            assert result["error_type"] == "player_not_found"
            assert "NonExistent" in result["error"]
            assert "Try providing a position" in result["error"]

    @pytest.mark.asyncio
    async def test_get_player_info_rankings_load_fails(self):
        """Test handling when loading position rankings fails."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.return_value = []  # No players found

            with patch('src.tools.player_info.get_player_rankings') as mock_rankings:
                mock_rankings.return_value = {"success": False, "error": "Network error"}

                result = await get_player_info(last_name="Allen", position="QB")

                assert result["success"] is False
                assert result["error_type"] == "player_not_found"

    @pytest.mark.asyncio
    async def test_get_player_info_multiple_matches(self, mock_players):
        """Test returning multiple matching players sorted by ranking."""

        # Create two players with same last name
        allen_qb = mock_players[0]  # Josh Allen, ranking 1
        allen_wr = Player(
            name="Keenan Allen",
            team="CHI",
            position="WR",
            bye_week=7,
            ranking=25,
            projected_points=85.0,
            injury_status=InjuryStatus.HEALTHY,
            notes="Veteran WR"
        )

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.return_value = [allen_wr, allen_qb]  # Return in wrong order

            result = await get_player_info(last_name="Allen")

            assert result["success"] is True
            assert result["count"] == 2

            # Should be sorted by ranking (Josh Allen first with ranking 1)
            players = result["players"]
            assert players[0]["name"] == "Josh Allen"
            assert players[0]["ranking"] == 1
            assert players[1]["name"] == "Keenan Allen"
            assert players[1]["ranking"] == 25

    @pytest.mark.asyncio
    async def test_get_player_info_unexpected_error(self):
        """Test handling of unexpected errors."""

        with patch('src.tools.player_info._search_cached_players') as mock_search:
            mock_search.side_effect = Exception("Database connection failed")

            result = await get_player_info(last_name="Allen")

            assert result["success"] is False
            assert result["error_type"] == "unexpected_error"
            assert "Database connection failed" in result["error"]

    def test_search_cached_players_with_search_method(self, mock_players):
        """Test searching when cache has search_players method."""

        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            mock_cache.search_players.return_value = [mock_players[0]]

            result = _search_cached_players("Allen", "Josh", "BUF", "QB")

            assert len(result) == 1
            assert result[0].name == "Josh Allen"

            # Verify search method was called with correct parameters
            mock_cache.search_players.assert_called_once_with(
                last_name="Allen",
                first_name="Josh",
                team="BUF",
                position="QB"
            )

    def test_search_cached_players_manual_search(self, mock_players):
        """Test manual search when cache doesn't have search_players method."""

        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            # Remove search_players method
            mock_cache.search_players = None

            # Mock cache data
            mock_cache.get_all_positions.return_value = ["QB", "RB", "WR"]
            mock_cache.get_position_data.side_effect = [
                [mock_players[0]],  # QB: Josh Allen
                [mock_players[1]],  # RB: Christian McCaffrey
                [mock_players[2]]   # WR: Tyreek Hill
            ]

            # Search for "Allen" - should find Josh Allen
            result = _search_cached_players("Allen")

            assert len(result) == 1
            assert result[0].name == "Josh Allen"

    def test_search_cached_players_position_filter(self, mock_players):
        """Test position filtering in manual search."""

        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            mock_cache.search_players = None
            mock_cache.get_all_positions.return_value = ["QB", "RB"]
            mock_cache.get_position_data.side_effect = [
                [mock_players[0]],  # QB: Josh Allen
                [mock_players[1]]   # RB: Christian McCaffrey
            ]

            # Search for position QB only
            result = _search_cached_players("Allen", position="QB")

            assert len(result) == 1
            assert result[0].position == "QB"

    def test_search_cached_players_team_filter(self, mock_players):
        """Test team filtering in manual search."""

        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            mock_cache.search_players = None
            mock_cache.get_all_positions.return_value = ["QB"]
            mock_cache.get_position_data.return_value = [mock_players[0]]  # Josh Allen (BUF)

            # Search for wrong team - should find nothing
            result = _search_cached_players("Allen", team="MIA")
            assert len(result) == 0

            # Search for correct team - should find Josh Allen
            result = _search_cached_players("Allen", team="BUF")
            assert len(result) == 1
            assert result[0].team == "BUF"

    def test_search_cached_players_name_matching(self, mock_players):
        """Test name matching logic."""

        with patch('src.tools.player_info._rankings_cache') as mock_cache:
            mock_cache.search_players = None
            mock_cache.get_all_positions.return_value = ["QB"]
            mock_cache.get_position_data.return_value = [mock_players[0]]  # Josh Allen

            # Test last name match
            result = _search_cached_players("Allen")
            assert len(result) == 1

            # Test first and last name match
            result = _search_cached_players("Allen", first_name="Josh")
            assert len(result) == 1

            # Test wrong first name
            result = _search_cached_players("Allen", first_name="Tom")
            assert len(result) == 0

            # Test partial name match
            result = _search_cached_players("All")  # Should match "Allen"
            assert len(result) == 1
