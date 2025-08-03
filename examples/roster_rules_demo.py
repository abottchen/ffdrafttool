#!/usr/bin/env python3
"""
Demonstration of Fantasy Football Roster Rules and Draft Strategy Analysis

This example shows how the RosterRules class enforces league settings and
how TeamAnalysis provides intelligent draft advice using these rules.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.draft_state import Team
from src.models.player import Player, Position
from src.models.roster_rules import RosterRules
from src.models.team_analysis import TeamAnalysis


def main():
    print("Fantasy Football Roster Rules & Draft Strategy Demo")
    print("=" * 60)

    # Create roster rules (default league settings)
    rules = RosterRules()
    print("League Settings:")
    print(f"  Starters: {sum(rules.starter_requirements.values())} total")
    print(f"    - QB: {rules.starter_requirements[Position.QB]}")
    print(f"    - RB: {rules.starter_requirements[Position.RB]}")
    print(f"    - WR: {rules.starter_requirements[Position.WR]}")
    print(f"    - TE: {rules.starter_requirements[Position.TE]}")
    print(f"    - FLEX: {rules.starter_requirements[Position.FLEX]}")
    print(f"    - K: {rules.starter_requirements[Position.K]}")
    print(f"    - DST: {rules.starter_requirements[Position.DST]}")
    print(f"  Bench: {rules.bench_slots} slots")
    print(f"  Max Roster: {rules.max_roster_size} players")
    print()

    # Create a sample team at different stages of the draft
    print("Draft Stage Analysis")
    print("-" * 40)

    # Early draft team (rounds 1-3)
    early_team = Team("Early Drafter", 1)
    early_team.add_player(Player("Christian McCaffrey", Position.RB, "SF", 9))
    early_team.add_player(Player("Tyreek Hill", Position.WR, "MIA", 10))
    early_team.add_player(Player("Travis Kelce", Position.TE, "KC", 10))

    print("Early Draft Team (3 picks):")
    analyze_team_state(rules, early_team, current_round=4)
    print()

    # Mid-draft team (rounds 4-8)
    mid_team = Team("Mid Drafter", 1)
    mid_team.add_player(Player("Josh Allen", Position.QB, "BUF", 13))
    mid_team.add_player(Player("Saquon Barkley", Position.RB, "NYG", 11))
    mid_team.add_player(Player("Austin Ekeler", Position.RB, "LAC", 5))
    mid_team.add_player(Player("Stefon Diggs", Position.WR, "BUF", 13))
    mid_team.add_player(Player("CeeDee Lamb", Position.WR, "DAL", 7))
    mid_team.add_player(Player("Mark Andrews", Position.TE, "BAL", 13))
    mid_team.add_player(Player("Tony Pollard", Position.RB, "DAL", 7))

    print("Mid-Draft Team (7 picks):")
    analyze_team_state(rules, mid_team, current_round=8)
    print()

    # Late draft team (rounds 12+) - needs K and DST
    late_team = Team("Late Drafter", 1)
    # Copy mid-team roster and add more players
    for player in mid_team.roster:
        late_team.add_player(player)

    late_team.add_player(Player("Alexander Mattison", Position.RB, "MIN", 13))
    late_team.add_player(Player("Romeo Doubs", Position.WR, "GB", 10))
    late_team.add_player(Player("Tua Tagovailoa", Position.QB, "MIA", 10))
    late_team.add_player(Player("Dalton Schultz", Position.TE, "HOU", 7))
    late_team.add_player(Player("Elijah Moore", Position.WR, "CLE", 5))
    # Still missing K and DST

    print("Late Draft Team (12 picks):")
    analyze_team_state(rules, late_team, current_round=13)
    print()

    # Show roster construction focus
    print("Draft-Focused Roster Construction")
    print("-" * 40)
    print("For draft assistance, we focus on:")
    print("  - Legal roster construction (position limits)")
    print("  - Position needs identification")
    print("  - FLEX eligibility for strategic depth")
    print("  - Not lineup validation (handled during season)")
    print()

    # Demonstrate FLEX optimization
    print("FLEX Position Analysis")
    print("-" * 40)

    flex_team = Team("FLEX Team", 1)
    flex_team.add_player(Player("QB1", Position.QB, "BUF", 13))
    flex_team.add_player(Player("RB1", Position.RB, "SF", 9))
    flex_team.add_player(Player("RB2", Position.RB, "LAC", 5))
    flex_team.add_player(Player("RB3", Position.RB, "DAL", 7))
    flex_team.add_player(Player("RB4", Position.RB, "MIN", 13))
    flex_team.add_player(Player("WR1", Position.WR, "MIA", 10))
    flex_team.add_player(Player("WR2", Position.WR, "BUF", 13))
    flex_team.add_player(Player("TE1", Position.TE, "KC", 10))

    eligibility = rules.calculate_flex_eligibility(flex_team)
    print("FLEX Analysis:")
    print(f"  Total eligible players: {len(eligibility.eligible_players)}")
    print(f"  RB options: {eligibility.rb_options}")
    print(f"  WR options: {eligibility.wr_options}")
    print(f"  TE options: {eligibility.te_options}")
    print()

    # Show position limits
    print("Position Limit Enforcement")
    print("-" * 40)

    limit_team = Team("Limit Test", 1)
    # Add maximum QBs
    for i in range(4):
        limit_team.add_player(Player(f"QB{i+1}", Position.QB, f"T{i+1}", 1))

    print("Team with 4 QBs (at limit):")
    print(f"  At QB limit: {rules.is_at_position_limit(limit_team, Position.QB)}")

    # Try to add another QB
    extra_qb = Player("QB5", Position.QB, "NYJ", 11)
    would_exceed = rules.would_exceed_limit(limit_team, extra_qb)
    print(f"  Adding 5th QB would exceed limit: {would_exceed}")

    remaining = rules.get_remaining_slots(limit_team)
    print(f"  Remaining QB slots: {remaining[Position.QB]}")
    print()


def analyze_team_state(rules: RosterRules, team: Team, current_round: int):
    """Analyze team state using RosterRules and TeamAnalysis"""

    # Basic roster validation
    roster_result = rules.is_roster_legal(team)
    print(f"  Roster Legal: {'YES' if roster_result.is_valid else 'NO'}")
    if roster_result.warnings:
        for warning in roster_result.warnings:
            print(f"    WARNING: {warning}")

    # Position needs
    needs = rules.get_position_needs(team, consider_flex_depth=True)
    urgent_needs = [pos.value for pos, count in needs.items() if count > 0 and pos != 'flex_depth']
    if urgent_needs:
        print(f"  Urgent Needs: {', '.join(urgent_needs)}")

    # FLEX eligibility
    flex_eligibility = rules.calculate_flex_eligibility(team)
    total_flex = flex_eligibility.rb_options + flex_eligibility.wr_options + flex_eligibility.te_options
    print(f"  FLEX Options: {total_flex} total ({flex_eligibility.rb_options} RB, {flex_eligibility.wr_options} WR, {flex_eligibility.te_options} TE)")

    # Draft strategy advice
    analysis = TeamAnalysis(roster_rules=rules, num_teams=12)
    advice = analysis.get_draft_strategy_advice(team, [], current_round, 15)

    if advice["primary_needs"]:
        print(f"  Strategy: {advice['primary_needs'][0]}")

    if advice["warnings"]:
        print(f"  Warning: {advice['warnings'][0]}")

    if advice["strategy_notes"]:
        print(f"  Round Advice: {advice['strategy_notes'][0]}")


if __name__ == "__main__":
    main()
