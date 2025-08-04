from unittest.mock import patch

import pytest

from src.tools.mcp_tools import suggest_draft_pick


class TestRosterAnalysisAdam:
    """Test that roster analysis correctly identifies picks for owner 'Adam'"""

    @pytest.mark.asyncio
    async def test_roster_analysis_identifies_adam_picks(self):
        """Test that roster analysis correctly counts Adam's picks"""
        # Mock draft state with Adam having made several picks
        mock_draft_state = {
            "picks": [
                # Adam's picks
                {
                    "pick_number": 5,
                    "round": 1,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Tyreek Hill",
                    "position": "WR",
                },
                {
                    "pick_number": 16,
                    "round": 2,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Breece Hall",
                    "position": "RB",
                },
                {
                    "pick_number": 25,
                    "round": 3,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Mark Andrews",
                    "position": "TE",
                },
                {
                    "pick_number": 36,
                    "round": 4,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Kyren Williams",
                    "position": "RB",
                },
                {
                    "pick_number": 45,
                    "round": 5,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Kenneth Walker III",
                    "position": "RB",
                },
                {
                    "pick_number": 56,
                    "round": 6,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Dak Prescott",
                    "position": "QB",
                },
                {
                    "pick_number": 65,
                    "round": 7,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "DeVonta Smith",
                    "position": "WR",
                },
                {
                    "pick_number": 76,
                    "round": 8,
                    "team": "Lambs",
                    "owner": "Adam",
                    "player_name": "Zay Flowers",
                    "position": "WR",
                },
                # Other team picks (should not be counted in Adam's roster)
                {
                    "pick_number": 1,
                    "round": 1,
                    "team": "Cock N Bulls",
                    "owner": "Levi",
                    "player_name": "Isiah Pacheco",
                    "position": "RB",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "team": "Jodi's Broncos",
                    "owner": "Jodi",
                    "player_name": "Derrick Henry",
                    "position": "RB",
                },
            ],
            "current_pick": 77,
            "teams": [
                {"team_name": "Lambs", "owner": "Adam", "draft_position": 5},
                {"team_name": "Cock N Bulls", "owner": "Levi", "draft_position": 1},
                {"team_name": "Jodi's Broncos", "owner": "Jodi", "draft_position": 2},
            ],
            "draft_state": {
                "total_picks": 76,
                "total_teams": 10,
                "current_round": 8,
                "completed_rounds": 7,
            },
        }

        # Mock the rankings call to return some available players so the function doesn't fail
        mock_rankings_result = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Available Player 1",
                        "position": "QB",
                        "team": "FA",
                        "bye_week": 10,
                        "average_rank": 50,
                        "average_score": 150,
                        "injury_status": None,
                    },
                    {
                        "name": "Available Player 2",
                        "position": "RB",
                        "team": "FA",
                        "bye_week": 11,
                        "average_rank": 51,
                        "average_score": 149,
                        "injury_status": None,
                    },
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_rankings:
            mock_rankings.return_value = mock_rankings_result

            result = await suggest_draft_pick(mock_draft_state, team_name="Lambs")

            # Debug: Print the result if it failed
            if not result.get("success", False):
                print(
                    f"Function failed with error: {result.get('error', 'Unknown error')}"
                )
                print(f"Full result: {result}")

            # Verify the function completed successfully
            assert result["success"] is True
            assert "roster_analysis" in result

            roster_analysis = result["roster_analysis"]
            position_needs = roster_analysis["position_needs"]
            current_roster = roster_analysis["current_roster"]

            # Verify Adam's QB picks are counted
            assert (
                position_needs["QB"]["current_count"] == 1
            ), f"Expected 1 QB, got {position_needs['QB']['current_count']}"
            assert len(current_roster["QB"]) == 1
            assert current_roster["QB"][0]["player_name"] == "Dak Prescott"

            # Verify Adam's RB picks are counted (3 total)
            assert (
                position_needs["RB"]["current_count"] == 3
            ), f"Expected 3 RBs, got {position_needs['RB']['current_count']}"
            assert len(current_roster["RB"]) == 3
            rb_names = [player["player_name"] for player in current_roster["RB"]]
            assert "Breece Hall" in rb_names
            assert "Kyren Williams" in rb_names
            assert "Kenneth Walker III" in rb_names

            # Verify Adam's WR picks are counted (3 total)
            assert (
                position_needs["WR"]["current_count"] == 3
            ), f"Expected 3 WRs, got {position_needs['WR']['current_count']}"
            assert len(current_roster["WR"]) == 3
            wr_names = [player["player_name"] for player in current_roster["WR"]]
            assert "Tyreek Hill" in wr_names
            assert "DeVonta Smith" in wr_names
            assert "Zay Flowers" in wr_names

            # Verify Adam's TE picks are counted
            assert (
                position_needs["TE"]["current_count"] == 1
            ), f"Expected 1 TE, got {position_needs['TE']['current_count']}"
            assert len(current_roster["TE"]) == 1
            assert current_roster["TE"][0]["player_name"] == "Mark Andrews"

            # Verify positions Adam hasn't drafted yet show 0
            assert position_needs["K"]["current_count"] == 0
            assert position_needs["DST"]["current_count"] == 0
            assert len(current_roster["K"]) == 0
            assert len(current_roster["DST"]) == 0

            # Verify other teams' picks are NOT counted in Adam's roster
            # Levi and Jodi's picks should not appear in Adam's roster
            all_adam_players = []
            for position_players in current_roster.values():
                all_adam_players.extend([p["player_name"] for p in position_players])

            assert (
                "Isiah Pacheco" not in all_adam_players
            ), "Levi's pick should not be in Adam's roster"
            assert (
                "Derrick Henry" not in all_adam_players
            ), "Jodi's pick should not be in Adam's roster"

    @pytest.mark.asyncio
    async def test_roster_analysis_with_no_adam_picks(self):
        """Test roster analysis when Adam hasn't made any picks yet"""
        mock_draft_state = {
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "team": "Other Team",
                    "owner": "Other Owner",
                    "player_name": "Some Player",
                    "position": "RB",
                }
            ],
            "current_pick": 2,
            "teams": [
                {"team_name": "Lambs", "owner": "Adam", "draft_position": 5},
                {
                    "team_name": "Other Team",
                    "owner": "Other Owner",
                    "draft_position": 1,
                },
            ],
            "draft_state": {
                "total_picks": 1,
                "total_teams": 2,
                "current_round": 1,
                "completed_rounds": 0,
            },
        }

        mock_rankings_result = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Available Player 1",
                        "position": "QB",
                        "team": "FA",
                        "bye_week": 10,
                        "average_rank": 50,
                        "average_score": 150,
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_rankings:
            mock_rankings.return_value = mock_rankings_result

            result = await suggest_draft_pick(mock_draft_state, team_name="Lambs")

            # Debug: Print the result if it failed
            if not result.get("success", False):
                print(
                    f"Function failed with error: {result.get('error', 'Unknown error')}"
                )
                print(f"Full result: {result}")

            assert result["success"] is True
            roster_analysis = result["roster_analysis"]
            position_needs = roster_analysis["position_needs"]
            current_roster = roster_analysis["current_roster"]

            # All positions should show 0 count (this is expected when no picks made)
            for position in ["QB", "RB", "WR", "TE", "K", "DST"]:
                assert position_needs[position]["current_count"] == 0
                assert len(current_roster[position]) == 0

    @pytest.mark.asyncio
    async def test_roster_analysis_identifies_correct_owner(self):
        """Test that roster analysis uses the correct owner identification logic"""
        # Test with different team name but same owner
        mock_draft_state = {
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "team": "Adam's Team",  # Different team name
                    "owner": "Adam",
                    "player_name": "Test Player",
                    "position": "QB",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "team": "Not Adam's Team",
                    "owner": "NotAdam",  # Different owner
                    "player_name": "Other Player",
                    "position": "QB",
                },
            ],
            "current_pick": 3,
            "teams": [
                {"team_name": "Adam's Team", "owner": "Adam", "draft_position": 1},
                {
                    "team_name": "Not Adam's Team",
                    "owner": "NotAdam",
                    "draft_position": 2,
                },
            ],
            "draft_state": {
                "total_picks": 2,
                "total_teams": 2,
                "current_round": 1,
                "completed_rounds": 0,
            },
        }

        mock_rankings_result = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Available Player 1",
                        "position": "QB",
                        "team": "FA",
                        "bye_week": 10,
                        "average_rank": 50,
                        "average_score": 150,
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_rankings:
            mock_rankings.return_value = mock_rankings_result

            result = await suggest_draft_pick(mock_draft_state, team_name="Adam's Team")

            # Debug: Print the result if it failed
            if not result.get("success", False):
                print(
                    f"Function failed with error: {result.get('error', 'Unknown error')}"
                )
                print(f"Full result: {result}")

            assert result["success"] is True
            roster_analysis = result["roster_analysis"]

            # Should only count Adam's pick, not NotAdam's pick
            assert roster_analysis["position_needs"]["QB"]["current_count"] == 1
            assert len(roster_analysis["current_roster"]["QB"]) == 1
            assert (
                roster_analysis["current_roster"]["QB"][0]["player_name"]
                == "Test Player"
            )
