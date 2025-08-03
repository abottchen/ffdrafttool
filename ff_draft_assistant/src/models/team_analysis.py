from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .draft_state import Team
from .player import Player, Position
from .roster_rules import RosterRules


@dataclass
class RosterNeed:
    position: Position
    needed_count: int
    current_count: int
    priority_score: float

    @property
    def deficit(self) -> int:
        return self.needed_count - self.current_count


@dataclass
class PositionScarcity:
    position: Position
    total_starters_needed: int
    quality_players_available: int
    scarcity_score: float


class TeamAnalysis:
    def __init__(
        self,
        roster_rules: Optional[RosterRules] = None,
        num_teams: int = 12,
        starter_threshold_percentile: float = 0.8
    ):
        self.roster_rules = roster_rules or RosterRules()
        self.num_teams = num_teams
        self.starter_threshold_percentile = starter_threshold_percentile

        # For backward compatibility - keep roster_requirements reference
        self.roster_requirements = self.roster_rules.starter_requirements

    def analyze_roster_needs(self, team: Team, consider_flex_depth: bool = True) -> List[RosterNeed]:
        """Analyze roster needs using RosterRules for accurate assessment"""
        needs = []

        # Use RosterRules to get position needs
        position_needs = self.roster_rules.get_position_needs(team, consider_flex_depth)

        for position, required_count in self.roster_requirements.items():
            current_count = team.get_position_count(position)

            # Get need from RosterRules calculation
            if position == Position.FLEX:
                # FLEX need is calculated differently by RosterRules
                deficit = position_needs.get(Position.FLEX, 0)
            else:
                deficit = max(0, required_count - current_count)

            # Calculate priority score based on deficit and position importance
            if required_count > 0:
                priority_score = deficit / required_count

                # Boost priority for key positions
                if position in [Position.QB, Position.RB, Position.WR]:
                    priority_score *= 1.2

                # Extra boost for FLEX depth since it provides positional flexibility
                if position in self.roster_rules.get_flex_eligible_positions():
                    flex_eligibility = self.roster_rules.calculate_flex_eligibility(team)
                    if flex_eligibility.rb_options + flex_eligibility.wr_options + flex_eligibility.te_options < 3:
                        priority_score *= 1.1  # Boost for FLEX depth
            else:
                priority_score = 0

            needs.append(RosterNeed(
                position=position,
                needed_count=required_count,
                current_count=current_count,
                priority_score=priority_score
            ))

        # Add FLEX depth need if identified by RosterRules
        flex_depth_need = position_needs.get('flex_depth', 0)
        if flex_depth_need > 0:
            needs.append(RosterNeed(
                position=Position.FLEX,  # Use FLEX to represent depth need
                needed_count=flex_depth_need,
                current_count=0,
                priority_score=0.8  # High priority for depth
            ))

        # Sort by priority score descending
        needs.sort(key=lambda n: n.priority_score, reverse=True)
        return needs

    def calculate_position_scarcity(
        self,
        available_players: List[Player],
        current_round: int,
        total_rounds: int
    ) -> List[PositionScarcity]:
        scarcity_list = []

        # Group players by position
        position_players = defaultdict(list)
        for player in available_players:
            if player.average_rank is not None:
                position_players[player.position].append(player)

        # Calculate scarcity for each position
        for position, required_count in self.roster_requirements.items():
            if position == Position.DST or position == Position.K:
                # Special handling for DST/K - only consider in late rounds
                if current_round < total_rounds - 3:
                    continue

            total_starters_needed = self.num_teams * required_count
            players = position_players.get(position, [])

            # Count quality players (above threshold)
            if players:
                sorted(players, key=lambda p: p.average_rank or float('inf'))
                threshold_index = int(len(players) * self.starter_threshold_percentile)
                quality_players = len(players[:threshold_index])
            else:
                quality_players = 0

            # Calculate scarcity score
            if total_starters_needed > 0:
                scarcity_score = 1 - (quality_players / total_starters_needed)
                scarcity_score = max(0, min(1, scarcity_score))
            else:
                scarcity_score = 0

            scarcity_list.append(PositionScarcity(
                position=position,
                total_starters_needed=total_starters_needed,
                quality_players_available=quality_players,
                scarcity_score=scarcity_score
            ))

        # Sort by scarcity score descending
        scarcity_list.sort(key=lambda s: s.scarcity_score, reverse=True)
        return scarcity_list

    def get_positional_tiers(
        self,
        players: List[Player],
        max_tiers: int = 5
    ) -> List[List[Player]]:
        if not players:
            return []

        # Sort players by average score
        sorted_players = sorted(
            [p for p in players if p.average_score is not None],
            key=lambda p: p.average_score,
            reverse=True
        )

        if not sorted_players:
            return []

        # Simple tier calculation based on score drops
        tiers = []
        current_tier = [sorted_players[0]]

        for i in range(1, len(sorted_players)):
            prev_score = sorted_players[i-1].average_score
            curr_score = sorted_players[i].average_score

            # If score drop is significant, start new tier
            if prev_score - curr_score > 3 and len(tiers) < max_tiers - 1:
                tiers.append(current_tier)
                current_tier = [sorted_players[i]]
            else:
                current_tier.append(sorted_players[i])

        if current_tier:
            tiers.append(current_tier)

        return tiers[:max_tiers]

    def calculate_value_over_replacement(
        self,
        player: Player,
        available_players: List[Player]
    ) -> float:
        if player.average_score is None:
            return 0

        # Find replacement level player (starter threshold)
        position_players = [
            p for p in available_players
            if p.position == player.position and p.average_score is not None
        ]

        if not position_players:
            return player.average_score

        position_players.sort(key=lambda p: p.average_score, reverse=True)

        # Replacement level is the last starter-quality player
        starters_needed = self.roster_requirements.get(player.position, 0) * self.num_teams
        replacement_index = min(starters_needed, len(position_players) - 1)

        if replacement_index < len(position_players):
            replacement_score = position_players[replacement_index].average_score
            return player.average_score - replacement_score
        else:
            return player.average_score

    def get_recommended_positions(
        self,
        team: Team,
        available_players: List[Player],
        current_round: int,
        total_rounds: int,
        max_recommendations: int = 3
    ) -> List[Position]:
        # Get roster needs
        needs = self.analyze_roster_needs(team)

        # Get position scarcity
        scarcity = self.calculate_position_scarcity(
            available_players, current_round, total_rounds
        )

        # Combine need and scarcity scores
        position_scores = {}

        for need in needs:
            if need.deficit > 0:
                need_score = need.priority_score

                # Find scarcity score for this position
                scarcity_score = next(
                    (s.scarcity_score for s in scarcity if s.position == need.position),
                    0
                )

                # Combined score (weighted average)
                position_scores[need.position] = (0.6 * need_score) + (0.4 * scarcity_score)

        # Sort positions by combined score
        recommended = sorted(
            position_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [pos for pos, _ in recommended[:max_recommendations]]

    def evaluate_pick_value(
        self,
        player: Player,
        team: Team,
        available_players: List[Player],
        current_round: int,
        total_rounds: int
    ) -> float:
        if player.average_score is None:
            return 0

        # Base value from player quality
        base_value = player.average_score / 100  # Normalize to 0-1

        # Check roster rules compliance
        validation = self.roster_rules.validate_draft_pick(team, player, current_round)
        if not validation.is_valid:
            return 0.1  # Very low value for invalid picks

        # Apply warning penalties
        warning_penalty = 1.0
        if validation.warnings:
            warning_penalty = 0.9  # 10% penalty for warnings

        # Roster need multiplier using RosterRules
        needs = self.analyze_roster_needs(team, consider_flex_depth=True)
        position_need = next(
            (n for n in needs if n.position == player.position),
            None
        )

        if position_need and position_need.deficit > 0:
            need_multiplier = 1 + (position_need.priority_score * 0.3)
        else:
            # Check if player can fill FLEX slot
            if player.position in self.roster_rules.get_flex_eligible_positions():
                flex_need = next(
                    (n for n in needs if n.position == Position.FLEX),
                    None
                )
                if flex_need and flex_need.deficit > 0:
                    need_multiplier = 1 + (flex_need.priority_score * 0.25)  # Slightly lower for FLEX
                else:
                    need_multiplier = 0.8  # Some value for FLEX depth
            else:
                need_multiplier = 0.7  # Penalty for drafting unneeded position

        # Position limit penalty - if close to limit, reduce value
        remaining_slots = self.roster_rules.get_remaining_slots(team)
        position_remaining = remaining_slots.get(player.position, 0)
        if position_remaining <= 1:  # Almost at limit
            need_multiplier *= 0.8

        # Scarcity multiplier
        scarcity_list = self.calculate_position_scarcity(
            available_players, current_round, total_rounds
        )
        position_scarcity = next(
            (s for s in scarcity_list if s.position == player.position),
            None
        )

        if position_scarcity:
            scarcity_multiplier = 1 + (position_scarcity.scarcity_score * 0.2)
        else:
            scarcity_multiplier = 1

        # FLEX value bonus - players who can fill FLEX get slight bonus
        flex_bonus = 1.0
        if player.position in self.roster_rules.get_flex_eligible_positions():
            flex_eligibility = self.roster_rules.calculate_flex_eligibility(team)
            total_flex_options = (flex_eligibility.rb_options +
                                flex_eligibility.wr_options +
                                flex_eligibility.te_options)
            if total_flex_options < 4:  # Need more FLEX depth
                flex_bonus = 1.05

        # Value over replacement bonus
        vor = self.calculate_value_over_replacement(player, available_players)
        vor_bonus = vor / 100  # Normalize

        # Calculate final value
        final_value = (base_value * need_multiplier * scarcity_multiplier *
                      flex_bonus * warning_penalty) + vor_bonus

        return min(1.0, final_value)  # Cap at 1.0

    def get_draft_strategy_advice(
        self,
        team: Team,
        available_players: List[Player],
        current_round: int,
        total_rounds: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive draft strategy advice using RosterRules.

        Returns advice like "you need RB depth for your FLEX spot" or
        "you're at the QB limit, focus on other positions."
        """
        advice = {
            "primary_needs": [],
            "warnings": [],
            "opportunities": [],
            "position_limits": {},
            "flex_analysis": {},
            "strategy_notes": []
        }

        # Analyze current roster state
        needs = self.analyze_roster_needs(team, consider_flex_depth=True)
        remaining_slots = self.roster_rules.get_remaining_slots(team)
        flex_eligibility = self.roster_rules.calculate_flex_eligibility(team)

        # Primary needs analysis
        high_priority_needs = [n for n in needs if n.priority_score > 0.5]
        for need in high_priority_needs[:3]:  # Top 3 needs
            if need.position == Position.FLEX and need.deficit > 0:
                advice["primary_needs"].append(
                    f"Need {need.deficit} more FLEX-eligible players (RB/WR/TE) for starting lineup"
                )
            elif need.deficit > 0:
                advice["primary_needs"].append(
                    f"Need {need.deficit} more {need.position.value} for starting lineup"
                )

        # Position limit warnings
        for position, remaining in remaining_slots.items():
            if remaining <= 1 and remaining > 0:
                advice["warnings"].append(
                    f"Close to {position.value} roster limit ({remaining} slot remaining)"
                )
            elif remaining == 0:
                advice["warnings"].append(
                    f"At {position.value} roster limit - cannot draft more"
                )

        # FLEX analysis
        total_flex_options = (flex_eligibility.rb_options +
                            flex_eligibility.wr_options +
                            flex_eligibility.te_options)

        advice["flex_analysis"] = {
            "total_flex_options": total_flex_options,
            "rb_depth": flex_eligibility.rb_options,
            "wr_depth": flex_eligibility.wr_options,
            "te_depth": flex_eligibility.te_options,
            "best_flex_option": flex_eligibility.best_flex_option.name if flex_eligibility.best_flex_option else None
        }

        if total_flex_options < 3:
            advice["opportunities"].append(
                "Need RB/WR/TE depth for FLEX position and bye week coverage"
            )
        elif total_flex_options >= 6:
            advice["opportunities"].append(
                "Good FLEX depth - can focus on other positions or best available"
            )

        # Round-specific strategy advice
        if current_round <= 3:
            # Early rounds - focus on starters
            advice["strategy_notes"].append(
                "Early rounds: prioritize guaranteed starters and elite talent"
            )
            if any(n.position in [Position.RB, Position.WR] and n.deficit > 0 for n in needs):
                advice["strategy_notes"].append(
                    "Consider RB/WR early for FLEX flexibility"
                )

        elif current_round <= 8:
            # Middle rounds - fill out starters and get depth
            advice["strategy_notes"].append(
                "Middle rounds: complete starting lineup and add key depth"
            )
            if total_flex_options < 4:
                advice["strategy_notes"].append(
                    "Focus on RB/WR/TE depth for FLEX and bye week coverage"
                )

        elif current_round <= 12:
            # Late rounds - depth and upside
            advice["strategy_notes"].append(
                "Late rounds: target depth, handcuffs, and high-upside players"
            )

        else:
            # Very late rounds - fill mandatory positions
            if remaining_slots.get(Position.K, 0) > 0:
                advice["strategy_notes"].append("Time to draft Kicker if not done")
            if remaining_slots.get(Position.DST, 0) > 0:
                advice["strategy_notes"].append("Time to draft Defense if not done")

        # Specific positional advice
        qb_count = team.get_position_count(Position.QB)
        if qb_count == 0 and current_round > 6:
            advice["warnings"].append("No QB drafted yet - becoming urgent")
        elif qb_count >= 2 and current_round <= 8:
            advice["opportunities"].append("QB position stable - can focus elsewhere")

        # Bye week considerations
        if current_round >= 6:
            bye_weeks = {}
            for player in team.roster:
                bye_weeks[player.bye_week] = bye_weeks.get(player.bye_week, 0) + 1

            problematic_byes = [week for week, count in bye_weeks.items() if count >= 3]
            if problematic_byes:
                advice["warnings"].append(
                    f"Heavy bye week conflicts in week(s) {', '.join(map(str, problematic_byes))}"
                )

        return advice
