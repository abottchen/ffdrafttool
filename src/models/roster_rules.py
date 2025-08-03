from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .draft_state import Team
from .player import Player, Position


class RosterValidationError(Exception):
    """Exception raised for roster validation errors"""

    pass


@dataclass
class ValidationResult:
    """Result of roster/lineup validation"""

    is_valid: bool
    violations: List[str] = field(default_factory=list)
    total_starters: int = 0
    total_players: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class FlexEligibility:
    """Information about FLEX eligibility for a team"""

    eligible_players: List[Player] = field(default_factory=list)
    rb_options: int = 0
    wr_options: int = 0
    te_options: int = 0
    best_flex_option: Optional[Player] = None


class RosterRules:
    """Enforces fantasy football roster construction rules"""

    def __init__(
        self,
        starter_requirements: Optional[Dict[Position, int]] = None,
        roster_limits: Optional[Dict[Position, int]] = None,
        bench_slots: int = 10,
        ir_slots: int = 2,
        flex_eligible_positions: Optional[Set[Position]] = None,
    ):
        # Default starter requirements
        self.starter_requirements = starter_requirements or {
            Position.QB: 1,
            Position.RB: 2,
            Position.WR: 2,
            Position.TE: 1,
            Position.FLEX: 1,
            Position.K: 1,
            Position.DST: 1,
        }

        # Default roster limits (max players per position)
        self.roster_limits = roster_limits or {
            Position.QB: 4,
            Position.RB: 8,
            Position.WR: 8,
            Position.TE: 4,
            Position.K: 3,
            Position.DST: 3,
        }

        self.bench_slots = bench_slots
        self.ir_slots = ir_slots

        # FLEX eligible positions
        self.flex_eligible_positions = flex_eligible_positions or {
            Position.RB,
            Position.WR,
            Position.TE,
        }

        # Calculate total starter slots and max roster size
        self.total_starter_slots = sum(self.starter_requirements.values())
        self.max_roster_size = self.total_starter_slots + self.bench_slots

    def get_flex_eligible_positions(self) -> Set[Position]:
        """Get positions eligible for FLEX slot"""
        return self.flex_eligible_positions.copy()

    def is_roster_legal(
        self, team: Team, ir_slots_used: int = 0, bench_slots_used: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate entire roster construction is legal.

        Args:
            team: Team to validate
            ir_slots_used: Number of IR slots currently used
            bench_slots_used: Number of bench slots used (auto-calculated if None)

        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        total_players = len(team.roster)

        # Count players by position
        position_counts = {}
        injured_players = 0

        for player in team.roster:
            pos = player.position
            position_counts[pos] = position_counts.get(pos, 0) + 1

            if player.is_injured:
                injured_players += 1

        # Check position limits
        for position, limit in self.roster_limits.items():
            count = position_counts.get(position, 0)
            if count > limit:
                result.is_valid = False
                result.violations.append(
                    f"Exceeds {position.value} limit: {count}/{limit}"
                )

        # Check total roster size
        effective_roster_size = total_players - ir_slots_used
        if effective_roster_size > self.max_roster_size:
            result.is_valid = False
            result.violations.append(
                f"Exceeds roster size limit: {effective_roster_size}/{self.max_roster_size}"
            )

        # Check IR slots
        if ir_slots_used > self.ir_slots:
            result.is_valid = False
            result.violations.append(
                f"Exceeds IR slots: {ir_slots_used}/{self.ir_slots}"
            )

        # Warn if IR slots are underutilized
        if injured_players > ir_slots_used:
            result.warnings.append(
                f"Consider moving {injured_players - ir_slots_used} injured players to IR"
            )

        result.total_players = total_players
        return result

    def get_position_needs(
        self, team: Team, consider_flex_depth: bool = False
    ) -> Dict[Position, int]:
        """
        Calculate position needs for a team.

        Args:
            team: Team to analyze
            consider_flex_depth: Whether to consider FLEX depth needs

        Returns:
            Dict mapping positions to number needed
        """
        needs = {}
        position_counts = {}

        # Count current players by position
        for player in team.roster:
            pos = player.position
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Calculate basic starter needs
        for position, required in self.starter_requirements.items():
            current = position_counts.get(position, 0)

            if position == Position.FLEX:
                # FLEX can be filled by flex-eligible positions
                flex_eligible_count = sum(
                    position_counts.get(pos, 0) for pos in self.flex_eligible_positions
                )
                # Need enough flex-eligible players for RB/WR/TE starters + FLEX
                required_flex_eligible = (
                    self.starter_requirements.get(Position.RB, 0)
                    + self.starter_requirements.get(Position.WR, 0)
                    + self.starter_requirements.get(Position.TE, 0)
                    + 1  # The FLEX slot itself
                )

                if flex_eligible_count < required_flex_eligible:
                    needs[Position.FLEX] = 1
                else:
                    needs[Position.FLEX] = 0
            else:
                needs[position] = max(0, required - current)

        # Consider FLEX depth if requested
        if consider_flex_depth:
            flex_eligible_count = sum(
                position_counts.get(pos, 0) for pos in self.flex_eligible_positions
            )

            # Recommend additional depth for bye weeks and injuries
            starter_needs = (
                self.starter_requirements.get(Position.RB, 0)
                + self.starter_requirements.get(Position.WR, 0)
                + self.starter_requirements.get(Position.TE, 0)
                + 1  # FLEX
            )

            recommended_depth = starter_needs + 2  # 2 extra for depth
            if flex_eligible_count < recommended_depth:
                needs["flex_depth"] = recommended_depth - flex_eligible_count

        return needs

    def calculate_flex_eligibility(
        self,
        team: Team,
        exclude_starters: Optional[Dict[Position, List[Player]]] = None,
    ) -> FlexEligibility:
        """
        Calculate FLEX eligibility for team's players.

        Args:
            team: Team to analyze
            exclude_starters: Players already assigned to starter slots

        Returns:
            FlexEligibility with eligible players and options
        """
        eligibility = FlexEligibility()

        # Get players to exclude (already in starting lineup)
        excluded_players = set()
        if exclude_starters:
            for players in exclude_starters.values():
                excluded_players.update(players)

        # Find eligible players
        for player in team.roster:
            if (
                player.position in self.flex_eligible_positions
                and player not in excluded_players
            ):
                eligibility.eligible_players.append(player)

                if player.position == Position.RB:
                    eligibility.rb_options += 1
                elif player.position == Position.WR:
                    eligibility.wr_options += 1
                elif player.position == Position.TE:
                    eligibility.te_options += 1

        # Sort by rankings to find best option
        ranked_players = [p for p in eligibility.eligible_players if p.average_rank]
        if ranked_players:
            eligibility.best_flex_option = min(
                ranked_players, key=lambda p: p.average_rank
            )
        elif eligibility.eligible_players:
            eligibility.best_flex_option = eligibility.eligible_players[0]

        return eligibility

    def get_roster_limits(self) -> Dict[Position, int]:
        """Get roster limits for each position"""
        return self.roster_limits.copy()

    def get_remaining_slots(self, team: Team) -> Dict[Position, int]:
        """Calculate remaining roster slots for each position"""
        remaining = {}
        position_counts = {}

        # Count current players
        for player in team.roster:
            pos = player.position
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Calculate remaining for each position
        for position, limit in self.roster_limits.items():
            current = position_counts.get(position, 0)
            remaining[position] = max(0, limit - current)

        return remaining

    def is_at_position_limit(self, team: Team, position: Position) -> bool:
        """Check if team is at the roster limit for a position"""
        if position not in self.roster_limits:
            return False

        current_count = team.get_position_count(position)
        return current_count >= self.roster_limits[position]

    def would_exceed_limit(self, team: Team, player: Player) -> bool:
        """Check if adding a player would exceed position limits"""
        if player.position not in self.roster_limits:
            return False

        current_count = team.get_position_count(player.position)
        return current_count >= self.roster_limits[player.position]

    def get_optimal_flex_choice(
        self,
        available_players: List[Player],
        current_starters: Optional[Dict[Position, List[Player]]] = None,
    ) -> Optional[Player]:
        """
        Get optimal FLEX player choice from available options.

        Args:
            available_players: Players available for FLEX
            current_starters: Current starting lineup to avoid double-counting

        Returns:
            Best FLEX option or None if no eligible players
        """
        excluded_players = set()
        if current_starters:
            for players in current_starters.values():
                excluded_players.update(players)

        # Filter to eligible players not already starting
        eligible = [
            p
            for p in available_players
            if (
                p.position in self.flex_eligible_positions and p not in excluded_players
            )
        ]

        if not eligible:
            return None

        # Sort by average rank (lower is better)
        ranked_players = [p for p in eligible if p.average_rank is not None]
        if ranked_players:
            return min(ranked_players, key=lambda p: p.average_rank)

        # Fallback to first eligible player
        return eligible[0]

    def validate_draft_pick(
        self, team: Team, player: Player, current_round: int = 1
    ) -> ValidationResult:
        """
        Validate if drafting a player makes sense for roster construction.

        Args:
            team: Current team roster
            player: Player being considered
            current_round: Current draft round

        Returns:
            ValidationResult with recommendations
        """
        result = ValidationResult(is_valid=True)

        # Check if adding player would exceed limits
        if self.would_exceed_limit(team, player):
            result.is_valid = False
            result.violations.append(
                f"Adding {player.name} would exceed {player.position.value} limit"
            )

        # Check if position is already filled adequately
        needs = self.get_position_needs(team)
        position_need = needs.get(player.position, 0)

        if position_need == 0 and current_round < 8:  # Early rounds
            result.warnings.append(
                f"{player.position.value} position may already be adequately filled"
            )

        # Check for better positional value in early rounds
        if current_round <= 3:
            high_need_positions = [pos for pos, need in needs.items() if need > 0]
            if (
                player.position not in high_need_positions
                and len(high_need_positions) > 0
            ):
                result.warnings.append(
                    f"Consider addressing {', '.join(p.value for p in high_need_positions[:2])} "
                    f"before {player.position.value}"
                )

        return result
