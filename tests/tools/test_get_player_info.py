from unittest.mock import patch

import pytest

from src.tools.mcp_tools import get_player_info


class TestGetPlayerInfo:
    @pytest.mark.asyncio
    async def test_get_player_info_by_last_name_only(self):
        """Test fetching player info with just last name"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Patrick Mahomes",
                        "position": "QB",
                        "team": "KC",
                        "bye_week": 6,
                        "rank": 1,
                        "score": 320.5,
                        "average_rank": 1.2,
                        "rankings": {
                            "espn": {"rank": 1, "score": 325},
                            "yahoo": {"rank": 2, "score": 316},
                        },
                        "projected_stats": {
                            "passing_yards": 4800,
                            "passing_tds": 38,
                            "rushing_yards": 250,
                            "rushing_tds": 2,
                        },
                        "injury_status": None,
                    },
                    {
                        "name": "Austin Mahomes",
                        "position": "QB",
                        "team": "FA",
                        "bye_week": None,
                        "rank": 150,
                        "score": 50.0,
                        "average_rank": 150,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            result = await get_player_info(last_name="Mahomes")

            assert result["success"]
            assert len(result["players"]) == 2

            # Check first player
            patrick = result["players"][0]
            assert patrick["full_name"] == "Patrick Mahomes"
            assert patrick["position"] == "QB"
            assert patrick["team"] == "KC"
            assert patrick["ranking_data"]["rank"] == 1
            assert patrick["ranking_data"]["score"] == 320.5
            assert patrick["ranking_data"]["average_rank"] == 1.2
            assert patrick["projected_stats"]["passing_yards"] == 4800
            assert patrick["injury_status"] is None

    @pytest.mark.asyncio
    async def test_get_player_info_with_full_name(self):
        """Test fetching player info with first and last name"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Patrick Mahomes",
                        "position": "QB",
                        "team": "KC",
                        "bye_week": 6,
                        "rank": 1,
                        "score": 320.5,
                        "average_rank": 1.2,
                        "rankings": {"espn": {"rank": 1, "score": 325}},
                        "projected_stats": {"passing_yards": 4800, "passing_tds": 38},
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            result = await get_player_info(first_name="Patrick", last_name="Mahomes")

            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Patrick Mahomes"

    @pytest.mark.asyncio
    async def test_get_player_info_with_position_filter(self):
        """Test fetching player info with position filter"""
        # Mock should return only WR players when position filter is applied
        mock_rankings_data_wr = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "NYJ",
                        "bye_week": 12,
                        "rank": 45,
                        "score": 180.5,
                        "average_rank": 46.2,
                        "rankings": {},
                        "projected_stats": {
                            "receiving_yards": 950,
                            "receiving_tds": 6,
                            "receptions": 65,
                        },
                        "injury_status": "QUESTIONABLE",
                        "injury_warning": "⚠️ INJURY: Injury: Ankle sprain, game-time decision",
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            # get_player_rankings should be called with position="WR"
            mock_get_rankings.return_value = mock_rankings_data_wr

            result = await get_player_info(last_name="Williams", position="WR")

            # Verify the position filter was passed to get_player_rankings
            mock_get_rankings.assert_called_once_with(
                sources=["fantasysharks", "espn", "yahoo", "fantasypros"],
                position="WR",  # position filter
                limit=None,  # limit
                force_refresh=False,  # force_refresh
            )

            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Mike Williams"
            assert result["players"][0]["position"] == "WR"

    @pytest.mark.asyncio
    async def test_get_player_info_with_team_filter(self):
        """Test fetching player info with team filter"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Tyreek Hill",
                        "position": "WR",
                        "team": "MIA",
                        "bye_week": 10,
                        "rank": 3,
                        "score": 285.5,
                        "average_rank": 3.5,
                        "rankings": {},
                        "projected_stats": {
                            "receiving_yards": 1650,
                            "receiving_tds": 12,
                            "receptions": 110,
                        },
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            result = await get_player_info(last_name="Hill", team="MIA")

            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["team"] == "MIA"

    @pytest.mark.asyncio
    async def test_get_player_info_no_matches(self):
        """Test when no players match the criteria"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Patrick Mahomes",
                        "position": "QB",
                        "team": "KC",
                        "bye_week": 6,
                        "rank": 1,
                        "score": 320.5,
                        "average_rank": 1.2,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            result = await get_player_info(last_name="NonExistentPlayer")

            assert result["success"]
            assert len(result["players"]) == 0
            assert "No players found" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_get_player_info_rankings_failure(self):
        """Test handling when rankings fetch fails"""
        mock_rankings_data = {"success": False, "error": "Failed to fetch rankings"}

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            result = await get_player_info(last_name="Mahomes")

            assert not result["success"]
            assert "Failed to fetch player rankings" in result["error"]

    @pytest.mark.asyncio
    async def test_get_player_info_case_insensitive(self):
        """Test that player name matching is case insensitive"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Patrick Mahomes",
                        "position": "QB",
                        "team": "KC",
                        "bye_week": 6,
                        "rank": 1,
                        "score": 320.5,
                        "average_rank": 1.2,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            # Test with lowercase
            result = await get_player_info(last_name="mahomes")
            assert result["success"]
            assert len(result["players"]) == 1

            # Test with mixed case
            result = await get_player_info(first_name="PATRICK", last_name="MaHoMeS")
            assert result["success"]
            assert len(result["players"]) == 1

    @pytest.mark.asyncio
    async def test_get_player_info_suffix_handling(self):
        """Test that player name matching handles suffixes like Jr., Sr., III"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Michael Penix Jr.",
                        "position": "QB",
                        "team": "ATL",
                        "bye_week": 12,
                        "rank": 125,
                        "score": 95.5,
                        "average_rank": 128.3,
                        "rankings": {},
                        "projected_stats": {"passing_yards": 1200, "passing_tds": 8},
                        "injury_status": None,
                    },
                    {
                        "name": "Marvin Harrison Jr.",
                        "position": "WR",
                        "team": "ARI",
                        "bye_week": 11,
                        "rank": 28,
                        "score": 210.5,
                        "average_rank": 30.2,
                        "rankings": {},
                        "projected_stats": {
                            "receiving_yards": 1100,
                            "receiving_tds": 8,
                            "receptions": 75,
                        },
                        "injury_status": None,
                    },
                    {
                        "name": "Martin Luther King III",
                        "position": "RB",
                        "team": "FA",
                        "bye_week": None,
                        "rank": 250,
                        "score": 10.0,
                        "average_rank": 250,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                    {
                        "name": "Michael Pittman",  # Player without suffix
                        "position": "WR",
                        "team": "IND",
                        "bye_week": 14,
                        "rank": 32,
                        "score": 195.5,
                        "average_rank": 35.7,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            # Test searching for "Penix" should find "Michael Penix Jr."
            result = await get_player_info(last_name="Penix")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Michael Penix Jr."

            # Test searching for "Harrison" should find "Marvin Harrison Jr."
            result = await get_player_info(last_name="Harrison")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Marvin Harrison Jr."

            # Test searching for "King" should find "Martin Luther King III"
            result = await get_player_info(last_name="King")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Martin Luther King III"

            # Test that exact match still works
            result = await get_player_info(last_name="Pittman")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Michael Pittman"

            # Test with first name to narrow down
            result = await get_player_info(first_name="Michael", last_name="Penix")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Michael Penix Jr."

    @pytest.mark.asyncio
    async def test_get_player_info_partial_last_name_matching(self):
        """Test that partial last name matching works correctly - should match from start of last name to first space"""
        mock_rankings_data = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Kenneth Walker III",
                        "position": "RB",
                        "team": "SEA",
                        "bye_week": 10,
                        "rank": 45,
                        "score": 180.5,
                        "average_rank": 46.2,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                    {
                        "name": "John Walker Smith",  # Should NOT match "Walker" search
                        "position": "WR",
                        "team": "FA",
                        "bye_week": None,
                        "rank": 200,
                        "score": 25.0,
                        "average_rank": 200,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "NYJ",
                        "bye_week": 12,
                        "rank": 50,
                        "score": 175.0,
                        "average_rank": 52.1,
                        "rankings": {},
                        "projected_stats": {},
                        "injury_status": None,
                    },
                ]
            },
        }

        with patch("src.tools.mcp_tools.get_player_rankings") as mock_get_rankings:
            mock_get_rankings.return_value = mock_rankings_data

            # Test searching for "Walker" should find "Kenneth Walker III"
            # but NOT "John Walker Smith" (Walker is not the last name there)
            result = await get_player_info(last_name="Walker")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Kenneth Walker III"

            # Test that "Will" should match "Mike Williams"
            # because "Will" is at the start of the last name "Williams"
            result = await get_player_info(last_name="Will")
            assert result["success"]
            assert len(result["players"]) == 1
            assert result["players"][0]["full_name"] == "Mike Williams"
