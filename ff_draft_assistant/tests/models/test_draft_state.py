from datetime import datetime

import pytest

from src.models.draft_state import DraftPick, DraftState, Team
from src.models.player import Player, Position


class TestTeam:
    def test_team_creation(self):
        team = Team(name="Team Alpha", draft_position=1)

        assert team.name == "Team Alpha"
        assert team.draft_position == 1
        assert team.roster == []

    def test_add_player(self):
        team = Team(name="Team Beta", draft_position=2)
        player = Player("Josh Allen", Position.QB, "BUF", 13)

        team.add_player(player)

        assert len(team.roster) == 1
        assert team.roster[0] == player

    def test_get_position_count(self):
        team = Team(name="Team Gamma", draft_position=3)

        qb = Player("Patrick Mahomes", Position.QB, "KC", 10)
        rb1 = Player("Christian McCaffrey", Position.RB, "SF", 9)
        rb2 = Player("Austin Ekeler", Position.RB, "LAC", 5)
        wr = Player("Justin Jefferson", Position.WR, "MIN", 13)

        team.add_player(qb)
        team.add_player(rb1)
        team.add_player(rb2)
        team.add_player(wr)

        assert team.get_position_count(Position.QB) == 1
        assert team.get_position_count(Position.RB) == 2
        assert team.get_position_count(Position.WR) == 1
        assert team.get_position_count(Position.TE) == 0

    def test_get_positions_needed(self):
        team = Team(name="Team Delta", draft_position=4)

        team.add_player(Player("Lamar Jackson", Position.QB, "BAL", 13))
        team.add_player(Player("Derrick Henry", Position.RB, "TEN", 6))

        roster_requirements = {
            Position.QB: 2,
            Position.RB: 4,
            Position.WR: 4,
            Position.TE: 2,
            Position.DST: 1,
            Position.K: 1
        }

        needed = team.get_positions_needed(roster_requirements)

        assert needed[Position.QB] == 1
        assert needed[Position.RB] == 3
        assert needed[Position.WR] == 4
        assert needed[Position.TE] == 2
        assert needed[Position.DST] == 1
        assert needed[Position.K] == 1


class TestDraftPick:
    def test_draft_pick_creation(self):
        player = Player("Tyreek Hill", Position.WR, "MIA", 10)
        pick = DraftPick(
            pick_number=5,
            round_number=1,
            team_name="Team Echo",
            player=player,
            timestamp=datetime.now()
        )

        assert pick.pick_number == 5
        assert pick.round_number == 1
        assert pick.team_name == "Team Echo"
        assert pick.player == player
        assert isinstance(pick.timestamp, datetime)


class TestDraftState:
    def test_draft_state_creation(self):
        teams = ["Team A", "Team B", "Team C", "Team D"]
        draft = DraftState(num_teams=4, team_names=teams)

        assert draft.num_teams == 4
        assert len(draft.teams) == 4
        assert draft.current_pick == 1
        assert draft.current_round == 1
        assert draft.picks == []
        assert len(draft.available_players) == 0

    def test_snake_draft_order(self):
        teams = ["Team 1", "Team 2", "Team 3"]
        draft = DraftState(num_teams=3, team_names=teams, is_snake=True)

        # First round: 1, 2, 3
        assert draft.get_current_team().name == "Team 1"
        draft.current_pick = 2
        assert draft.get_current_team().name == "Team 2"
        draft.current_pick = 3
        assert draft.get_current_team().name == "Team 3"

        # Second round: 3, 2, 1 (snake back)
        draft.current_pick = 4
        draft.current_round = 2
        assert draft.get_current_team().name == "Team 3"
        draft.current_pick = 5
        assert draft.get_current_team().name == "Team 2"
        draft.current_pick = 6
        assert draft.get_current_team().name == "Team 1"

    def test_linear_draft_order(self):
        teams = ["Team 1", "Team 2", "Team 3"]
        draft = DraftState(num_teams=3, team_names=teams, is_snake=False)

        # All rounds: 1, 2, 3
        assert draft.get_current_team().name == "Team 1"
        draft.current_pick = 4
        draft.current_round = 2
        assert draft.get_current_team().name == "Team 1"

    def test_make_pick(self):
        teams = ["Team Alpha", "Team Beta"]
        draft = DraftState(num_teams=2, team_names=teams)

        player = Player("Jonathan Taylor", Position.RB, "IND", 11)
        draft.available_players = [player]

        pick = draft.make_pick(player)

        assert pick.pick_number == 1
        assert pick.round_number == 1
        assert pick.team_name == "Team Alpha"
        assert pick.player == player
        assert player not in draft.available_players
        assert player in draft.teams[0].roster
        assert draft.current_pick == 2

    def test_make_pick_not_available(self):
        teams = ["Team A", "Team B"]
        draft = DraftState(num_teams=2, team_names=teams)

        player = Player("Unavailable Player", Position.WR, "XXX", 1)

        with pytest.raises(ValueError, match="not available"):
            draft.make_pick(player)

    def test_is_player_drafted(self):
        teams = ["Team 1", "Team 2"]
        draft = DraftState(num_teams=2, team_names=teams)

        player1 = Player("Drafted Player", Position.QB, "DAL", 7)
        player2 = Player("Available Player", Position.QB, "NYG", 13)

        draft.available_players = [player1, player2]
        draft.make_pick(player1)

        assert draft.is_player_drafted(player1)
        assert not draft.is_player_drafted(player2)

    def test_get_team_by_name(self):
        teams = ["Awesome Team", "Cool Team"]
        draft = DraftState(num_teams=2, team_names=teams)

        team = draft.get_team_by_name("Cool Team")
        assert team is not None
        assert team.name == "Cool Team"
        assert team.draft_position == 2

        assert draft.get_team_by_name("Nonexistent Team") is None

    def test_set_available_players(self):
        draft = DraftState(num_teams=2, team_names=["A", "B"])

        players = [
            Player("Player 1", Position.QB, "T1", 1),
            Player("Player 2", Position.RB, "T2", 2),
            Player("Player 3", Position.WR, "T3", 3)
        ]

        draft.set_available_players(players)

        assert len(draft.available_players) == 3
        assert all(p in draft.available_players for p in players)

    def test_update_from_external_picks(self):
        teams = ["My Team", "Other Team"]
        draft = DraftState(num_teams=2, team_names=teams)

        player1 = Player("External Pick 1", Position.RB, "T1", 5)
        player2 = Player("External Pick 2", Position.WR, "T2", 7)

        draft.available_players = [player1, player2]

        # Simulate external picks
        external_picks = [
            {"team": "My Team", "player_name": "External Pick 1"},
            {"team": "Other Team", "player_name": "External Pick 2"}
        ]

        for pick_data in external_picks:
            player = next(p for p in draft.available_players
                         if p.name == pick_data["player_name"])
            draft.make_pick(player)

        assert draft.current_pick == 3
        assert draft.current_round == 2
        assert len(draft.picks) == 2
        assert len(draft.available_players) == 0

    def test_get_recent_picks(self):
        teams = ["Team 1", "Team 2", "Team 3"]
        draft = DraftState(num_teams=3, team_names=teams)

        players = [
            Player(f"Player {i}", Position.RB, f"T{i}", i)
            for i in range(1, 6)
        ]
        draft.available_players = players.copy()

        # Make 5 picks
        for player in players:
            draft.make_pick(player)

        recent = draft.get_recent_picks(3)
        assert len(recent) == 3
        assert recent[0].player.name == "Player 5"  # Most recent
        assert recent[2].player.name == "Player 3"  # 3rd most recent

    def test_to_dict_from_dict(self):
        teams = ["Team X", "Team Y"]
        draft = DraftState(num_teams=2, team_names=teams, rounds_per_draft=10)

        player = Player("Test Player", Position.TE, "KC", 10)
        draft.available_players = [player]
        draft.make_pick(player)

        # Convert to dict
        draft_dict = draft.to_dict()

        # Create new draft from dict
        new_draft = DraftState.from_dict(draft_dict)

        assert new_draft.num_teams == draft.num_teams
        assert new_draft.current_pick == draft.current_pick
        assert new_draft.current_round == draft.current_round
        assert len(new_draft.picks) == len(draft.picks)
        assert new_draft.teams[0].roster[0].name == player.name
