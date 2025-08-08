"""Tests for the simplified Player model."""

from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player


class TestPlayer:
    def test_player_creation(self):
        """Test creating a player with all fields."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            injury_status=InjuryStatus.HEALTHY,
            ranking=1,
            projected_points=325.5,
            notes="Elite dual-threat QB with rushing upside"
        )

        assert player.name == "Josh Allen"
        assert player.team == "BUF"
        assert player.position == "QB"
        assert player.bye_week == 12
        assert player.injury_status == InjuryStatus.HEALTHY
        assert player.ranking == 1
        assert player.projected_points == 325.5
        assert player.notes == "Elite dual-threat QB with rushing upside"

    def test_player_creation_with_defaults(self):
        """Test creating a player with minimal required fields."""
        player = Player(
            name="Christian McCaffrey",
            team="SF",
            position="RB",
            bye_week=9,
            ranking=1,
            projected_points=285.2
        )

        assert player.name == "Christian McCaffrey"
        assert player.team == "SF"
        assert player.position == "RB"
        assert player.bye_week == 9
        assert player.injury_status == InjuryStatus.HEALTHY  # Default
        assert player.ranking == 1
        assert player.projected_points == 285.2
        assert player.notes == ""  # Default

    def test_player_equality(self):
        """Test that players are equal based on name, team, and position."""
        player1 = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        player2 = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=2,  # Different ranking
            projected_points=300.0  # Different projection
        )

        player3 = Player(
            name="Lamar Jackson",
            team="BAL",
            position="QB",
            bye_week=14,
            ranking=2,
            projected_points=315.0
        )

        assert player1 == player2  # Same name/team/position
        assert player1 != player3  # Different name
        assert hash(player1) == hash(player2)  # Same hash for equal players

    def test_player_str_representation(self):
        """Test string representation of player."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        assert str(player) == "Josh Allen (QB - BUF)"

    def test_player_to_dict(self):
        """Test converting player to dictionary."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            injury_status=InjuryStatus.QUESTIONABLE,
            ranking=1,
            projected_points=325.5,
            notes="Elite dual-threat QB"
        )

        expected = {
            "name": "Josh Allen",
            "team": "BUF",
            "position": "QB",
            "bye_week": 12,
            "injury_status": "Q",
            "ranking": 1,
            "projected_points": 325.5,
            "notes": "Elite dual-threat QB"
        }

        assert player.to_dict() == expected

    def test_player_from_dict(self):
        """Test creating player from dictionary."""
        data = {
            "name": "Josh Allen",
            "team": "BUF",
            "position": "QB",
            "bye_week": 12,
            "injury_status": "Q",
            "ranking": 1,
            "projected_points": 325.5,
            "notes": "Elite dual-threat QB"
        }

        player = Player.from_dict(data)

        assert player.name == "Josh Allen"
        assert player.team == "BUF"
        assert player.position == "QB"
        assert player.bye_week == 12
        assert player.injury_status == InjuryStatus.QUESTIONABLE
        assert player.ranking == 1
        assert player.projected_points == 325.5
        assert player.notes == "Elite dual-threat QB"

    def test_player_from_dict_with_defaults(self):
        """Test creating player from dictionary with missing optional fields."""
        data = {
            "name": "Christian McCaffrey",
            "team": "SF",
            "position": "RB",
            "bye_week": 9,
            "ranking": 1,
            "projected_points": 285.2
        }

        player = Player.from_dict(data)

        assert player.name == "Christian McCaffrey"
        assert player.injury_status == InjuryStatus.HEALTHY  # Default
        assert player.notes == ""  # Default
