"""
Draft rules and logic for the DAN League special draft format
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class DraftType(Enum):
    """Types of draft rounds"""

    AUCTION = "auction"
    KEEPER = "keeper"
    SNAKE = "snake"


@dataclass
class DraftRules:
    """
    Defines the draft format and rules for the league
    """

    # Round type definitions
    auction_rounds: List[int] = None  # Rounds 1-3
    keeper_round: int = 4
    snake_start_round: int = 5

    # Team and draft settings
    total_teams: int = 10
    total_rounds: int = 20  # Estimate, could vary

    def __post_init__(self):
        if self.auction_rounds is None:
            self.auction_rounds = [1, 2, 3]

    def get_round_type(self, round_num: int) -> DraftType:
        """Determine the type of draft for a given round"""
        if round_num in self.auction_rounds:
            return DraftType.AUCTION
        elif round_num == self.keeper_round:
            return DraftType.KEEPER
        elif round_num >= self.snake_start_round:
            return DraftType.SNAKE
        else:
            # Default for any undefined rounds
            return DraftType.SNAKE

    def is_auction_round(self, round_num: int) -> bool:
        """Check if a round is auction-style"""
        return round_num in self.auction_rounds

    def is_keeper_round(self, round_num: int) -> bool:
        """Check if a round is the keeper round"""
        return round_num == self.keeper_round

    def is_snake_round(self, round_num: int) -> bool:
        """Check if a round follows snake draft order"""
        return round_num >= self.snake_start_round

    def get_snake_pick_order(self, round_num: int, total_teams: int) -> List[int]:
        """
        Get the pick order for a snake draft round.
        Returns list of team indices (0-based) in pick order.
        """
        if not self.is_snake_round(round_num):
            raise ValueError(f"Round {round_num} is not a snake round")

        # Adjust round number for snake calculation (snake starts at round 5, so round 5 = snake round 1)
        snake_round = round_num - self.snake_start_round + 1

        if snake_round % 2 == 1:  # Odd snake rounds: 1→total_teams
            return list(range(total_teams))
        else:  # Even snake rounds: total_teams→1
            return list(range(total_teams - 1, -1, -1))

    def calculate_overall_pick_number(
        self, round_num: int, pick_in_round: int, completed_picks_before_round: int
    ) -> int:
        """
        Calculate the overall pick number across all draft types.

        Args:
            round_num: The current round number
            pick_in_round: Position within the round (1-based)
            completed_picks_before_round: Total picks completed in all previous rounds
        """
        return completed_picks_before_round + pick_in_round


class DraftAnalyzer:
    """Analyzes draft data according to DAN League rules"""

    def __init__(self, rules: DraftRules = None):
        self.rules = rules or DraftRules()

    def analyze_round_participation(
        self, round_num: int, picks_in_round: List[Dict]
    ) -> Dict:
        """
        Analyze which teams participated in a round.
        Important for keeper round where not all teams participate.
        """
        participating_teams = set()
        non_participating_teams = set()

        # Get all team names from picks
        for pick in picks_in_round:
            participating_teams.add(pick.get("team"))

        # For keeper round, determine non-participating teams
        if self.is_keeper_round(round_num):
            # These teams kept players and didn't draft
            all_teams = set()  # Would need to be populated from team list
            non_participating_teams = all_teams - participating_teams

        return {
            "participating_teams": list(participating_teams),
            "non_participating_teams": list(non_participating_teams),
            "participation_count": len(participating_teams),
            "round_type": self.rules.get_round_type(round_num).value,
        }

    def get_draft_strategy_for_round(self, round_num: int) -> Dict:
        """
        Get strategic guidance based on round type.
        """
        round_type = self.rules.get_round_type(round_num)

        if round_type == DraftType.AUCTION:
            return {
                "type": "auction",
                "strategy": "Identify optimal players to target for your team",
                "considerations": [
                    "Analyze player rankings and projections",
                    "Consider positional needs for your roster",
                    "Evaluate player upside and consistency",
                    "Target players that fit your team strategy",
                    "Consider injury risk and reliability",
                ],
            }
        elif round_type == DraftType.KEEPER:
            return {
                "type": "keeper",
                "strategy": "Only draft if you did not keep a player",
                "considerations": [
                    "Limited participation - only non-keeper teams",
                    "Good opportunity for value picks",
                    "Fill positional needs not met by keeper",
                ],
            }
        else:  # SNAKE
            return {
                "type": "snake",
                "strategy": "Traditional best available player strategy",
                "considerations": [
                    "Follow snake draft order",
                    "Consider bye weeks",
                    "Balance roster construction",
                    "Plan for upcoming picks",
                ],
            }

    def is_keeper_round(self, round_num: int) -> bool:
        """Convenience method to check keeper round"""
        return self.rules.is_keeper_round(round_num)

    def is_auction_round(self, round_num: int) -> bool:
        """Convenience method to check auction round"""
        return self.rules.is_auction_round(round_num)

    def is_snake_round(self, round_num: int) -> bool:
        """Convenience method to check snake round"""
        return self.rules.is_snake_round(round_num)
