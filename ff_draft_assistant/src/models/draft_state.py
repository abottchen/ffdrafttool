from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .player import Player, Position


@dataclass
class Team:
    name: str
    draft_position: int
    roster: List[Player] = field(default_factory=list)

    def add_player(self, player: Player) -> None:
        self.roster.append(player)

    def get_position_count(self, position: Position) -> int:
        return sum(1 for p in self.roster if p.position == position)

    def get_positions_needed(
        self, roster_requirements: Dict[Position, int]
    ) -> Dict[Position, int]:
        needed = {}
        for position, required_count in roster_requirements.items():
            current_count = self.get_position_count(position)
            needed[position] = max(0, required_count - current_count)
        return needed


@dataclass
class DraftPick:
    pick_number: int
    round_number: int
    team_name: str
    player: Player
    timestamp: datetime = field(default_factory=datetime.now)


class DraftState:
    def __init__(
        self,
        num_teams: int,
        team_names: List[str],
        rounds_per_draft: int = 15,
        is_snake: bool = True,
    ):
        self.num_teams = num_teams
        self.rounds_per_draft = rounds_per_draft
        self.is_snake = is_snake
        self.teams: List[Team] = []
        self.picks: List[DraftPick] = []
        self.available_players: List[Player] = []
        self.current_pick = 1
        self.current_round = 1

        # Initialize teams
        for i, name in enumerate(team_names):
            self.teams.append(Team(name=name, draft_position=i + 1))

    def get_current_team(self) -> Team:
        if self.is_snake and self.current_round % 2 == 0:
            # Even rounds go in reverse order
            position = self.num_teams - ((self.current_pick - 1) % self.num_teams)
        else:
            # Odd rounds or linear draft
            position = ((self.current_pick - 1) % self.num_teams) + 1

        return self.teams[position - 1]

    def make_pick(self, player: Player) -> DraftPick:
        if player not in self.available_players:
            raise ValueError(f"{player.name} is not available")

        current_team = self.get_current_team()
        pick = DraftPick(
            pick_number=self.current_pick,
            round_number=self.current_round,
            team_name=current_team.name,
            player=player,
        )

        # Update state
        self.picks.append(pick)
        self.available_players.remove(player)
        current_team.add_player(player)

        # Advance to next pick
        self.current_pick += 1
        if (self.current_pick - 1) % self.num_teams == 0:
            self.current_round += 1

        return pick

    def is_player_drafted(self, player: Player) -> bool:
        return any(pick.player == player for pick in self.picks)

    def get_team_by_name(self, name: str) -> Optional[Team]:
        for team in self.teams:
            if team.name == name:
                return team
        return None

    def set_available_players(self, players: List[Player]) -> None:
        self.available_players = players.copy()

    def get_recent_picks(self, num_picks: int = 5) -> List[DraftPick]:
        if not self.picks:
            return []
        return list(reversed(self.picks[-num_picks:]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_teams": self.num_teams,
            "rounds_per_draft": self.rounds_per_draft,
            "is_snake": self.is_snake,
            "current_pick": self.current_pick,
            "current_round": self.current_round,
            "teams": [
                {
                    "name": team.name,
                    "draft_position": team.draft_position,
                    "roster": [p.to_dict() for p in team.roster],
                }
                for team in self.teams
            ],
            "picks": [
                {
                    "pick_number": pick.pick_number,
                    "round_number": pick.round_number,
                    "team_name": pick.team_name,
                    "player": pick.player.to_dict(),
                    "timestamp": pick.timestamp.isoformat(),
                }
                for pick in self.picks
            ],
            "available_players": [p.to_dict() for p in self.available_players],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DraftState":
        team_names = [team["name"] for team in data["teams"]]
        draft = cls(
            num_teams=data["num_teams"],
            team_names=team_names,
            rounds_per_draft=data["rounds_per_draft"],
            is_snake=data["is_snake"],
        )

        draft.current_pick = data["current_pick"]
        draft.current_round = data["current_round"]

        # Restore teams and rosters
        for team_data, team in zip(data["teams"], draft.teams):
            for player_data in team_data["roster"]:
                player = Player.from_dict(player_data)
                team.add_player(player)

        # Restore picks
        for pick_data in data["picks"]:
            pick = DraftPick(
                pick_number=pick_data["pick_number"],
                round_number=pick_data["round_number"],
                team_name=pick_data["team_name"],
                player=Player.from_dict(pick_data["player"]),
                timestamp=datetime.fromisoformat(pick_data["timestamp"]),
            )
            draft.picks.append(pick)

        # Restore available players
        draft.available_players = [
            Player.from_dict(p) for p in data["available_players"]
        ]

        return draft
