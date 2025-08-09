"""Tests for team roster tool."""

from unittest.mock import patch

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.tools.team_roster import get_team_roster


class TestTeamRoster:
    """Test team roster functionality."""

    @pytest.fixture
    def mock_draft_state(self):
        """Mock draft state with multiple owners and picks."""
        teams = [
            {"team_name": "Sunnydale Slayers", "owner": "Buffy", "team_number": 1},
            {"team_name": "Willow's Witches", "owner": "Willow", "team_number": 2},
            {"team_name": "Xander's Xperts", "owner": "Xander", "team_number": 3},
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
                    notes="Elite QB",
                ),
            ),
            DraftPick(
                owner="Buffy",
                player=Player(
                    name="Christian McCaffrey",
                    team="SF",
                    position="RB",
                    bye_week=9,
                    ranking=2,
                    projected_points=98.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="Workhorse RB",
                ),
            ),
            DraftPick(
                owner="Willow",
                player=Player(
                    name="Tyreek Hill",
                    team="MIA",
                    position="WR",
                    bye_week=6,
                    ranking=3,
                    projected_points=97.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="Speedy WR",
                ),
            ),
            DraftPick(
                owner="Xander",
                player=Player(
                    name="Lamar Jackson",
                    team="BAL",
                    position="QB",
                    bye_week=14,
                    ranking=4,
                    projected_points=96.0,
                    injury_status=InjuryStatus.HEALTHY,
                    notes="Dual-threat QB",
                ),
            ),
        ]

        return DraftState(teams=teams, picks=picks)

    @pytest.mark.asyncio
    async def test_get_team_roster_success(self, mock_draft_state):
        """Test successful retrieval of team roster."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_team_roster("Buffy")

            assert result["success"] is True
            assert result["owner_name"] == "Buffy"
            assert len(result["players"]) == 2

            # Check that Buffy's players are returned
            player_names = [p.name for p in result["players"]]
            assert "Josh Allen" in player_names
            assert "Christian McCaffrey" in player_names

            # Verify players are Player objects
            for player in result["players"]:
                assert isinstance(player, Player)

            # Verify draft state was fetched
            mock_draft.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_team_roster_case_insensitive(self, mock_draft_state):
        """Test that owner name matching is case insensitive."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_team_roster("buffy")

            assert result["success"] is True
            assert result["owner_name"] == "buffy"
            assert len(result["players"]) == 2

            # Check that Buffy's players are returned despite case difference
            player_names = [p.name for p in result["players"]]
            assert "Josh Allen" in player_names
            assert "Christian McCaffrey" in player_names

    @pytest.mark.asyncio
    async def test_get_team_roster_no_picks(self, mock_draft_state):
        """Test owner with no picks returns empty list."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_team_roster("Giles")

            assert result["success"] is True
            assert result["owner_name"] == "Giles"
            assert len(result["players"]) == 0
            assert result["players"] == []

    @pytest.mark.asyncio
    async def test_get_team_roster_single_pick(self, mock_draft_state):
        """Test owner with single pick."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_team_roster("Willow")

            assert result["success"] is True
            assert result["owner_name"] == "Willow"
            assert len(result["players"]) == 1

            player = result["players"][0]
            assert player.name == "Tyreek Hill"
            assert player.position == "WR"
            assert isinstance(player, Player)

    @pytest.mark.asyncio
    async def test_get_team_roster_empty_owner_name(self):
        """Test error handling for empty owner name."""

        result = await get_team_roster("")

        assert result["success"] is False
        assert result["error_type"] == "invalid_owner_name"
        assert "cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_get_team_roster_whitespace_owner_name(self):
        """Test error handling for whitespace-only owner name."""

        result = await get_team_roster("   ")

        assert result["success"] is False
        assert result["error_type"] == "invalid_owner_name"
        assert "cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_get_team_roster_draft_state_fail(self):
        """Test handling when draft state fetch fails."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = {"success": False, "error": "Sheet access denied"}

            result = await get_team_roster("Buffy")

            assert result["success"] is False
            assert result["error_type"] == "draft_state_failed"
            assert "Sheet access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_get_team_roster_unexpected_draft_state_format(self):
        """Test handling when draft state has unexpected format."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            # Return something that's not a DraftState object or error dict
            mock_draft.return_value = "invalid_format"

            result = await get_team_roster("Buffy")

            assert result["success"] is False
            assert result["error_type"] == "invalid_draft_state"
            assert "Unexpected draft state format" in result["error"]

    @pytest.mark.asyncio
    async def test_get_team_roster_unexpected_error(self, mock_draft_state):
        """Test handling of unexpected errors."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.side_effect = Exception("Network connection failed")

            result = await get_team_roster("Buffy")

            assert result["success"] is False
            assert result["error_type"] == "unexpected_error"
            assert "Network connection failed" in result["error"]
            assert "troubleshooting" in result

    @pytest.mark.asyncio
    async def test_get_team_roster_owner_name_trimming(self, mock_draft_state):
        """Test that owner names are trimmed of whitespace."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            result = await get_team_roster("  Buffy  ")

            assert result["success"] is True
            assert result["owner_name"] == "Buffy"  # Should be trimmed
            assert len(result["players"]) == 2

    @pytest.mark.asyncio
    async def test_get_team_roster_multiple_owners_verification(self, mock_draft_state):
        """Test that each owner gets only their own picks."""

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            mock_draft.return_value = mock_draft_state

            # Test Buffy (2 picks)
            result_buffy = await get_team_roster("Buffy")
            assert len(result_buffy["players"]) == 2
            buffy_names = [p.name for p in result_buffy["players"]]
            assert "Josh Allen" in buffy_names
            assert "Christian McCaffrey" in buffy_names

            # Test Willow (1 pick)
            result_willow = await get_team_roster("Willow")
            assert len(result_willow["players"]) == 1
            willow_names = [p.name for p in result_willow["players"]]
            assert "Tyreek Hill" in willow_names

            # Test Xander (1 pick)
            result_xander = await get_team_roster("Xander")
            assert len(result_xander["players"]) == 1
            xander_names = [p.name for p in result_xander["players"]]
            assert "Lamar Jackson" in xander_names

            # Verify no cross-contamination
            assert "Tyreek Hill" not in buffy_names
            assert "Lamar Jackson" not in buffy_names
            assert "Josh Allen" not in willow_names
            assert "Christian McCaffrey" not in willow_names
