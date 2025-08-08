"""Tests for the DraftState model."""

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.player_simple import Player


class TestDraftState:
    def test_draft_state_creation_empty(self):
        """Test creating an empty draft state."""
        teams = [
            {"owner": "Buffy", "team_name": "Team Buffy"},
            {"owner": "Willow", "team_name": "Team Willow"}
        ]

        draft_state = DraftState(picks=[], teams=teams)

        assert draft_state.picks == []
        assert draft_state.teams == teams

    def test_draft_state_with_picks(self):
        """Test creating draft state with picks."""
        teams = [
            {"owner": "Buffy", "team_name": "Team Buffy"},
            {"owner": "Willow", "team_name": "Team Willow"}
        ]

        player1 = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        player2 = Player(
            name="Christian McCaffrey",
            team="SF",
            position="RB",
            bye_week=9,
            ranking=1,
            projected_points=285.2
        )

        picks = [
            DraftPick(player=player1, owner="Buffy"),
            DraftPick(player=player2, owner="Willow")
        ]

        draft_state = DraftState(picks=picks, teams=teams)

        assert len(draft_state.picks) == 2
        assert draft_state.picks[0].owner == "Buffy"
        assert draft_state.picks[1].owner == "Willow"

    def test_get_picks_by_owner(self):
        """Test getting all picks for a specific owner."""
        teams = [
            {"owner": "Buffy", "team_name": "Team Buffy"},
            {"owner": "Willow", "team_name": "Team Willow"}
        ]

        player1 = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        player2 = Player(
            name="Christian McCaffrey",
            team="SF",
            position="RB",
            bye_week=9,
            ranking=1,
            projected_points=285.2
        )

        player3 = Player(
            name="Tyreek Hill",
            team="MIA",
            position="WR",
            bye_week=6,
            ranking=1,
            projected_points=270.8
        )

        picks = [
            DraftPick(player=player1, owner="Buffy"),
            DraftPick(player=player2, owner="Willow"),
            DraftPick(player=player3, owner="Buffy")
        ]

        draft_state = DraftState(picks=picks, teams=teams)

        buffy_picks = draft_state.get_picks_by_owner("Buffy")
        willow_picks = draft_state.get_picks_by_owner("Willow")

        assert len(buffy_picks) == 2
        assert len(willow_picks) == 1
        assert buffy_picks[0].player.name == "Josh Allen"
        assert buffy_picks[1].player.name == "Tyreek Hill"
        assert willow_picks[0].player.name == "Christian McCaffrey"

    def test_get_drafted_players(self):
        """Test getting set of all drafted players."""
        teams = [{"owner": "Buffy", "team_name": "Team Buffy"}]

        player1 = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        player2 = Player(
            name="Christian McCaffrey",
            team="SF",
            position="RB",
            bye_week=9,
            ranking=1,
            projected_points=285.2
        )

        picks = [
            DraftPick(player=player1, owner="Buffy"),
            DraftPick(player=player2, owner="Buffy")
        ]

        draft_state = DraftState(picks=picks, teams=teams)
        drafted_players = draft_state.get_drafted_players()

        assert len(drafted_players) == 2
        assert player1 in drafted_players
        assert player2 in drafted_players

    def test_is_player_drafted(self):
        """Test checking if a specific player has been drafted."""
        teams = [{"owner": "Buffy", "team_name": "Team Buffy"}]

        drafted_player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        undrafted_player = Player(
            name="Lamar Jackson",
            team="BAL",
            position="QB",
            bye_week=14,
            ranking=2,
            projected_points=315.0
        )

        picks = [DraftPick(player=drafted_player, owner="Buffy")]
        draft_state = DraftState(picks=picks, teams=teams)

        assert draft_state.is_player_drafted(drafted_player)
        assert not draft_state.is_player_drafted(undrafted_player)

    def test_draft_state_to_dict(self):
        """Test converting draft state to dictionary."""
        teams = [{"owner": "Buffy", "team_name": "Team Buffy"}]

        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )

        picks = [DraftPick(player=player, owner="Buffy")]
        draft_state = DraftState(picks=picks, teams=teams)

        expected = {
            "teams": [{"owner": "Buffy", "team_name": "Team Buffy"}],
            "picks": [
                {
                    "owner": "Buffy",
                    "player": {
                        "name": "Josh Allen",
                        "team": "BUF",
                        "position": "QB",
                        "bye_week": 12,
                        "injury_status": "HEALTHY",
                        "ranking": 1,
                        "projected_points": 325.5,
                        "notes": ""
                    }
                }
            ]
        }

        assert draft_state.to_dict() == expected

    def test_draft_state_from_dict(self):
        """Test creating draft state from dictionary."""
        data = {
            "teams": [{"owner": "Buffy", "team_name": "Team Buffy"}],
            "picks": [
                {
                    "owner": "Buffy",
                    "player": {
                        "name": "Josh Allen",
                        "team": "BUF",
                        "position": "QB",
                        "bye_week": 12,
                        "injury_status": "HEALTHY",
                        "ranking": 1,
                        "projected_points": 325.5,
                        "notes": ""
                    }
                }
            ]
        }

        draft_state = DraftState.from_dict(data)

        assert len(draft_state.teams) == 1
        assert draft_state.teams[0]["owner"] == "Buffy"
        assert len(draft_state.picks) == 1
        assert draft_state.picks[0].owner == "Buffy"
        assert draft_state.picks[0].player.name == "Josh Allen"
