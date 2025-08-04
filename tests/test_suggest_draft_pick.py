#!/usr/bin/env python3
"""
Comprehensive tests for the suggest_draft_pick tool.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.mcp_tools import suggest_draft_pick


class TestSuggestDraftPick:
    """Test suite for suggest_draft_pick function"""

    @pytest.fixture
    def sample_draft_state(self):
        """Sample draft state with picks and team info"""
        return {
            "picks": [
                {
                    "pick_number": 1,
                    "round": 1,
                    "team": "Team Alpha",
                    "player_name": "Christian McCaffrey",
                    "position": "RB",
                    "bye_week": 7,
                },
                {
                    "pick_number": 2,
                    "round": 1,
                    "team": "Test Team",  # Our team
                    "player_name": "Tyreek Hill",
                    "position": "WR",
                    "bye_week": 10,
                },
            ],
            "teams": [{"team_name": "Test Team", "owner": "Test Owner"}],
            "current_team": {"team_name": "Test Team", "owner": "Test Owner"},
            "draft_state": {
                "total_picks": 2,
                "total_teams": 10,
                "current_round": 2,
                "completed_rounds": 1,
                "draft_rules": {
                    "auction_rounds": [1, 2, 3],
                    "keeper_round": 4,
                    "snake_start_round": 5,
                },
            },
        }

    @pytest.fixture
    def sample_analysis_response(self):
        """Sample response from analyze_available_players"""
        return {
            "success": True,
            "analysis": {
                "total_available": 200,
                "analyzed_count": 50,
                "current_round": 2,
                "round_type": "auction",
                "strategy_note": "Focus on elite talent and positional scarcity",
            },
            "players": [
                {
                    "name": "Derrick Henry",
                    "position": "RB",
                    "team": "BAL",
                    "bye_week": 14,
                    "average_rank": 8.0,
                    "average_score": 88.2,
                    "value_metrics": {
                        "overall_value": 85.5,
                        "tier": "Tier 1",
                        "tier_rank": 2,
                        "positional_rank": 2,
                    },
                    "scarcity_analysis": {
                        "position_scarcity": "High",
                        "available_at_position": 15,
                    },
                    "bye_week_analysis": {
                        "bye_week": 14,
                        "bye_week_penalty": 1.0,
                        "conflict_severity": "None",
                        "conflicts_found": [],
                        "helps_bye_diversity": True,
                    },
                },
                {
                    "name": "Josh Allen",
                    "position": "QB",
                    "team": "BUF",
                    "bye_week": 12,
                    "average_rank": 25.0,
                    "average_score": 78.5,
                    "value_metrics": {
                        "overall_value": 75.2,
                        "tier": "Elite",
                        "tier_rank": 1,
                        "positional_rank": 1,
                    },
                    "scarcity_analysis": {
                        "position_scarcity": "Medium",
                        "available_at_position": 12,
                    },
                    "bye_week_analysis": {
                        "bye_week": 12,
                        "bye_week_penalty": 1.0,
                        "conflict_severity": "None",
                        "conflicts_found": [],
                        "helps_bye_diversity": True,
                    },
                },
                {
                    "name": "Cooper Kupp",
                    "position": "WR",
                    "team": "LAR",
                    "bye_week": 10,
                    "average_rank": 15.0,
                    "average_score": 82.1,
                    "value_metrics": {
                        "overall_value": 70.8,
                        "tier": "Tier 1",
                        "tier_rank": 2,
                        "positional_rank": 5,
                    },
                    "scarcity_analysis": {
                        "position_scarcity": "Low",
                        "available_at_position": 30,
                    },
                    "bye_week_analysis": {
                        "bye_week": 10,
                        "bye_week_penalty": 0.75,  # Conflict with Tyreek Hill
                        "conflict_severity": "Medium",
                        "conflicts_found": ["WR starter conflict on bye week 10"],
                        "helps_bye_diversity": False,
                    },
                },
            ],
            "bye_week_analysis": {
                "current_conflicts": {
                    10: {
                        "total_players": 1,
                        "positions_affected": ["WR"],
                        "severity": "Medium",
                    }
                },
                "problematic_weeks": [10],
                "roster_summary": {"WR": 1},
            },
        }

    @pytest.mark.asyncio
    async def test_suggest_basic_functionality(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test basic functionality of suggest_draft_pick"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            # Verify basic structure
            assert result["success"] is True
            assert "recommendation" in result
            assert "analysis" in result
            assert "roster_analysis" in result
            assert "strategic_guidance" in result
            assert "confidence_factors" in result

            # Verify recommendation structure
            recommendation = result["recommendation"]
            assert "primary_pick" in recommendation
            assert "alternatives" in recommendation
            assert recommendation["strategy_used"] == "balanced"  # default

            # Verify primary pick has required fields
            primary_pick = recommendation["primary_pick"]
            assert "name" in primary_pick
            assert "position" in primary_pick
            assert "strategy_score" in primary_pick
            assert "detailed_reasoning" in primary_pick

    @pytest.mark.asyncio
    async def test_strategy_balanced(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test balanced strategy prioritizes roster needs + value"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", strategy="balanced"
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]

            # Should favor RB (roster need) over QB (no immediate need)
            # Since we only have 1 WR and need RBs
            assert primary_pick["position"] == "RB"
            assert primary_pick["name"] == "Derrick Henry"

            # Check reasoning mentions roster balance
            reasoning = primary_pick["detailed_reasoning"]
            reasoning_text = " ".join(reasoning)
            assert (
                "balance" in reasoning_text.lower() or "need" in reasoning_text.lower()
            )

    @pytest.mark.asyncio
    async def test_strategy_best_available(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test best available strategy prioritizes pure value"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", strategy="best_available"
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]

            # Should provide a valid recommendation with value-based reasoning
            assert "name" in primary_pick
            assert "position" in primary_pick
            assert "value_metrics" in primary_pick

            # Check reasoning mentions best available strategy
            reasoning = primary_pick["detailed_reasoning"]
            reasoning_text = " ".join(reasoning).lower()
            assert (
                "best available" in reasoning_text
                or "value" in reasoning_text
                or "elite" in reasoning_text
            )

    @pytest.mark.asyncio
    async def test_strategy_upside(self, sample_draft_state, sample_analysis_response):
        """Test upside strategy in different rounds"""

        # Early round upside
        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", strategy="upside"
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]

            # Early round upside should provide valid recommendation with upside reasoning
            assert "name" in primary_pick
            assert "position" in primary_pick
            assert "value_metrics" in primary_pick

            reasoning = primary_pick["detailed_reasoning"]
            reasoning_text = " ".join(reasoning).lower()
            assert (
                "upside" in reasoning_text
                or "ceiling" in reasoning_text
                or "potential" in reasoning_text
            )

    @pytest.mark.asyncio
    async def test_strategy_safe(self, sample_draft_state, sample_analysis_response):
        """Test safe strategy prioritizes consistency"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", strategy="safe"
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]

            # Safe strategy should provide valid recommendation with safety reasoning
            assert "name" in primary_pick
            assert "position" in primary_pick
            assert "value_metrics" in primary_pick

            reasoning = primary_pick["detailed_reasoning"]
            reasoning_text = " ".join(reasoning).lower()
            assert (
                "safe" in reasoning_text
                or "reliable" in reasoning_text
                or "consistent" in reasoning_text
                or "floor" in reasoning_text
            )

    @pytest.mark.asyncio
    async def test_bye_week_consideration(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test bye week conflicts are properly considered"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            # Test with bye week consideration (default)
            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", consider_bye_weeks=True
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]

            # Should avoid Cooper Kupp due to bye week conflict with Tyreek Hill (both week 10)
            # Derrick Henry (week 14) or Josh Allen (week 12) should be preferred
            assert primary_pick["name"] in ["Derrick Henry", "Josh Allen"]
            assert primary_pick["name"] != "Cooper Kupp"

            # Test without bye week consideration
            result_no_bye = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", consider_bye_weeks=False
            )

            assert result_no_bye["success"] is True
            # Should potentially consider Cooper Kupp now

    @pytest.mark.asyncio
    async def test_roster_needs_analysis(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test roster needs are properly analyzed"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is True
            roster_analysis = result["roster_analysis"]

            # Verify roster analysis structure
            assert "position_needs" in roster_analysis
            assert "current_roster" in roster_analysis
            assert "roster_balance_score" in roster_analysis

            position_needs = roster_analysis["position_needs"]

            # Should show critical need for all positions (roster appears empty)
            assert (
                position_needs["RB"]["urgency"] == "Critical"
            )  # Need 2 starters, have 0
            assert (
                position_needs["QB"]["urgency"] == "Critical"
            )  # Need 1 starter, have 0
            assert (
                position_needs["WR"]["urgency"] == "High"
            )  # Need 1 more starter, have Tyreek Hill
            assert (
                position_needs["TE"]["urgency"] == "Critical"
            )  # Need 1 starter, have 0

    @pytest.mark.asyncio
    async def test_round_specific_guidance(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test round-specific strategic guidance"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            # Test auction round guidance
            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )  # Round 2 = auction

            assert result["success"] is True
            guidance = result["strategic_guidance"]["round_guidance"]

            assert guidance["round_type"] == "auction"
            assert "target specific players" in guidance["key_focus"].lower()
            assert any(
                "elite talent" in note.lower() for note in guidance["strategy_notes"]
            )

            # Test snake round guidance
            snake_draft_state = sample_draft_state.copy()
            snake_draft_state["draft_state"]["current_round"] = 6
            sample_analysis_response["analysis"]["current_round"] = 6

            result_snake = await suggest_draft_pick(
                snake_draft_state, owner_name="Test Owner"
            )

            assert result_snake["success"] is True
            guidance_snake = result_snake["strategic_guidance"]["round_guidance"]

            assert guidance_snake["round_type"] == "early_snake"
            assert any(
                "rb/wr scarcity" in note.lower()
                for note in guidance_snake["strategy_notes"]
            )

    @pytest.mark.asyncio
    async def test_position_specific_recommendations(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test position-specific recommendations"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is True
            position_recs = result["strategic_guidance"]["position_recommendations"]

            # Should have recommendations for major positions
            assert len(position_recs) >= 3  # At least QB, RB, WR

            # Check that each position recommendation has proper structure
            for position, pos_rec in position_recs.items():
                assert position in [
                    "QB",
                    "RB",
                    "WR",
                    "TE",
                    "K",
                    "DST",
                ]  # Valid positions
                assert "urgency" in pos_rec
                assert "current_count" in pos_rec
                assert "top_available" in pos_rec
                assert "recommendation" in pos_rec

                # Top available should have required fields if present
                if pos_rec["top_available"]:
                    top = pos_rec["top_available"][0]
                    assert "name" in top
                    assert "rank" in top
                    assert "tier" in top
                    assert "value" in top

    @pytest.mark.asyncio
    async def test_confidence_factors(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test confidence factor calculations"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is True
            confidence = result["confidence_factors"]

            # Verify confidence factors structure
            assert "high_confidence" in confidence
            assert "clear_best_pick" in confidence
            assert "positional_need_urgent" in confidence
            assert "bye_week_conflicts" in confidence

            # All should be boolean values
            for factor in confidence.values():
                assert isinstance(factor, bool)

            # Should show urgent positional needs (we have critical gaps)
            assert confidence["positional_need_urgent"] is True

            # Should show bye week conflicts (week 10 conflict exists)
            assert confidence["bye_week_conflicts"] is True

    @pytest.mark.asyncio
    async def test_invalid_strategy(self, sample_draft_state):
        """Test handling of invalid strategy parameter"""

        result = await suggest_draft_pick(
            sample_draft_state, owner_name="Test Owner", strategy="invalid_strategy"
        )

        assert result["success"] is False
        assert "Invalid strategy" in result["error"]
        assert "balanced, best_available, upside, safe" in result["error"]

    @pytest.mark.asyncio
    async def test_analysis_failure_handling(self, sample_draft_state):
        """Test handling when player analysis fails"""

        failed_analysis = {"success": False, "error": "Failed to analyze players"}

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = failed_analysis

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is False
            assert "Failed to analyze available players" in result["error"]
            assert "analysis_error" in result

    @pytest.mark.asyncio
    async def test_no_available_players(self, sample_draft_state):
        """Test handling when no players are available"""

        empty_analysis = {
            "success": True,
            "players": [],
            "analysis": {"current_round": 2, "round_type": "auction"},
        }

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = empty_analysis

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is False
            assert "No available players found" in result["error"]

    @pytest.mark.asyncio
    async def test_alternatives_generation(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test that alternatives are properly generated"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is True
            alternatives = result["recommendation"]["alternatives"]

            # Should have alternatives (up to 3)
            assert len(alternatives) > 0
            assert len(alternatives) <= 3

            # Each alternative should have detailed reasoning
            for alt in alternatives:
                assert "detailed_reasoning" in alt
                assert "strategy_score" in alt

                reasoning = alt["detailed_reasoning"]
                reasoning_text = " ".join(reasoning)
                assert "alternative" in reasoning_text.lower()

    @pytest.mark.asyncio
    async def test_detailed_reasoning_generation(
        self, sample_draft_state, sample_analysis_response
    ):
        """Test detailed reasoning generation"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = sample_analysis_response

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner", strategy="balanced"
            )

            assert result["success"] is True
            primary_pick = result["recommendation"]["primary_pick"]
            reasoning = primary_pick["detailed_reasoning"]

            # Should be a list of strings
            assert isinstance(reasoning, list)
            assert len(reasoning) > 0

            # Should contain key reasoning elements
            reasoning_text = " ".join(reasoning).lower()

            # Should mention the player and position
            assert primary_pick["name"].lower() in reasoning_text
            assert primary_pick["position"].lower() in reasoning_text

            # Should contain strategy-relevant reasoning
            if "critical need" in reasoning_text:
                assert "0" in reasoning_text or "need starters" in reasoning_text

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_draft_state):
        """Test general error handling"""

        with patch(
            "tools.mcp_tools.analyze_available_players", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.side_effect = Exception("Unexpected error")

            result = await suggest_draft_pick(
                sample_draft_state, owner_name="Test Owner"
            )

            assert result["success"] is False
            assert "error" in result
            assert "error_type" in result
            assert result["error_type"] == "suggestion_failed"
            assert "troubleshooting" in result


if __name__ == "__main__":
    pytest.main([__file__])
