import pytest

from src.models.draft_state import Team
from src.models.player import InjuryStatus, Player, Position
from src.models.roster_rules import RosterRules


class TestRosterRules:
    @pytest.fixture
    def default_rules(self):
        """Default fantasy football roster rules"""
        return RosterRules()

    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing"""
        players = {
            'qb1': Player("Josh Allen", Position.QB, "BUF", 13),
            'qb2': Player("Lamar Jackson", Position.QB, "BAL", 13),
            'rb1': Player("Christian McCaffrey", Position.RB, "SF", 9),
            'rb2': Player("Austin Ekeler", Position.RB, "LAC", 5),
            'rb3': Player("Derrick Henry", Position.RB, "TEN", 6),
            'wr1': Player("Tyreek Hill", Position.WR, "MIA", 10),
            'wr2': Player("Stefon Diggs", Position.WR, "BUF", 13),
            'wr3': Player("CeeDee Lamb", Position.WR, "DAL", 7),
            'te1': Player("Travis Kelce", Position.TE, "KC", 10),
            'te2': Player("Mark Andrews", Position.TE, "BAL", 13),
            'k1': Player("Justin Tucker", Position.K, "BAL", 13),
            'dst1': Player("49ers D/ST", Position.DST, "SF", 9),
        }
        return players

    def test_roster_rules_initialization(self, default_rules):
        """Test RosterRules initializes with correct defaults"""
        assert default_rules.starter_requirements[Position.QB] == 1
        assert default_rules.starter_requirements[Position.RB] == 2
        assert default_rules.starter_requirements[Position.WR] == 2
        assert default_rules.starter_requirements[Position.TE] == 1
        assert default_rules.starter_requirements[Position.FLEX] == 1
        assert default_rules.starter_requirements[Position.K] == 1
        assert default_rules.starter_requirements[Position.DST] == 1

        assert default_rules.roster_limits[Position.QB] == 4
        assert default_rules.roster_limits[Position.RB] == 8
        assert default_rules.roster_limits[Position.WR] == 8
        assert default_rules.roster_limits[Position.TE] == 4
        assert default_rules.roster_limits[Position.K] == 3
        assert default_rules.roster_limits[Position.DST] == 3

        assert default_rules.bench_slots == 10
        assert default_rules.ir_slots == 2
        assert default_rules.max_roster_size == 19  # 9 starters (1+2+2+1+1+1+1) + 10 bench

    def test_get_flex_eligible_positions(self, default_rules):
        """Test FLEX eligible positions"""
        flex_positions = default_rules.get_flex_eligible_positions()
        assert Position.RB in flex_positions
        assert Position.WR in flex_positions
        assert Position.TE in flex_positions
        assert Position.QB not in flex_positions
        assert Position.K not in flex_positions
        assert Position.DST not in flex_positions




class TestRosterValidation:
    @pytest.fixture
    def default_rules(self):
        return RosterRules()

    @pytest.fixture
    def sample_team(self, sample_players):
        """Create a team with sample roster"""
        team = Team("Test Team", 1)
        # Add a balanced roster
        team.add_player(sample_players['qb1'])
        team.add_player(sample_players['rb1'])
        team.add_player(sample_players['rb2'])
        team.add_player(sample_players['wr1'])
        team.add_player(sample_players['wr2'])
        team.add_player(sample_players['te1'])
        team.add_player(sample_players['k1'])
        team.add_player(sample_players['dst1'])
        return team

    def test_is_roster_legal_valid_team(self, default_rules, sample_team):
        """Test valid roster passes legal check"""
        result = default_rules.is_roster_legal(sample_team)
        assert result.is_valid
        assert len(result.violations) == 0

    def test_is_roster_legal_exceeds_position_limit(self, default_rules, sample_team, sample_players):
        """Test roster fails when exceeding position limits"""
        # Add 4 more QBs to exceed limit of 4
        for i in range(5):
            qb = Player(f"QB{i+2}", Position.QB, "TEAM", 1)
            sample_team.add_player(qb)

        result = default_rules.is_roster_legal(sample_team)
        assert not result.is_valid
        assert any("QB" in v and "limit" in v.lower() for v in result.violations)

    def test_is_roster_legal_exceeds_total_size(self, default_rules, sample_team):
        """Test roster fails when exceeding total roster size"""
        # Add many bench players to exceed roster size
        for i in range(15):  # This will exceed the 18-player limit
            player = Player(f"Bench{i}", Position.RB, "TEAM", 1)
            sample_team.add_player(player)

        result = default_rules.is_roster_legal(sample_team)
        assert not result.is_valid
        assert any("roster size" in v.lower() for v in result.violations)

    def test_is_roster_legal_with_injured_players(self, default_rules, sample_team):
        """Test roster handles injured players correctly"""
        # Add injured players to IR slots
        injured1 = Player("Injured RB", Position.RB, "TEAM", 1)
        injured1.update_injury_status(InjuryStatus.OUT)
        injured2 = Player("Injured WR", Position.WR, "TEAM", 1)
        injured2.update_injury_status(InjuryStatus.OUT)

        sample_team.add_player(injured1)
        sample_team.add_player(injured2)

        result = default_rules.is_roster_legal(sample_team, ir_slots_used=2)
        assert result.is_valid


class TestPositionNeeds:
    @pytest.fixture
    def default_rules(self):
        return RosterRules()

    def test_get_position_needs_empty_team(self, default_rules):
        """Test position needs for empty team"""
        empty_team = Team("Empty", 1)
        needs = default_rules.get_position_needs(empty_team)

        assert needs[Position.QB] == 1  # Need 1 QB starter
        assert needs[Position.RB] == 2  # Need 2 RB starters
        assert needs[Position.WR] == 2  # Need 2 WR starters
        assert needs[Position.TE] == 1  # Need 1 TE starter
        assert needs[Position.FLEX] == 1  # Need 1 FLEX starter
        assert needs[Position.K] == 1   # Need 1 K starter
        assert needs[Position.DST] == 1 # Need 1 DST starter

    def test_get_position_needs_partial_team(self, default_rules, sample_players):
        """Test position needs for partially filled team"""
        team = Team("Partial", 1)
        team.add_player(sample_players['qb1'])
        team.add_player(sample_players['rb1'])
        team.add_player(sample_players['wr1'])

        needs = default_rules.get_position_needs(team)

        assert needs[Position.QB] == 0  # QB filled
        assert needs[Position.RB] == 1  # Need 1 more RB
        assert needs[Position.WR] == 1  # Need 1 more WR
        assert needs[Position.TE] == 1  # Still need TE
        assert needs[Position.FLEX] == 1  # Still need FLEX

    def test_get_position_needs_considers_flex_depth(self, default_rules, sample_players):
        """Test position needs considers FLEX depth requirements"""
        team = Team("FlexDepth", 1)
        # Add minimum starters
        team.add_player(sample_players['qb1'])
        team.add_player(sample_players['rb1'])
        team.add_player(sample_players['rb2'])  # 2 RBs for starters
        team.add_player(sample_players['wr1'])
        team.add_player(sample_players['wr2'])  # 2 WRs for starters
        team.add_player(sample_players['te1'])
        team.add_player(sample_players['k1'])
        team.add_player(sample_players['dst1'])
        # No FLEX player yet

        needs = default_rules.get_position_needs(team, consider_flex_depth=True)

        # Should still need RB/WR/TE for FLEX position
        assert needs[Position.FLEX] == 1
        # Should recommend additional flex-eligible players
        flex_needs = needs.get('flex_depth', 0)
        assert flex_needs > 0


class TestFlexEligibility:
    @pytest.fixture
    def default_rules(self):
        return RosterRules()

    def test_calculate_flex_eligibility_basic(self, default_rules, sample_players):
        """Test basic FLEX eligibility calculation"""
        team = Team("FlexTest", 1)
        team.add_player(sample_players['rb1'])
        team.add_player(sample_players['rb2'])
        team.add_player(sample_players['rb3'])
        team.add_player(sample_players['wr1'])
        team.add_player(sample_players['wr2'])
        team.add_player(sample_players['te1'])

        eligibility = default_rules.calculate_flex_eligibility(team)

        assert len(eligibility.eligible_players) == 6  # 3 RBs + 2 WRs + 1 TE
        assert eligibility.rb_options == 3
        assert eligibility.wr_options == 2
        assert eligibility.te_options == 1

    def test_calculate_flex_eligibility_excludes_starters(self, default_rules, sample_players):
        """Test FLEX eligibility excludes already assigned starters"""
        team = Team("FlexTest", 1)
        team.add_player(sample_players['rb1'])
        team.add_player(sample_players['rb2'])
        team.add_player(sample_players['rb3'])
        team.add_player(sample_players['wr1'])
        team.add_player(sample_players['wr2'])

        # Simulate lineup where rb1, rb2 are RB starters, wr1, wr2 are WR starters
        current_lineup = {
            Position.RB: [sample_players['rb1'], sample_players['rb2']],
            Position.WR: [sample_players['wr1'], sample_players['wr2']],
        }

        eligibility = default_rules.calculate_flex_eligibility(
            team,
            exclude_starters=current_lineup
        )

        # Only rb3 should be available for FLEX
        assert len(eligibility.eligible_players) == 1
        assert eligibility.eligible_players[0] == sample_players['rb3']

    def test_calculate_flex_eligibility_empty_team(self, default_rules):
        """Test FLEX eligibility for empty team"""
        empty_team = Team("Empty", 1)
        eligibility = default_rules.calculate_flex_eligibility(empty_team)

        assert len(eligibility.eligible_players) == 0
        assert eligibility.rb_options == 0
        assert eligibility.wr_options == 0
        assert eligibility.te_options == 0


class TestRosterLimits:
    @pytest.fixture
    def default_rules(self):
        return RosterRules()

    def test_get_roster_limits_default(self, default_rules):
        """Test default roster limits"""
        limits = default_rules.get_roster_limits()

        assert limits[Position.QB] == 4
        assert limits[Position.RB] == 8
        assert limits[Position.WR] == 8
        assert limits[Position.TE] == 4
        assert limits[Position.K] == 3
        assert limits[Position.DST] == 3
        # FLEX has no roster limit (can be filled by RB/WR/TE)
        assert Position.FLEX not in limits

    def test_get_remaining_slots(self, default_rules, sample_players):
        """Test remaining roster slots calculation"""
        team = Team("Test", 1)
        team.add_player(sample_players['qb1'])  # 1 QB
        team.add_player(sample_players['rb1'])  # 1 RB
        team.add_player(sample_players['rb2'])  # 2 RBs total

        remaining = default_rules.get_remaining_slots(team)

        assert remaining[Position.QB] == 3  # 4 - 1 = 3
        assert remaining[Position.RB] == 6  # 8 - 2 = 6
        assert remaining[Position.WR] == 8  # 8 - 0 = 8
        assert remaining[Position.TE] == 4  # 4 - 0 = 4

    def test_is_at_position_limit(self, default_rules, sample_players):
        """Test position limit checking"""
        team = Team("LimitTest", 1)

        # Add maximum QBs (4)
        for i in range(4):
            qb = Player(f"QB{i+1}", Position.QB, f"T{i+1}", 1)
            team.add_player(qb)

        assert default_rules.is_at_position_limit(team, Position.QB)
        assert not default_rules.is_at_position_limit(team, Position.RB)

        # Test adding one more QB would exceed limit
        qb5 = Player("QB5", Position.QB, "T5", 1)
        assert default_rules.would_exceed_limit(team, qb5)


class TestCustomRosterRules:
    def test_custom_roster_rules_initialization(self):
        """Test custom roster rules"""
        custom_rules = RosterRules(
            starter_requirements={
                Position.QB: 2,  # Superflex league
                Position.RB: 2,
                Position.WR: 3,  # 3 WR league
                Position.TE: 1,
                Position.FLEX: 1,
                Position.K: 1,
                Position.DST: 1,
            },
            roster_limits={
                Position.QB: 6,  # Higher QB limit for superflex
                Position.RB: 10,
                Position.WR: 10,
                Position.TE: 6,
                Position.K: 2,
                Position.DST: 2,
            },
            bench_slots=12,
            ir_slots=3
        )

        assert custom_rules.starter_requirements[Position.QB] == 2
        assert custom_rules.starter_requirements[Position.WR] == 3
        assert custom_rules.roster_limits[Position.QB] == 6
        assert custom_rules.bench_slots == 12
        assert custom_rules.ir_slots == 3


class TestEdgeCases:
    @pytest.fixture
    def default_rules(self):
        return RosterRules()

    def test_exactly_at_limits(self, default_rules, sample_players):
        """Test team exactly at roster limits"""
        team = Team("MaxTeam", 1)

        # Add exactly 4 QBs (the limit)
        for i in range(4):
            qb = Player(f"QB{i+1}", Position.QB, f"T{i+1}", 1)
            team.add_player(qb)

        # Add exactly 8 RBs (the limit)
        for i in range(8):
            rb = Player(f"RB{i+1}", Position.RB, f"T{i+1}", 1)
            team.add_player(rb)

        # Add other positions to stay under roster limit
        team.add_player(sample_players['wr1'])
        team.add_player(sample_players['te1'])
        team.add_player(sample_players['k1'])
        team.add_player(sample_players['dst1'])

        result = default_rules.is_roster_legal(team)
        assert result.is_valid

        # Verify we're at limits
        assert default_rules.is_at_position_limit(team, Position.QB)
        assert default_rules.is_at_position_limit(team, Position.RB)

    def test_flex_optimization_scenarios(self, default_rules, sample_players):
        """Test FLEX optimization in various scenarios"""
        team = Team("FlexOpt", 1)

        # Scenario 1: Heavy RB roster
        team.roster = [
            sample_players['qb1'],
            sample_players['rb1'], sample_players['rb2'], sample_players['rb3'],
            Player("RB4", Position.RB, "T4", 1), Player("RB5", Position.RB, "T5", 1),
            sample_players['wr1'], sample_players['wr2'],
            sample_players['te1'],
            sample_players['k1'], sample_players['dst1']
        ]

        eligibility = default_rules.calculate_flex_eligibility(team)
        assert eligibility.rb_options == 5  # 5 RBs available

        # Scenario 2: Balanced roster
        team.roster = [
            sample_players['qb1'],
            sample_players['rb1'], sample_players['rb2'],
            sample_players['wr1'], sample_players['wr2'], sample_players['wr3'],
            sample_players['te1'], sample_players['te2'],
            sample_players['k1'], sample_players['dst1']
        ]

        eligibility = default_rules.calculate_flex_eligibility(team)
        assert eligibility.rb_options == 2
        assert eligibility.wr_options == 3
        assert eligibility.te_options == 2

    def test_invalid_roster_configurations(self, default_rules):
        """Test various invalid roster configurations"""
        # Test roster exceeding total size limit
        oversized_team = Team("Oversized", 1)

        # Add too many players (over the 19-player limit)
        for i in range(25):  # Way over limit
            player = Player(f"Player{i}", Position.RB, "TEAM", 1)
            oversized_team.add_player(player)

        result = default_rules.is_roster_legal(oversized_team)
        assert not result.is_valid
        assert any("roster size" in v.lower() for v in result.violations)


# Add the fixture to the test file
@pytest.fixture
def sample_players():
    """Create sample players for testing"""
    players = {
        'qb1': Player("Josh Allen", Position.QB, "BUF", 13),
        'qb2': Player("Lamar Jackson", Position.QB, "BAL", 13),
        'rb1': Player("Christian McCaffrey", Position.RB, "SF", 9),
        'rb2': Player("Austin Ekeler", Position.RB, "LAC", 5),
        'rb3': Player("Derrick Henry", Position.RB, "TEN", 6),
        'wr1': Player("Tyreek Hill", Position.WR, "MIA", 10),
        'wr2': Player("Stefon Diggs", Position.WR, "BUF", 13),
        'wr3': Player("CeeDee Lamb", Position.WR, "DAL", 7),
        'te1': Player("Travis Kelce", Position.TE, "KC", 10),
        'te2': Player("Mark Andrews", Position.TE, "BAL", 13),
        'k1': Player("Justin Tucker", Position.K, "BAL", 13),
        'dst1': Player("49ers D/ST", Position.DST, "SF", 9),
    }
    return players
