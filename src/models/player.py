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
    BE = "BE"  # Bench
    IR = "IR"  # Injured Reserve


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

        total_rank = sum(ranking["rank"] for ranking in self.rankings.values())
        return total_rank / len(self.rankings)

    @property
    def average_score(self) -> Optional[float]:
        if not self.rankings:
            return None

        total_score = sum(ranking["score"] for ranking in self.rankings.values())
        return total_score / len(self.rankings)

    def get_best_ranking(self) -> Optional[Dict[str, Any]]:
        """Get the ranking with the lowest rank number (best ranking)."""
        if not self.rankings:
            return None

        best_source = min(self.rankings, key=lambda x: self.rankings[x]["rank"])
        return {
            "source": best_source,
            "rank": self.rankings[best_source]["rank"],
            "score": self.rankings[best_source]["score"]
        }

    def get_ranking_by_source(self, source: RankingSource) -> Optional[Dict[str, float]]:
        """Get ranking data from a specific source."""
        return self.rankings.get(source)

    def has_injury_concern(self) -> bool:
        """Check if player has any injury concerns."""
        return self.injury_status in [
            InjuryStatus.PROBABLE,
            InjuryStatus.QUESTIONABLE,
            InjuryStatus.DOUBTFUL,
            InjuryStatus.OUT
        ]

    def __str__(self) -> str:
        injury_note = f" ({self.injury_status.value})" if self.injury_status != InjuryStatus.HEALTHY else ""
        avg_rank = f"Avg Rank: {self.average_rank:.1f}" if self.average_rank else "No rankings"
        return f"{self.name} ({self.position.value}, {self.team}){injury_note} - {avg_rank}"
