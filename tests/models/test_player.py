from src.models.player import InjuryStatus, Player, Position, RankingSource


class TestPlayer:
    def test_player_creation(self):
        player = Player(
            name="Christian McCaffrey", position=Position.RB, team="SF", bye_week=9
        )

        assert player.name == "Christian McCaffrey"
        assert player.position == Position.RB
        assert player.team == "SF"
        assert player.bye_week == 9
        assert player.injury_status == InjuryStatus.HEALTHY
        assert player.rankings == {}

    def test_player_with_injury_status(self):
        player = Player(
            name="Justin Jefferson",
            position=Position.WR,
            team="MIN",
            bye_week=13,
            injury_status=InjuryStatus.QUESTIONABLE,
        )

        assert player.injury_status == InjuryStatus.QUESTIONABLE

    def test_add_ranking(self):
        player = Player(
            name="Josh Allen", position=Position.QB, team="BUF", bye_week=13
        )

        player.add_ranking(RankingSource.ESPN, 3, 98.5)
        player.add_ranking(RankingSource.YAHOO, 2, 99.0)

        assert player.rankings[RankingSource.ESPN] == {"rank": 3, "score": 98.5}
        assert player.rankings[RankingSource.YAHOO] == {"rank": 2, "score": 99.0}

    def test_average_rank(self):
        player = Player(
            name="Tyreek Hill", position=Position.WR, team="MIA", bye_week=10
        )

        player.add_ranking(RankingSource.ESPN, 5, 95.0)
        player.add_ranking(RankingSource.YAHOO, 7, 93.0)
        player.add_ranking(RankingSource.CBS, 6, 94.0)

        assert player.average_rank == 6.0

    def test_average_rank_no_rankings(self):
        player = Player(
            name="Rookie Player", position=Position.RB, team="JAX", bye_week=9
        )

        assert player.average_rank is None

    def test_average_score(self):
        player = Player(
            name="Travis Kelce", position=Position.TE, team="KC", bye_week=10
        )

        player.add_ranking(RankingSource.ESPN, 10, 88.0)
        player.add_ranking(RankingSource.YAHOO, 12, 86.0)

        assert player.average_score == 87.0

    def test_is_injured(self):
        healthy_player = Player(
            name="Healthy Player",
            position=Position.WR,
            team="DAL",
            bye_week=7,
            injury_status=InjuryStatus.HEALTHY,
        )

        injured_player = Player(
            name="Injured Player",
            position=Position.RB,
            team="NYG",
            bye_week=13,
            injury_status=InjuryStatus.OUT,
        )

        assert not healthy_player.has_injury_concern()
        assert injured_player.has_injury_concern()

    def test_player_str_representation(self):
        player = Player(
            name="Stefon Diggs", position=Position.WR, team="BUF", bye_week=13
        )
        player.add_ranking(RankingSource.ESPN, 8, 92.0)

        str_repr = str(player)
        assert "Stefon Diggs" in str_repr
        assert "WR" in str_repr
        assert "BUF" in str_repr

    def test_player_equality(self):
        player1 = Player(
            name="Patrick Mahomes", position=Position.QB, team="KC", bye_week=10
        )

        player2 = Player(
            name="Patrick Mahomes", position=Position.QB, team="KC", bye_week=10
        )

        player3 = Player(
            name="Lamar Jackson", position=Position.QB, team="BAL", bye_week=13
        )

        assert player1 == player2
        assert player1 != player3

    def test_injury_status_assignment(self):
        player = Player(name="Joe Mixon", position=Position.RB, team="CIN", bye_week=7)

        assert player.injury_status == InjuryStatus.HEALTHY

        # Test direct assignment (current interface)
        player.injury_status = InjuryStatus.DOUBTFUL
        assert player.injury_status == InjuryStatus.DOUBTFUL

    def test_string_representation(self):
        player = Player(
            name="CeeDee Lamb",
            position=Position.WR,
            team="DAL",
            bye_week=7,
            injury_status=InjuryStatus.PROBABLE,
        )
        player.add_ranking(RankingSource.ESPN, 4, 96.0)

        player_str = str(player)

        # Test that string representation includes key info
        assert "CeeDee Lamb" in player_str
        assert "WR" in player_str
        assert "DAL" in player_str
        assert "PROBABLE" in player_str
        assert "4.0" in player_str  # Average rank

    def test_dataclass_creation(self):
        # Test direct creation with all fields
        player = Player(
            name="Derrick Henry",
            position=Position.RB,
            team="TEN",
            bye_week=6,
            injury_status=InjuryStatus.HEALTHY
        )

        player.add_ranking(RankingSource.ESPN, 15, 85.0)

        assert player.name == "Derrick Henry"
        assert player.position == Position.RB
        assert player.team == "TEN"
        assert player.bye_week == 6
        assert player.injury_status == InjuryStatus.HEALTHY
        assert RankingSource.ESPN in player.rankings
