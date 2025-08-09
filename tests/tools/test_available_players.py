"""Tests for available players tool."""

from unittest.mock import patch

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.tools.available_players import _normalize_player_name, get_available_players


class TestAvailablePlayers:
    """Test available players functionality."""

    @pytest.fixture
    def mock_draft_state(self):
        """Mock draft state with some picks."""
        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
            {"team_name": "Willow's Witches", "owner": "Willow", "team_number": 2},
        ]

        picks = [
            DraftPick(
                owner="Buffy",
                player=Player(
                    name="Josh Allen",
                    team="BUF",
                    position="QB",
                    bye_week=12,
                    ranking=1,
                    projected_points=99.0,
                    injury_status=InjuryStatus.HEALTHY,
                ),
            ),
            DraftPick(
                owner="Willow",
                player=Player(
                    name="Christian McCaffrey",
                    team="SF",
                    position="RB",
                    bye_week=9,
                    ranking=2,
                    projected_points=98.0,
                    injury_status=InjuryStatus.HEALTHY,
                ),
            ),
        ]

        return DraftState(teams=teams, picks=picks)

    @pytest.fixture
    def mock_rankings_response(self):
        """Mock response from player rankings tool."""
        return {
            "success": True,
            "players": [
                {
                    "name": "Lamar Jackson",
                    "team": "BAL",
                    "position": "QB",
                    "bye_week": 14,
                    "ranking": 3,
                    "projected_points": 96.0,
                    "injury_status": "HEALTHY",
                    "notes": "Dual-threat QB",
                },
                {
                    "name": "Josh Allen",  # This one is drafted
                    "team": "BUF",
                    "position": "QB",
                    "bye_week": 12,
                    "ranking": 1,
                    "projected_points": 99.0,
                    "injury_status": "HEALTHY",
                    "notes": "Elite QB",
                },
                {
                    "name": "Dak Prescott",
                    "team": "DAL",
                    "position": "QB",
                    "bye_week": 7,
                    "ranking": 5,
                    "projected_points": 90.0,
                    "injury_status": "HEALTHY",
                    "notes": "Solid QB",
                },
                {
                    "name": "Tua Tagovailoa",
                    "team": "MIA",
                    "position": "QB",
                    "bye_week": 6,
                    "ranking": 8,
                    "projected_points": 85.0,
                    "injury_status": "HEALTHY",
                    "notes": "Accurate passer",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_available_players_success(
        self, mock_draft_state, mock_rankings_response
    ):
        """Test successful retrieval of available players."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = mock_rankings_response
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=3)

                assert result["success"] is True
                assert result["position"] == "QB"
                assert result["limit"] == 3
                assert (
                    result["total_available"] == 3
                )  # 4 total - 1 drafted (Josh Allen)
                assert result["returned_count"] == 3

                # Check that Josh Allen is filtered out (he was drafted)
                player_names = [p["name"] for p in result["players"]]
                assert "Josh Allen" not in player_names
                assert "Lamar Jackson" in player_names
                assert "Dak Prescott" in player_names
                assert "Tua Tagovailoa" in player_names

                # Should be sorted by projected_points (descending)
                players = result["players"]
                assert players[0]["name"] == "Lamar Jackson"  # 96.0 points
                assert players[1]["name"] == "Dak Prescott"  # 90.0 points
                assert players[2]["name"] == "Tua Tagovailoa"  # 85.0 points

                # Verify rankings was called with correct position
                mock_rankings.assert_called_once_with(position="QB")
                # Verify draft state was fetched
                mock_draft.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_players_with_limit(
        self, mock_draft_state, mock_rankings_response
    ):
        """Test that limit parameter works correctly."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = mock_rankings_response
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=2)

                assert result["success"] is True
                assert result["limit"] == 2
                assert result["returned_count"] == 2
                assert result["total_available"] == 3  # Total available before limit

                # Should only return top 2
                assert len(result["players"]) == 2
                assert result["players"][0]["name"] == "Lamar Jackson"
                assert result["players"][1]["name"] == "Dak Prescott"

    @pytest.mark.asyncio
    async def test_get_available_players_invalid_position(self, mock_draft_state):
        """Test error handling for invalid position."""

        with patch("src.tools.available_players.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_available_players(position="INVALID", limit=5)

            assert result["success"] is False
            assert result["error_type"] == "invalid_position"
            assert "Invalid position" in result["error"]

    @pytest.mark.asyncio
    async def test_get_available_players_invalid_limit(self, mock_draft_state):
        """Test error handling for invalid limit."""

        with patch("src.tools.available_players.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_available_players(position="QB", limit=0)

            assert result["success"] is False
            assert result["error_type"] == "invalid_limit"
            assert "must be greater than 0" in result["error"]

    @pytest.mark.asyncio
    async def test_get_available_players_rankings_fail(self, mock_draft_state):
        """Test handling when player rankings fails."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = {
                    "success": False,
                    "error": "Network error",
                }
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=5)

                assert result["success"] is False
                assert result["error_type"] == "rankings_failed"
                assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_available_players_all_drafted(self, mock_draft_state):
        """Test when all players in rankings have been drafted."""

        # Mock rankings with only drafted players
        drafted_only_response = {
            "success": True,
            "players": [
                {
                    "name": "Josh Allen",  # This is drafted
                    "team": "BUF",
                    "position": "QB",
                    "bye_week": 12,
                    "ranking": 1,
                    "projected_points": 99.0,
                    "injury_status": "HEALTHY",
                    "notes": "Elite QB",
                }
            ],
        }

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = drafted_only_response
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=5)

                assert result["success"] is True
                assert result["total_available"] == 0
                assert result["returned_count"] == 0
                assert len(result["players"]) == 0

    @pytest.mark.asyncio
    async def test_get_available_players_draft_state_fail(self):
        """Test handling when draft state fetch fails."""

        with patch("src.tools.available_players.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = {"success": False, "error": "Sheet access denied"}

            result = await get_available_players(position="QB", limit=5)

            assert result["success"] is False
            assert result["error_type"] == "draft_state_failed"
            assert "Sheet access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_get_available_players_case_insensitive_matching(
        self, mock_rankings_response
    ):
        """Test case-insensitive player name matching."""

        # Create draft state with different case
        teams = [{"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1}]
        picks = [
            DraftPick(
                owner="Buffy",
                player=Player(
                    name="josh allen",  # lowercase
                    team="BUF",
                    position="QB",
                    bye_week=12,
                    ranking=1,
                    projected_points=99.0,
                    injury_status=InjuryStatus.HEALTHY,
                ),
            )
        ]
        draft_state = DraftState(teams=teams, picks=picks)

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = mock_rankings_response
                mock_draft.return_value = draft_state

                result = await get_available_players(position="QB", limit=5)

                # "Josh Allen" should still be filtered out despite case difference
                player_names = [p["name"] for p in result["players"]]
                assert "Josh Allen" not in player_names
                assert len(result["players"]) == 3

    @pytest.mark.asyncio
    async def test_get_available_players_unexpected_error(self, mock_draft_state):
        """Test handling of unexpected errors."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.side_effect = Exception("Network request failed")
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=5)

                assert result["success"] is False
                assert result["error_type"] == "unexpected_error"
                assert "Network request failed" in result["error"]
                assert "troubleshooting" in result

    def test_normalize_player_name(self):
        """Test player name normalization."""

        # Test basic normalization
        assert _normalize_player_name("Josh Allen") == "josh allen"
        assert _normalize_player_name("JOSH ALLEN") == "josh allen"

        # Test punctuation removal
        assert _normalize_player_name("D'Andre Swift") == "dandre swift"
        assert _normalize_player_name("T.J. Hockenson") == "tj hockenson"
        assert _normalize_player_name("Gabe Davis-Jones") == "gabe davisjones"

        # Test suffix removal
        assert _normalize_player_name("Kenneth Walker III") == "kenneth walker"
        assert _normalize_player_name("Marvin Harrison Jr") == "marvin harrison"
        assert _normalize_player_name("Dale Earnhardt Sr") == "dale earnhardt"

        # Test extra whitespace
        assert _normalize_player_name("  Josh   Allen  ") == "josh allen"

    @pytest.mark.asyncio
    async def test_get_available_players_position_case_insensitive(
        self, mock_draft_state, mock_rankings_response
    ):
        """Test position parameter is case insensitive."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = mock_rankings_response
                mock_draft.return_value = mock_draft_state

                # Test lowercase
                result = await get_available_players(position="qb", limit=5)

                assert result["success"] is True
                assert result["position"] == "QB"

                # Verify uppercase was passed to rankings
                mock_rankings.assert_called_with(position="QB")

    @pytest.mark.asyncio
    async def test_get_available_players_includes_context(
        self, mock_draft_state, mock_rankings_response
    ):
        """Test that result includes draft context information."""

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = mock_rankings_response
                mock_draft.return_value = mock_draft_state

                result = await get_available_players(position="QB", limit=5)

                assert result["success"] is True
                assert "draft_context" in result

                context = result["draft_context"]
                assert context["total_picks_made"] == 2  # Buffy and Willow made picks
                assert context["total_teams"] == 2

    @pytest.mark.asyncio
    async def test_get_available_players_with_clean_names(self):
        """Test available players filtering works correctly with clean player names."""

        # Create draft state with clean names (no team abbreviations)
        from src.models.draft_pick import DraftPick
        from src.models.draft_state_simple import DraftState
        from src.models.injury_status import InjuryStatus
        from src.models.player_simple import Player

        picks = [
            DraftPick(
                player=Player(
                    name="Josh Allen",  # Clean name (no team suffix)
                    team="BUF",
                    position="QB",
                    bye_week=7,
                    ranking=1,
                    projected_points=99.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="",
                ),
                owner="Buffy",
            ),
            DraftPick(
                player=Player(
                    name="Lamar Jackson",  # Clean name (no team suffix)
                    team="BAL",
                    position="QB",
                    bye_week=7,
                    ranking=2,
                    projected_points=98.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="",
                ),
                owner="Willow",
            ),
        ]

        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy"},
            {"team_name": "Willow's Witches", "owner": "Willow"},
        ]

        draft_state = DraftState(teams=teams, picks=picks)

        # Mock rankings response with clean names
        rankings_response = {
            "success": True,
            "players": [
                {
                    "name": "Josh Allen",  # Clean name in rankings
                    "team": "BUF",
                    "position": "QB",
                    "bye_week": 7,
                    "ranking": 1,
                    "projected_points": 99.0,
                    "injury_status": "HEALTHY",
                    "notes": "Elite QB",
                },
                {
                    "name": "Lamar Jackson",  # Clean name in rankings
                    "team": "BAL",
                    "position": "QB",
                    "bye_week": 7,
                    "ranking": 2,
                    "projected_points": 98.0,
                    "injury_status": "HEALTHY",
                    "notes": "Dual threat QB",
                },
                {
                    "name": "Jayden Daniels",  # Available player
                    "team": "WAS",
                    "position": "QB",
                    "bye_week": 12,
                    "ranking": 3,
                    "projected_points": 97.0,
                    "injury_status": "HEALTHY",
                    "notes": "Rookie QB",
                },
            ],
        }

        with patch("src.tools.available_players.get_player_rankings") as mock_rankings:
            with patch(
                "src.tools.available_players.get_cached_draft_state"
            ) as mock_draft:
                mock_rankings.return_value = rankings_response
                mock_draft.return_value = draft_state

                result = await get_available_players("QB", 5)

                assert result["success"] is True
                assert result["total_available"] == 1  # Only Jayden Daniels available
                assert result["returned_count"] == 1

                # Verify Josh Allen and Lamar Jackson are NOT in available players
                available_names = {p["name"] for p in result["players"]}
                assert (
                    "Josh Allen" not in available_names
                ), "Josh Allen should be filtered out (already drafted)"
                assert (
                    "Lamar Jackson" not in available_names
                ), "Lamar Jackson should be filtered out (already drafted)"
                assert (
                    "Jayden Daniels" in available_names
                ), "Jayden Daniels should be available"
