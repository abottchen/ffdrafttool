#!/usr/bin/env python3
"""
Comprehensive tests for the analyze_available_players tool.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tools import analyze_available_players


class TestAnalyzeAvailablePlayers:
    """Test suite for analyze_available_players function"""

    @pytest.fixture
    def sample_draft_state(self):
        """Sample draft state with picks and team info"""
        return {
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "team": "Team Alpha",
                    "player": "Christian McCaffrey",
                    "position": "RB",
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "team": "Team Beta",
                    "player": "Tyreek Hill",
                    "position": "WR",
                },
                {
                    "pick_number": 3,
                    "round": 1,
                    "team": "Team Gamma",
                    "player": "Justin Jefferson",
                    "position": "WR",
                },
                {
                    "pick_number": 4,
                    "round": 1,
                    "team": "Team Delta",
                    "player": "Jahmyr Gibbs DET",
                    "position": "RB",
                },
                {
                    "pick_number": 5,
                    "round": 1,
                    "team": "Team Echo",
                    "player": "Mike Williams NYJ",
                    "position": "WR",
                },
            ],
            "draft_state": {
                "total_picks": 5,
                "total_teams": 10,
                "current_round": 1,
                "completed_rounds": 0,
                "draft_rules": {
                    "auction_rounds": [1, 2, 3],
                    "keeper_round": 4,
                    "snake_start_round": 5,
                },
            },
        }

    @pytest.fixture
    def sample_rankings_response(self):
        """Sample rankings response from get_player_rankings"""
        return {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Christian McCaffrey",
                        "position": "RB",
                        "team": "SF",
                        "bye_week": 9,
                        "average_rank": 1.0,
                        "average_score": 95.5,
                        "rankings": {"fantasysharks": {"rank": 1, "score": 95.5}},
                        "commentary": "Elite RB1 with high ceiling",
                    },
                    {
                        "name": "Derrick Henry",
                        "position": "RB",
                        "team": "BAL",
                        "bye_week": 14,
                        "average_rank": 8.0,
                        "average_score": 88.2,
                        "rankings": {"fantasysharks": {"rank": 8, "score": 88.2}},
                        "commentary": "Consistent goal line back",
                    },
                    {
                        "name": "Cooper Kupp",
                        "position": "WR",
                        "team": "LAR",
                        "bye_week": 6,
                        "average_rank": 15.0,
                        "average_score": 82.1,
                        "rankings": {"fantasysharks": {"rank": 15, "score": 82.1}},
                        "commentary": "High target share WR",
                    },
                    {
                        "name": "Josh Allen",
                        "position": "QB",
                        "team": "BUF",
                        "bye_week": 12,
                        "average_rank": 25.0,
                        "average_score": 78.5,
                        "rankings": {"fantasysharks": {"rank": 25, "score": 78.5}},
                        "commentary": "Dual threat QB1",
                    },
                    {
                        "name": "Travis Kelce",
                        "position": "TE",
                        "team": "KC",
                        "bye_week": 10,
                        "average_rank": 35.0,
                        "average_score": 75.2,
                        "rankings": {"fantasysharks": {"rank": 35, "score": 75.2}},
                        "commentary": "Elite TE with consistent targets",
                    },
                    {
                        "name": "Jahmyr Gibbs",
                        "position": "RB",
                        "team": "DET",
                        "bye_week": 5,
                        "average_rank": 12.0,
                        "average_score": 85.3,
                        "rankings": {"fantasysharks": {"rank": 12, "score": 85.3}},
                        "commentary": "Explosive dual-threat RB",
                    },
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "NYJ",
                        "bye_week": 12,
                        "average_rank": 45.0,
                        "average_score": 72.1,
                        "rankings": {"fantasysharks": {"rank": 45, "score": 72.1}},
                        "commentary": "Big-play receiver when healthy",
                    },
                    {
                        "name": "Mike Williams",
                        "position": "WR",
                        "team": "PIT",
                        "bye_week": 9,
                        "average_rank": 95.0,
                        "average_score": 55.5,
                        "rankings": {"fantasysharks": {"rank": 95, "score": 55.5}},
                        "commentary": "Deep threat option",
                    },
                ]
            },
        }

    @pytest.mark.asyncio
    async def test_analyze_basic_functionality(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test basic functionality of analyze_available_players"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            # Verify basic structure
            assert result["success"] is True
            assert "analysis" in result
            assert "players" in result
            assert "position_breakdown" in result
            assert "recommendations" in result

            # Verify draft analysis
            analysis = result["analysis"]
            assert analysis["current_round"] == 1
            assert analysis["round_type"] == "auction"
            assert (
                "elite talent" in analysis["strategy_note"].lower()
                or "scarcity" in analysis["strategy_note"].lower()
            )

            # Verify players are filtered (McCaffrey should be excluded as drafted)
            players = result["players"]
            player_names = [p["name"] for p in players]
            assert "Christian McCaffrey" not in player_names  # Should be filtered out
            assert "Derrick Henry" in player_names  # Should be available

            # Verify value metrics are calculated
            for player in players:
                assert "value_metrics" in player
                assert "scarcity_analysis" in player
                assert "overall_value" in player["value_metrics"]
                assert "tier" in player["value_metrics"]

    @pytest.mark.asyncio
    async def test_position_filtering(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test position filtering functionality"""

        # Create RB-only response
        rb_only_response = {
            "success": True,
            "aggregated": {
                "players": [
                    p
                    for p in sample_rankings_response["aggregated"]["players"]
                    if p["position"] == "RB"
                ]
            },
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = rb_only_response

            # Test RB filter
            result = await analyze_available_players(
                sample_draft_state, position_filter="RB"
            )

            assert result["success"] is True
            players = result["players"]

            # All returned players should be RBs
            for player in players:
                assert player["position"] == "RB"

            # Should have called get_player_rankings with position filter
            mock_rankings.assert_called_with(
                sources=["fantasysharks", "espn", "yahoo", "fantasypros"],
                position="RB",
                limit=None,
                force_refresh=False,
            )

    @pytest.mark.asyncio
    async def test_position_filtering_token_efficiency(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test that position filtering improves token efficiency by reducing response size"""

        # Create position-specific responses
        qb_only_response = {
            "success": True,
            "aggregated": {
                "players": [
                    p
                    for p in sample_rankings_response["aggregated"]["players"]
                    if p["position"] == "QB"
                ]
            },
        }

        rb_only_response = {
            "success": True,
            "aggregated": {
                "players": [
                    p
                    for p in sample_rankings_response["aggregated"]["players"]
                    if p["position"] == "RB"
                ]
            },
        }

        def mock_get_rankings(*args, **kwargs):
            """Mock function that returns filtered results based on position parameter"""
            position = kwargs.get("position")
            if position == "QB":
                return qb_only_response
            elif position == "RB":
                return rb_only_response
            else:
                return sample_rankings_response  # All positions

        with patch(
            "src.tools.analyze_players.get_player_rankings",
            new_callable=AsyncMock,
            side_effect=mock_get_rankings,
        ) as mock_rankings:

            # Test without position filter (all positions)
            result_all = await analyze_available_players(
                sample_draft_state, position_filter=None, limit=50
            )
            assert result_all["success"] is True

            # Test with QB filter only
            result_qb = await analyze_available_players(
                sample_draft_state, position_filter="QB", limit=50
            )
            assert result_qb["success"] is True

            # Test with RB filter only
            result_rb = await analyze_available_players(
                sample_draft_state, position_filter="RB", limit=50
            )
            assert result_rb["success"] is True

            # Verify position filtering works correctly
            qb_players = result_qb["players"]
            rb_players = result_rb["players"]
            all_players = result_all["players"]

            # All QB results should be QBs only
            for player in qb_players:
                assert player["position"] == "QB"

            # All RB results should be RBs only
            for player in rb_players:
                assert player["position"] == "RB"

            # Filtered results should be subsets of all results
            assert len(qb_players) <= len(all_players)
            assert len(rb_players) <= len(all_players)

            # Convert to JSON strings to estimate token usage
            import json

            json_all = json.dumps(result_all)
            json_qb = json.dumps(result_qb)
            json_rb = json.dumps(result_rb)

            # Position-filtered responses should be smaller (more token efficient)
            assert len(json_qb) <= len(
                json_all
            ), "QB filter should reduce response size"
            assert len(json_rb) <= len(
                json_all
            ), "RB filter should reduce response size"

            # Verify that get_player_rankings was called with correct position filters
            call_args_list = mock_rankings.call_args_list
            assert len(call_args_list) == 3

            # Verify the position parameter was passed correctly in each call
            all_call, qb_call, rb_call = call_args_list
            assert all_call.kwargs.get("position") is None  # All positions
            assert qb_call.kwargs.get("position") == "QB"  # QB only
            assert rb_call.kwargs.get("position") == "RB"  # RB only

    @pytest.mark.asyncio
    async def test_invalid_position_filter(self, sample_draft_state):
        """Test handling of invalid position filter"""

        result = await analyze_available_players(
            sample_draft_state, position_filter="INVALID"
        )

        assert result["success"] is False
        assert "Invalid position filter" in result["error"]
        assert "Valid positions: QB, RB, WR, TE, K, DST" in result["error"]

    @pytest.mark.asyncio
    async def test_limit_functionality(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test limit parameter functionality"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state, limit=2)

            assert result["success"] is True
            assert len(result["players"]) == 2

            # Should be sorted by value (highest first)
            players = result["players"]
            if len(players) >= 2:
                assert (
                    players[0]["value_metrics"]["overall_value"]
                    >= players[1]["value_metrics"]["overall_value"]
                )

    @pytest.mark.asyncio
    async def test_value_metrics_calculation(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test value metrics are calculated correctly"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is True
            players = result["players"]

            for player in players:
                value_metrics = player["value_metrics"]

                # Check all required value metrics exist
                assert "overall_value" in value_metrics
                assert "rank_value" in value_metrics
                assert "scarcity_multiplier" in value_metrics
                assert "tier" in value_metrics
                assert "tier_rank" in value_metrics
                assert "positional_rank" in value_metrics
                assert "position_depth" in value_metrics

                # Check value calculations make sense
                assert value_metrics["overall_value"] >= 0
                assert value_metrics["scarcity_multiplier"] >= 1.0
                assert value_metrics["tier_rank"] in [1, 2, 3, 4, 5, 6]
                assert value_metrics["positional_rank"] >= 1

    @pytest.mark.asyncio
    async def test_scarcity_analysis(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test scarcity analysis calculations"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is True
            players = result["players"]

            for player in players:
                scarcity = player["scarcity_analysis"]

                # Check all required scarcity fields exist
                assert "position_scarcity" in scarcity
                assert "available_at_position" in scarcity
                assert "position_rank" in scarcity
                assert "is_positional_run" in scarcity

                # Check scarcity values are valid
                assert scarcity["position_scarcity"] in ["High", "Medium", "Low"]
                assert scarcity["available_at_position"] >= 0
                assert scarcity["position_rank"] >= 1
                assert isinstance(scarcity["is_positional_run"], bool)

    @pytest.mark.asyncio
    async def test_position_breakdown(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test position breakdown functionality"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is True
            position_breakdown = result["position_breakdown"]

            # Should have breakdown for each position found
            for pos, breakdown in position_breakdown.items():
                assert "count" in breakdown
                assert "best_available" in breakdown
                assert "scarcity_level" in breakdown

                # Best available should have required fields
                if breakdown["best_available"]:
                    best = breakdown["best_available"]
                    assert "name" in best
                    assert "rank" in best
                    assert "value" in best

                # Scarcity level should be valid
                assert breakdown["scarcity_level"] in ["High", "Medium", "Low"]

    @pytest.mark.asyncio
    async def test_recommendations(self, sample_draft_state, sample_rankings_response):
        """Test recommendations generation"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is True
            recommendations = result["recommendations"]

            # Check recommendation categories exist
            assert "high_value_targets" in recommendations
            assert "scarcity_picks" in recommendations
            assert "tier_breaks" in recommendations

            # Check recommendations are lists
            assert isinstance(recommendations["high_value_targets"], list)
            assert isinstance(recommendations["scarcity_picks"], list)
            assert isinstance(recommendations["tier_breaks"], list)

    @pytest.mark.asyncio
    async def test_round_type_detection(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test different round types are detected correctly"""

        # Test auction round
        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)
            assert result["analysis"]["round_type"] == "auction"
            assert (
                "elite talent" in result["analysis"]["strategy_note"].lower()
                or "scarcity" in result["analysis"]["strategy_note"].lower()
            )

        # Test keeper round
        draft_state_keeper = sample_draft_state.copy()
        draft_state_keeper["draft_state"]["current_round"] = 4

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(draft_state_keeper)
            assert result["analysis"]["round_type"] == "keeper"
            assert (
                "value" in result["analysis"]["strategy_note"].lower()
                or "opportunity" in result["analysis"]["strategy_note"].lower()
            )

        # Test snake round
        draft_state_snake = sample_draft_state.copy()
        draft_state_snake["draft_state"]["current_round"] = 5

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(draft_state_snake)
            assert result["analysis"]["round_type"] == "snake"
            assert "snake" in result["analysis"]["strategy_note"].lower()

    @pytest.mark.asyncio
    async def test_drafted_player_filtering(
        self, sample_draft_state, sample_rankings_response
    ):
        """Test that drafted players are properly filtered out"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is True
            players = result["players"]
            player_names = [p["name"] for p in players]

            # Drafted players should not appear in available players (name-only checks)
            simple_drafted_names = [
                "Christian McCaffrey",
                "Tyreek Hill",
                "Justin Jefferson",
                "Jahmyr Gibbs",
            ]
            for drafted_name in simple_drafted_names:
                assert (
                    drafted_name not in player_names
                ), f"Drafted player {drafted_name} should not appear in available players"

            # Special test for Mike Williams - NYJ version was drafted but PIT should be available
            mike_williams_players = [p for p in players if p["name"] == "Mike Williams"]
            # Should only have PIT Mike Williams since NYJ version was drafted
            assert (
                len(mike_williams_players) == 1
            ), f"Expected 1 Mike Williams but found {len(mike_williams_players)}"
            assert (
                mike_williams_players[0]["team"] == "PIT"
            ), f"Expected PIT Mike Williams but found {mike_williams_players[0]['team']}"

    @pytest.mark.asyncio
    async def test_rankings_failure_handling(self, sample_draft_state):
        """Test handling when player rankings fetch fails"""

        failed_rankings_response = {
            "success": False,
            "error": "Network error fetching rankings",
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = failed_rankings_response

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is False
            assert "Failed to fetch player rankings" in result["error"]
            assert "ranking_error" in result

    @pytest.mark.asyncio
    async def test_empty_draft_state(self, sample_rankings_response):
        """Test handling of empty draft state"""

        empty_draft_state = {
            "picks": [],
            "draft_state": {
                "current_round": 1,
                "total_teams": 10,
                "draft_rules": {
                    "auction_rounds": [1, 2, 3],
                    "keeper_round": 4,
                    "snake_start_round": 5,
                },
            },
        }

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.return_value = sample_rankings_response

            result = await analyze_available_players(empty_draft_state)

            assert result["success"] is True
            # All players should be available since none are drafted
            assert result["analysis"]["total_available"] == len(
                sample_rankings_response["aggregated"]["players"]
            )

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_draft_state):
        """Test general error handling"""

        with patch(
            "src.tools.analyze_players.get_player_rankings", new_callable=AsyncMock
        ) as mock_rankings:
            mock_rankings.side_effect = Exception("Unexpected error")

            result = await analyze_available_players(sample_draft_state)

            assert result["success"] is False
            assert "error" in result
            assert "error_type" in result
            assert result["error_type"] == "analysis_failed"
            assert "troubleshooting" in result


if __name__ == "__main__":
    pytest.main([__file__])
