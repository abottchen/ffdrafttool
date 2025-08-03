from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Position(Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DST = "DST"
    FLEX = "FLEX"  # Flex position (RB/WR/TE eligible)
    BE = "BE"      # Bench
    IR = "IR"      # Injured Reserve


class InjuryStatus(Enum):
    HEALTHY = "HEALTHY"
    PROBABLE = "PROBABLE"
    QUESTIONABLE = "QUESTIONABLE"
    DOUBTFUL = "DOUBTFUL"
    OUT = "OUT"


class RankingSource(Enum):
    ESPN = "ESPN"
    YAHOO = "YAHOO"
    CBS = "CBS"
    FANTASYPROS = "FANTASYPROS"
    OTHER = "OTHER"


@dataclass
class Player:
    name: str
    position: Position
    team: str
    bye_week: int
    injury_status: InjuryStatus = InjuryStatus.HEALTHY
    rankings: Dict[RankingSource, Dict[str, float]] = field(default_factory=dict)
    commentary: Optional[str] = None  # Player analysis/notes from sources

    def add_ranking(self, source: RankingSource, rank: int, score: float) -> None:
        self.rankings[source] = {"rank": rank, "score": score}

    @property
    def average_rank(self) -> Optional[float]:
        if not self.rankings:
            return None
        ranks = [data["rank"] for data in self.rankings.values()]
        return sum(ranks) / len(ranks)

    @property
    def average_score(self) -> Optional[float]:
        if not self.rankings:
            return None
        scores = [data["score"] for data in self.rankings.values()]
        return sum(scores) / len(scores)

    @property
    def is_injured(self) -> bool:
        return self.injury_status in [
            InjuryStatus.QUESTIONABLE,
            InjuryStatus.DOUBTFUL,
            InjuryStatus.OUT
        ]

    def update_injury_status(self, status: InjuryStatus) -> None:
        self.injury_status = status

    def __str__(self) -> str:
        return f"{self.name} ({self.position.value} - {self.team})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return NotImplemented
        return (self.name == other.name and
                self.position == other.position and
                self.team == other.team)

    def __hash__(self) -> int:
        return hash((self.name, self.position, self.team))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "position": self.position.value,
            "team": self.team,
            "bye_week": self.bye_week,
            "injury_status": self.injury_status.value,
            "commentary": self.commentary,
            "rankings": {
                source.value: data
                for source, data in self.rankings.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        player = cls(
            name=data["name"],
            position=Position(data["position"]),
            team=data["team"],
            bye_week=data["bye_week"],
            injury_status=InjuryStatus(data.get("injury_status", "HEALTHY")),
            commentary=data.get("commentary")
        )

        if "rankings" in data:
            for source_str, ranking_data in data["rankings"].items():
                source = RankingSource(source_str)
                player.rankings[source] = ranking_data

        return player
