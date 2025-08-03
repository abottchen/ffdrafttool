import pytest

from src.models.draft_state import Team
from src.models.player import Player, Position, RankingSource
from src.models.roster_rules import RosterRules
from src.models.team_analysis import TeamAnalysis


class TestDraftStrategyAdvice:
    @pytest.fixture
    def roster_rules(self):
        return RosterRules()

    @pytest.fixture
    def team_analysis(self, roster_rules):
        return TeamAnalysis(roster_rules=roster_rules, num_teams=12)

    @pytest.fixture
    def early_draft_team(self):
        """Team with just a few early picks"""
        team = Team("Early Team", 1)
        team.add_player(Player("Elite RB", Position.RB, "SF", 9))
        team.add_player(Player("Elite WR", Position.WR, "MIA", 10))
        return team

    @pytest.fixture
    def mid_draft_team(self):
        """Team in middle of draft"""
        team = Team("Mid Team", 1)
        team.add_player(Player("QB1", Position.QB, "BUF", 13))
        team.add_player(Player("RB1", Position.RB, "SF", 9))
        team.add_player(Player("RB2", Position.RB, "LAC", 5))
        team.add_player(Player("WR1", Position.WR, "MIA", 10))
        team.add_player(Player("WR2", Position.WR, "BUF", 13))
        team.add_player(Player("TE1", Position.TE, "KC", 10))
        return team

    @pytest.fixture
    def late_draft_team(self):
        """Team near end of draft"""
        team = Team("Late Team", 1)
        # Add full starting lineup
        team.add_player(Player("QB1", Position.QB, "BUF", 13))
        team.add_player(Player("RB1", Position.RB, "SF", 9))
        team.add_player(Player("RB2", Position.RB, "LAC", 5))
        team.add_player(Player("RB3", Position.RB, "MIN", 13))
        team.add_player(Player("WR1", Position.WR, "MIA", 10))
        team.add_player(Player("WR2", Position.WR, "BUF", 13))
        team.add_player(Player("WR3", Position.WR, "DAL", 7))
        team.add_player(Player("TE1", Position.TE, "KC", 10))
        team.add_player(Player("TE2", Position.TE, "BAL", 13))
        # Missing K and DST
        return team

    @pytest.fixture
    def sample_available_players(self):
        """Available players for draft analysis"""
        players = []
        positions = [
            Position.QB,
            Position.RB,
            Position.WR,
            Position.TE,
            Position.K,
            Position.DST,
        ]

        for pos in positions:
            for i in range(10):
                player = Player(f"{pos.value}{i+1}", pos, f"T{i+1}", (i % 14) + 1)
                player.add_ranking(RankingSource.ESPN, i + 1, 95 - i)
                players.append(player)

        return players

    def test_early_round_strategy_advice(
        self, team_analysis, early_draft_team, sample_available_players
    ):
        """Test strategy advice for early rounds"""
        advice = team_analysis.get_draft_strategy_advice(
            early_draft_team, sample_available_players, current_round=3, total_rounds=15
        )

        # Should have primary needs
        assert len(advice["primary_needs"]) > 0

        # Should mention early round strategy
        strategy_text = " ".join(advice["strategy_notes"])
        assert "early" in strategy_text.lower()

        # Should have FLEX analysis
        assert "flex_analysis" in advice
        assert advice["flex_analysis"]["total_flex_options"] >= 0

    def test_position_limit_warnings(self, team_analysis, roster_rules):
        """Test warnings when approaching position limits"""
        # Create team at QB limit
        team = Team("Limit Team", 1)
        for i in range(4):  # Max QB limit
            team.add_player(Player(f"QB{i+1}", Position.QB, f"T{i+1}", 1))

        advice = team_analysis.get_draft_strategy_advice(
            team, [], current_round=8, total_rounds=15
        )

        # Should warn about being at QB limit
        warning_text = " ".join(advice["warnings"])
        assert "QB" in warning_text and "limit" in warning_text

    def test_flex_depth_analysis(self, team_analysis, sample_available_players):
        """Test FLEX depth analysis"""
        # Team with limited FLEX options
        team = Team("Limited Flex", 1)
        team.add_player(Player("QB1", Position.QB, "BUF", 13))
        team.add_player(Player("RB1", Position.RB, "SF", 9))
        team.add_player(Player("RB2", Position.RB, "LAC", 5))  # Only 2 RBs
        team.add_player(Player("WR1", Position.WR, "MIA", 10))  # Only 1 WR
        team.add_player(Player("TE1", Position.TE, "KC", 10))  # Only 1 TE

        advice = team_analysis.get_draft_strategy_advice(
            team, sample_available_players, current_round=6, total_rounds=15
        )

        # Should recommend FLEX depth or show in primary needs
        opportunities_text = " ".join(advice["opportunities"])
        primary_needs_text = " ".join(advice["primary_needs"])

        assert (
            "flex" in opportunities_text.lower()
            or "depth" in opportunities_text.lower()
            or "flex" in primary_needs_text.lower()
        )

        # FLEX analysis should show limited options
        assert advice["flex_analysis"]["total_flex_options"] <= 4

    def test_late_round_strategy(
        self, team_analysis, late_draft_team, sample_available_players
    ):
        """Test strategy advice for late rounds"""
        advice = team_analysis.get_draft_strategy_advice(
            late_draft_team, sample_available_players, current_round=14, total_rounds=15
        )

        # Should mention kicker and defense
        strategy_text = " ".join(advice["strategy_notes"])
        assert "kicker" in strategy_text.lower() or "defense" in strategy_text.lower()

    def test_bye_week_warnings(self, team_analysis, sample_available_players):
        """Test bye week conflict warnings"""
        # Team with many players on same bye week
        team = Team("Bye Week Issues", 1)
        bye_week = 9

        # Add multiple players with same bye week
        team.add_player(Player("QB1", Position.QB, "BUF", bye_week))
        team.add_player(Player("RB1", Position.RB, "SF", bye_week))
        team.add_player(Player("WR1", Position.WR, "MIA", bye_week))
        team.add_player(Player("TE1", Position.TE, "KC", bye_week))

        advice = team_analysis.get_draft_strategy_advice(
            team, sample_available_players, current_round=8, total_rounds=15
        )

        # Should warn about bye week conflicts
        warnings_text = " ".join(advice["warnings"])
        assert "bye" in warnings_text.lower()

    def test_qb_urgency_warning(self, team_analysis, sample_available_players):
        """Test QB urgency warning in late rounds without QB"""
        # Team without QB in late rounds
        team = Team("No QB Team", 1)
        team.add_player(Player("RB1", Position.RB, "SF", 9))
        team.add_player(Player("WR1", Position.WR, "MIA", 10))
        team.add_player(Player("WR2", Position.WR, "BUF", 13))

        advice = team_analysis.get_draft_strategy_advice(
            team,
            sample_available_players,
            current_round=8,  # Late for no QB
            total_rounds=15,
        )

        # Should warn about QB urgency
        warnings_text = " ".join(advice["warnings"])
        assert "qb" in warnings_text.lower() and "urgent" in warnings_text.lower()

    def test_balanced_team_advice(
        self, team_analysis, mid_draft_team, sample_available_players
    ):
        """Test advice for well-balanced team"""
        # Add more players to make team more balanced
        mid_draft_team.add_player(Player("RB3", Position.RB, "MIN", 13))
        mid_draft_team.add_player(Player("WR3", Position.WR, "DAL", 7))

        advice = team_analysis.get_draft_strategy_advice(
            mid_draft_team, sample_available_players, current_round=8, total_rounds=15
        )

        # Should show good FLEX depth
        flex_total = advice["flex_analysis"]["total_flex_options"]
        assert flex_total >= 4  # Should have good depth

        # Should have fewer high-priority needs (excluding K/DST which are always needed late)
        skill_position_needs = [
            n
            for n in advice["primary_needs"]
            if "starting lineup" in n and not any(pos in n for pos in ["K", "DST"])
        ]
        assert len(skill_position_needs) <= 2  # Most skill positions filled

    def test_strategy_advice_structure(
        self, team_analysis, early_draft_team, sample_available_players
    ):
        """Test that strategy advice has expected structure"""
        advice = team_analysis.get_draft_strategy_advice(
            early_draft_team, sample_available_players, current_round=5, total_rounds=15
        )

        # Check all expected keys are present
        expected_keys = [
            "primary_needs",
            "warnings",
            "opportunities",
            "position_limits",
            "flex_analysis",
            "strategy_notes",
        ]

        for key in expected_keys:
            assert key in advice

        # Check FLEX analysis structure
        flex_keys = [
            "total_flex_options",
            "rb_depth",
            "wr_depth",
            "te_depth",
            "best_flex_option",
        ]
        for key in flex_keys:
            assert key in advice["flex_analysis"]

    def test_recommendations_based_on_round(
        self, team_analysis, early_draft_team, sample_available_players
    ):
        """Test that recommendations change based on round"""
        # Early round advice
        early_advice = team_analysis.get_draft_strategy_advice(
            early_draft_team, sample_available_players, current_round=2, total_rounds=15
        )

        # Late round advice
        late_advice = team_analysis.get_draft_strategy_advice(
            early_draft_team,
            sample_available_players,
            current_round=13,
            total_rounds=15,
        )

        # Strategy notes should be different
        early_strategy = " ".join(early_advice["strategy_notes"]).lower()
        late_strategy = " ".join(late_advice["strategy_notes"]).lower()

        assert early_strategy != late_strategy
        assert "early" in early_strategy or "elite" in early_strategy
        assert (
            "kicker" in late_strategy
            or "defense" in late_strategy
            or "late" in late_strategy
        )
