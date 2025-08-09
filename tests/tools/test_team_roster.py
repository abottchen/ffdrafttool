"""Tests for team roster tool."""

import logging
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
        """Test successful retrieval of team roster with enrichment."""

        # Mock rankings data for enrichment
        mock_qb_rankings = {
            "success": True,
            "players": [
                {
                    "name": "Josh Allen",
                    "team": "BUF",
                    "position": "QB",
                    "bye_week": 12,
                    "ranking": 1,
                    "projected_points": 99.0,
                    "notes": "Elite QB",
                }
            ],
        }

        mock_rb_rankings = {
            "success": True,
            "players": [
                {
                    "name": "Christian McCaffrey",
                    "team": "SF",
                    "position": "RB",
                    "bye_week": 9,
                    "ranking": 2,
                    "projected_points": 98.0,
                    "notes": "Workhorse RB",
                }
            ],
        }

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            with patch("src.tools.team_roster.get_player_rankings") as mock_rankings:
                mock_draft.return_value = mock_draft_state

                # Return different rankings based on position
                def rankings_side_effect(position):
                    if position == "QB":
                        return mock_qb_rankings
                    elif position == "RB":
                        return mock_rb_rankings
                    return {"success": True, "players": []}

                mock_rankings.side_effect = rankings_side_effect

                result = await get_team_roster("Buffy")

                assert result["success"] is True
                assert result["owner_name"] == "Buffy"
                assert len(result["players"]) == 2

                # Check that Buffy's players are returned with enriched data
                players_by_name = {p.name: p for p in result["players"]}

                josh = players_by_name["Josh Allen"]
                assert josh.bye_week == 12  # Should be enriched, not default 1
                assert josh.projected_points == 99.0
                assert josh.ranking == 1

                cmc = players_by_name["Christian McCaffrey"]
                assert cmc.bye_week == 9  # Should be enriched, not default 1
                assert cmc.projected_points == 98.0
                assert cmc.ranking == 2

                # Verify players are Player objects
                for player in result["players"]:
                    assert isinstance(player, Player)

                # Verify draft state and rankings were fetched
                mock_draft.assert_called_once()
                assert (
                    mock_rankings.call_count == 4
                )  # 2 positions * 2 calls each (check + fetch)

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

    @pytest.mark.asyncio
    async def test_get_team_roster_player_not_found_in_rankings(
        self, mock_draft_state, caplog
    ):
        """Test error logging when drafted player not found in rankings."""

        # Mock rankings that don't contain the drafted players
        mock_empty_rankings = {
            "success": True,
            "players": [],  # Empty - players won't be found
        }

        with patch("src.tools.team_roster.get_cached_draft_state") as mock_draft:
            with patch("src.tools.team_roster.get_player_rankings") as mock_rankings:
                mock_draft.return_value = mock_draft_state
                mock_rankings.return_value = mock_empty_rankings

                with caplog.at_level(logging.ERROR):
                    result = await get_team_roster("Buffy")

                assert result["success"] is True
                assert len(result["players"]) == 2

                # Check that error was logged for missing players
                error_logs = [
                    record for record in caplog.records if record.levelname == "ERROR"
                ]
                assert len(error_logs) == 2  # One for each player not found

                assert "PLAYER DATA ISSUE" in error_logs[0].message
                assert (
                    "Josh Allen" in error_logs[0].message
                    or "Christian McCaffrey" in error_logs[0].message
                )
                assert "was not found in" in error_logs[0].message
