from src.models.player import InjuryStatus, Player, Position, RankingSource


class TestPlayer:
    def test_player_creation(self):
        player = Player(
            name="Christian McCaffrey",
            position=Position.RB,
            team="SF",
            bye_week=9
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
            injury_status=InjuryStatus.QUESTIONABLE
        )

        assert player.injury_status == InjuryStatus.QUESTIONABLE

    def test_add_ranking(self):
        player = Player(
            name="Josh Allen",
            position=Position.QB,
            team="BUF",
            bye_week=13
        )

        player.add_ranking(RankingSource.ESPN, 3, 98.5)
        player.add_ranking(RankingSource.YAHOO, 2, 99.0)

        assert player.rankings[RankingSource.ESPN] == {"rank": 3, "score": 98.5}
        assert player.rankings[RankingSource.YAHOO] == {"rank": 2, "score": 99.0}

    def test_average_rank(self):
        player = Player(
            name="Tyreek Hill",
            position=Position.WR,
            team="MIA",
            bye_week=10
        )

        player.add_ranking(RankingSource.ESPN, 5, 95.0)
        player.add_ranking(RankingSource.YAHOO, 7, 93.0)
        player.add_ranking(RankingSource.CBS, 6, 94.0)

        assert player.average_rank == 6.0

    def test_average_rank_no_rankings(self):
        player = Player(
            name="Rookie Player",
            position=Position.RB,
            team="JAX",
            bye_week=9
        )

        assert player.average_rank is None

    def test_average_score(self):
        player = Player(
            name="Travis Kelce",
            position=Position.TE,
            team="KC",
            bye_week=10
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
            injury_status=InjuryStatus.HEALTHY
        )

        injured_player = Player(
            name="Injured Player",
            position=Position.RB,
            team="NYG",
            bye_week=13,
            injury_status=InjuryStatus.OUT
        )

        assert not healthy_player.is_injured
        assert injured_player.is_injured

    def test_player_str_representation(self):
        player = Player(
            name="Stefon Diggs",
            position=Position.WR,
            team="BUF",
            bye_week=13
        )
        player.add_ranking(RankingSource.ESPN, 8, 92.0)

        str_repr = str(player)
        assert "Stefon Diggs" in str_repr
        assert "WR" in str_repr
        assert "BUF" in str_repr

    def test_player_equality(self):
        player1 = Player(
            name="Patrick Mahomes",
            position=Position.QB,
            team="KC",
            bye_week=10
        )

        player2 = Player(
            name="Patrick Mahomes",
            position=Position.QB,
            team="KC",
            bye_week=10
        )

        player3 = Player(
            name="Lamar Jackson",
            position=Position.QB,
            team="BAL",
            bye_week=13
        )

        assert player1 == player2
        assert player1 != player3

    def test_update_injury_status(self):
        player = Player(
            name="Joe Mixon",
            position=Position.RB,
            team="CIN",
            bye_week=7
        )

        assert player.injury_status == InjuryStatus.HEALTHY

        player.update_injury_status(InjuryStatus.DOUBTFUL)
        assert player.injury_status == InjuryStatus.DOUBTFUL

    def test_to_dict(self):
        player = Player(
            name="CeeDee Lamb",
            position=Position.WR,
            team="DAL",
            bye_week=7,
            injury_status=InjuryStatus.PROBABLE
        )
        player.add_ranking(RankingSource.ESPN, 4, 96.0)

        player_dict = player.to_dict()

        assert player_dict["name"] == "CeeDee Lamb"
        assert player_dict["position"] == "WR"
        assert player_dict["team"] == "DAL"
        assert player_dict["bye_week"] == 7
        assert player_dict["injury_status"] == "PROBABLE"
        assert RankingSource.ESPN.value in player_dict["rankings"]

    def test_from_dict(self):
        player_data = {
            "name": "Derrick Henry",
            "position": "RB",
            "team": "TEN",
            "bye_week": 6,
            "injury_status": "HEALTHY",
            "rankings": {
                "ESPN": {"rank": 15, "score": 85.0}
            }
        }

        player = Player.from_dict(player_data)

        assert player.name == "Derrick Henry"
        assert player.position == Position.RB
        assert player.team == "TEN"
        assert player.bye_week == 6
        assert player.injury_status == InjuryStatus.HEALTHY
        assert RankingSource.ESPN in player.rankings
