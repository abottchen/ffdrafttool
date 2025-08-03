
import pytest

from src.tools.mcp_tools import (
    analyze_available_players,
    get_player_rankings,
    suggest_draft_pick,
)


class TestGetPlayerRankings:
    @pytest.mark.asyncio
    async def test_get_player_rankings_success(self):
        # Now uses all sources by default
        result = await get_player_rankings(["fantasysharks", "espn", "yahoo", "fantasypros"])

        assert result["success"]
        assert "aggregated" in result

        aggregated = result["aggregated"]
        assert "players" in aggregated
        assert isinstance(aggregated["players"], list)
        assert len(aggregated["players"]) > 0

        # Check player structure
        first_player = aggregated["players"][0]
        assert "name" in first_player
        assert "position" in first_player
        assert "team" in first_player
        assert "bye_week" in first_player
        assert "rank" in first_player  # Primary ranking only
        assert "score" in first_player  # Primary score only
        assert "average_rank" in first_player

    @pytest.mark.asyncio
    async def test_get_player_rankings_with_position_filter(self):
        result = await get_player_rankings(
            ["fantasysharks", "espn", "yahoo", "fantasypros"],
            position="RB"
        )

        assert result["success"]
        players = result["aggregated"]["players"]
        assert all(p["position"] == "RB" for p in players)

    @pytest.mark.asyncio
    async def test_get_player_rankings_invalid_position(self):
        """Test error handling for invalid position"""
        result = await get_player_rankings(
            ["fantasysharks", "espn", "yahoo", "fantasypros"],
            position="INVALID"
        )

        assert not result["success"]
        assert "Invalid position" in result["error"]

    @pytest.mark.asyncio
    async def test_get_player_rankings_unknown_source(self):
        """Test handling of unknown sources"""
        result = await get_player_rankings(
            ["unknown_source", "espn"]
        )

        assert result["success"]  # Should succeed for valid sources
        # Response structure doesn't expose individual source details,
        # but should still aggregate successfully from valid sources
        assert "aggregated" in result
        assert len(result["aggregated"]["players"]) > 0

    @pytest.mark.asyncio
    async def test_get_player_rankings_fantasysharks_structure(self):
        """Test FantasySharks source structure"""
        result = await get_player_rankings(
            ["fantasysharks"],
            position="QB",
            limit=5
        )

        # Note: This test may fail if no internet connection
        # In a real test environment, we'd mock the network calls
        if result["success"]:
            # Check aggregated data structure
            aggregated = result["aggregated"]
            assert "players" in aggregated
            assert len(aggregated["players"]) <= 5  # Respects limit

            if aggregated["players"]:
                first_player = aggregated["players"][0]
                assert first_player["position"] == "QB"
                assert "rank" in first_player  # Has ranking data

    @pytest.mark.asyncio
    async def test_get_player_rankings_with_limit(self):
        result = await get_player_rankings(
            ["fantasysharks", "espn", "yahoo", "fantasypros"],
            limit=3
        )

        assert result["success"]
        assert len(result["aggregated"]["players"]) <= 3


# TestReadDraftProgress tests moved to tests/tools/test_read_draft_progress.py
# for better organization and comprehensive coverage


class TestAnalyzeAvailablePlayers:
    @pytest.mark.asyncio
    async def test_analyze_available_players_basic(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 25,
            "current_round": 3,
            "my_team_name": "My Team",
            "roster_requirements": {
                "QB": 2, "RB": 4, "WR": 4, "TE": 2
            }
        }

        result = await analyze_available_players(
            draft_state=draft_state,
            position_filter=None,
            limit=20
        )

        assert "players" in result
        assert "position_breakdown" in result
        assert "recommendations" in result
        assert len(result["players"]) <= 20

    @pytest.mark.asyncio
    async def test_analyze_available_players_with_position_filter(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 13,
            "my_team_name": "My Team"
        }

        result = await analyze_available_players(
            draft_state=draft_state,
            position_filter="WR",
            limit=10
        )

        players = result["players"]
        assert all(p["position"] == "WR" for p in players)

    @pytest.mark.asyncio
    async def test_analyze_available_players_includes_value_metrics(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 5,
            "my_team_name": "My Team"
        }

        result = await analyze_available_players(
            draft_state=draft_state
        )

        players = result["players"]
        if players:
            first_player = players[0]
            assert "value_metrics" in first_player
            assert "scarcity_analysis" in first_player
            # Check value metrics structure
            value_metrics = first_player["value_metrics"]
            assert "overall_value" in value_metrics

    @pytest.mark.asyncio
    async def test_analyze_available_players_calculates_scarcity(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 37,
            "current_round": 4,
            "my_team_name": "My Team"
        }

        result = await analyze_available_players(
            draft_state=draft_state
        )

        # Check position breakdown contains scarcity information
        position_breakdown = result["position_breakdown"]
        assert isinstance(position_breakdown, dict)
        assert "RB" in position_breakdown
        assert "WR" in position_breakdown

        # Each position should have count and other metrics
        for pos_data in position_breakdown.values():
            if isinstance(pos_data, dict):
                assert "count" in pos_data
                assert "scarcity_level" in pos_data


class TestSuggestDraftPick:
    @pytest.mark.asyncio
    async def test_suggest_draft_pick_basic(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 10,
            "current_round": 1,
            "my_team_name": "My Team",
            "my_roster": [],
            "roster_requirements": {
                "QB": 2, "RB": 4, "WR": 4, "TE": 2
            }
        }

        result = await suggest_draft_pick(
            draft_state=draft_state,
            strategy="balanced"
        )

        assert "recommendation" in result
        assert "primary_pick" in result["recommendation"]
        assert "alternatives" in result["recommendation"]

        pick = result["recommendation"]["primary_pick"]
        assert "name" in pick
        assert "position" in pick
        assert "value_metrics" in pick

    @pytest.mark.asyncio
    async def test_suggest_draft_pick_with_existing_roster(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 49,
            "current_round": 5,
            "my_team_name": "My Team",
            "my_roster": [
                {"name": "Josh Allen", "position": "QB"},
                {"name": "Christian McCaffrey", "position": "RB"},
                {"name": "Tyreek Hill", "position": "WR"},
                {"name": "CeeDee Lamb", "position": "WR"}
            ],
            "roster_requirements": {
                "QB": 2, "RB": 4, "WR": 4, "TE": 2
            }
        }

        result = await suggest_draft_pick(
            draft_state=draft_state,
            strategy="best_available"
        )

        # Should consider roster needs
        reasoning = ' '.join(result["recommendation"]["primary_pick"]["detailed_reasoning"])
        assert "roster" in reasoning.lower() or "need" in reasoning.lower()

    @pytest.mark.asyncio
    async def test_suggest_draft_pick_different_strategies(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 25,
            "current_round": 3,
            "my_team_name": "My Team",
            "my_roster": [
                {"name": "Lamar Jackson", "position": "QB"},
                {"name": "Derrick Henry", "position": "RB"}
            ]
        }

        # Test different strategies
        strategies = ["balanced", "best_available", "upside", "safe"]
        results = {}

        for strategy in strategies:
            result = await suggest_draft_pick(
                draft_state=draft_state,
                strategy=strategy
            )
            results[strategy] = result

        # Different strategies might suggest different players
        assert all("recommendation" in r for r in results.values())

    @pytest.mark.asyncio
    async def test_suggest_draft_pick_late_round(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 145,
            "current_round": 13,
            "my_team_name": "My Team",
            "my_roster": [
                # Full roster except K and DST
                {"name": "QB1", "position": "QB"},
                {"name": "QB2", "position": "QB"},
                {"name": "RB1", "position": "RB"},
                {"name": "RB2", "position": "RB"},
                {"name": "RB3", "position": "RB"},
                {"name": "RB4", "position": "RB"},
                {"name": "WR1", "position": "WR"},
                {"name": "WR2", "position": "WR"},
                {"name": "WR3", "position": "WR"},
                {"name": "WR4", "position": "WR"},
                {"name": "TE1", "position": "TE"},
                {"name": "TE2", "position": "TE"}
            ],
            "roster_requirements": {
                "QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DST": 1
            }
        }

        result = await suggest_draft_pick(
            draft_state=draft_state,
            strategy="balanced"
        )

        # Should provide a recommendation for the roster gaps
        pick = result["recommendation"]["primary_pick"]
        # With current roster, should prioritize remaining needs (K, DST, or depth)
        assert pick["position"] in ["K", "DST", "QB", "RB", "WR", "TE"]  # Any valid position
        assert "detailed_reasoning" in pick

    @pytest.mark.asyncio
    async def test_suggest_draft_pick_considers_bye_weeks(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 61,
            "current_round": 6,
            "my_team_name": "My Team",
            "my_roster": [
                {"name": "Player1", "position": "RB", "bye_week": 7},
                {"name": "Player2", "position": "RB", "bye_week": 7},
                {"name": "Player3", "position": "WR", "bye_week": 7}
            ]
        }

        result = await suggest_draft_pick(
            draft_state=draft_state,
            strategy="balanced",
            consider_bye_weeks=True
        )

        # Should mention bye week consideration in strategic guidance
        strategic_guidance = result.get("strategic_guidance", {})
        guidance_text = str(strategic_guidance).lower()
        assert "bye" in guidance_text

    @pytest.mark.asyncio
    async def test_suggest_draft_pick_very_late_round(self):
        draft_state = {
            "num_teams": 12,
            "current_pick": 200,
            "current_round": 17,
            "my_team_name": "My Team"
        }

        result = await suggest_draft_pick(
            draft_state=draft_state,
            strategy="balanced"
        )

        # Should still provide a recommendation even in very late rounds
        assert result["success"] is True
        assert result["recommendation"]["primary_pick"] is not None
        pick = result["recommendation"]["primary_pick"]
        assert "name" in pick
        assert "position" in pick
