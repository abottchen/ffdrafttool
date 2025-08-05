import logging
import time
from typing import Any, Dict, List

from src.tools.analyze_players import analyze_available_players

logger = logging.getLogger(__name__)


async def suggest_draft_pick(
    draft_state: Dict[str, Any],
    owner_name: str,
    strategy: str = "balanced",
    consider_bye_weeks: bool = True,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Suggest the best draft pick based on team needs, strategy, and roster construction.

    Args:
        draft_state: Current draft state including roster and available players
        owner_name: Name of the team owner to provide suggestions for (e.g., "Adam", "Jodi")
        strategy: Draft strategy ("balanced", "best_available", "upside", "safe")
        consider_bye_weeks: Whether to consider bye week conflicts (default: True)

    Returns:
        Dict containing recommended pick, alternatives, reasoning, and strategic analysis
    """
    start_time = time.time()
    logger.info(
        f"Generating draft pick suggestion with strategy: {strategy}, consider_bye_weeks: {consider_bye_weeks}"
    )

    try:
        # Validate strategy
        valid_strategies = ["balanced", "best_available", "upside", "safe"]
        if strategy not in valid_strategies:
            return {
                "success": False,
                "error": f"Invalid strategy: {strategy}. Valid strategies: {', '.join(valid_strategies)}",
            }

        # Get comprehensive player analysis
        available_analysis = await analyze_available_players(
            draft_state, limit=50, force_refresh=force_refresh
        )

        if not available_analysis.get("success"):
            return {
                "success": False,
                "error": "Failed to analyze available players for draft suggestion",
                "analysis_error": available_analysis.get("error"),
            }

        available_players = available_analysis["players"]
        if not available_players:
            return {
                "success": False,
                "error": "No available players found for draft suggestion",
            }

        # Find the specified team by owner
        teams = draft_state.get("teams", [])
        analysis_team = None

        for team in teams:
            if team.get("owner") == owner_name:
                analysis_team = team
                logger.info(
                    f"Found team for draft suggestion - Owner: {owner_name}, Team: {team.get('team_name')}"
                )
                break

        if not analysis_team:
            return {
                "success": False,
                "error": f"Owner '{owner_name}' not found in draft data. Available owners: {[t.get('owner') for t in teams]}",
            }

        roster_analysis = _analyze_roster_needs(draft_state, analysis_team)

        # Calculate current round from picks and teams (same logic as analyze_available_players)
        # But respect existing current_round in draft_state if provided (for tests)
        existing_round = draft_state.get("draft_state", {}).get("current_round")
        if existing_round:
            current_round = existing_round
        else:
            total_picks = len(draft_state.get("picks", []))
            teams = draft_state.get("teams", [])
            total_teams = len(teams) if teams else 10
            current_pick = total_picks + 1
            current_round = ((current_pick - 1) // total_teams) + 1

        # Apply strategy-specific scoring
        strategy_weighted_players = []

        for player in available_players:
            base_value = player["value_metrics"]["overall_value"]
            position = player["position"]

            # Strategy-specific multipliers
            strategy_multiplier = _calculate_strategy_multiplier(
                player, roster_analysis, strategy, current_round
            )

            # Bye week consideration
            bye_week_factor = 1.0
            if consider_bye_weeks:
                bye_week_factor = player["bye_week_analysis"]["bye_week_penalty"]

            # Roster need factor
            position_need_factor = (
                roster_analysis["position_needs"]
                .get(position, {})
                .get("urgency_multiplier", 1.0)
            )

            # Final weighted score
            final_score = (
                base_value
                * strategy_multiplier
                * bye_week_factor
                * position_need_factor
            )

            strategy_weighted_players.append(
                {
                    **player,
                    "strategy_score": round(final_score, 2),
                    "strategy_multiplier": round(strategy_multiplier, 2),
                    "position_need_factor": round(position_need_factor, 2),
                    "final_reasoning": [],
                }
            )

        # Sort by strategy-weighted score
        strategy_weighted_players.sort(key=lambda p: p["strategy_score"], reverse=True)

        # Generate recommendations
        top_pick = strategy_weighted_players[0] if strategy_weighted_players else None
        alternatives = (
            strategy_weighted_players[1:4] if len(strategy_weighted_players) > 1 else []
        )

        # Generate detailed reasoning for top pick
        if top_pick:
            reasoning = _generate_pick_reasoning(
                top_pick, roster_analysis, strategy, current_round, consider_bye_weeks
            )
            top_pick["detailed_reasoning"] = reasoning

        # Generate alternative reasoning
        for alt in alternatives:
            alt_reasoning = _generate_pick_reasoning(
                alt,
                roster_analysis,
                strategy,
                current_round,
                consider_bye_weeks,
                is_alternative=True,
            )
            alt["detailed_reasoning"] = alt_reasoning

        # Round-specific strategic guidance
        draft_rules = draft_state.get("draft_state", {}).get("draft_rules", {})
        round_guidance = _get_round_specific_guidance(
            current_round, draft_rules, strategy
        )

        # Position-specific recommendations
        position_recs = _get_position_specific_recommendations(
            available_players, roster_analysis, strategy
        )

        logger.info(
            f"Draft pick suggestion completed in {time.time() - start_time:.2f} seconds"
        )
        return {
            "success": True,
            "recommendation": {
                "primary_pick": top_pick,
                "alternatives": alternatives,
                "strategy_used": strategy,
                "consider_bye_weeks": consider_bye_weeks,
            },
            "analysis": {
                "current_round": current_round,
                "round_type": available_analysis["analysis"]["round_type"],
                "total_options_analyzed": len(available_players),
                "team_analyzed": (
                    analysis_team.get("team_name")
                    if analysis_team
                    else "General (no specific team)"
                ),
            },
            "roster_analysis": roster_analysis,
            "strategic_guidance": {
                "round_guidance": round_guidance,
                "position_recommendations": position_recs,
                "bye_week_considerations": available_analysis["bye_week_analysis"],
            },
            "confidence_factors": {
                "high_confidence": (
                    top_pick["strategy_score"] > 50 if top_pick else False
                ),
                "clear_best_pick": (
                    (top_pick["strategy_score"] - alternatives[0]["strategy_score"])
                    > 10
                    if top_pick and alternatives
                    else False
                ),
                "positional_need_urgent": any(
                    need["urgency"] == "Critical"
                    for need in roster_analysis["position_needs"].values()
                ),
                "bye_week_conflicts": len(
                    available_analysis["bye_week_analysis"]["problematic_weeks"]
                )
                > 0,
            },
        }

    except Exception as e:
        logger.error(f"Error generating draft pick suggestion: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "suggestion_failed",
            "troubleshooting": {
                "problem": f"Failed to generate draft pick suggestion: {str(e)}",
                "next_steps": [
                    "1. Verify draft_state contains valid data",
                    "2. Check that available players analysis is working",
                    "3. Ensure strategy parameter is valid",
                    "4. Verify current team information is available",
                ],
            },
        }


def _analyze_roster_needs(
    draft_state: Dict[str, Any], current_team: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze current roster composition and identify needs"""

    # Standard roster requirements
    roster_requirements = {
        "QB": {"starters": 1, "recommended_depth": 2, "max_useful": 3},
        "RB": {
            "starters": 2,
            "recommended_depth": 4,
            "max_useful": 6,
        },  # 2 starters + FLEX
        "WR": {
            "starters": 2,
            "recommended_depth": 4,
            "max_useful": 6,
        },  # 2 starters + FLEX
        "TE": {"starters": 1, "recommended_depth": 2, "max_useful": 3},
        "K": {"starters": 1, "recommended_depth": 1, "max_useful": 2},
        "DST": {"starters": 1, "recommended_depth": 1, "max_useful": 2},
    }

    current_roster = {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": []}

    # Count current roster by position
    if current_team:
        team_name = current_team.get("team_name")
        picks = draft_state.get("picks", [])

        for pick in picks:
            # Handle both "team" and "column_team" fields (column_team from sheets data)
            pick_team = pick.get("column_team") or pick.get("team")
            if pick_team == team_name:
                position = pick.get("position", "").upper()
                if position in current_roster:
                    current_roster[position].append(pick)

    # Analyze needs for each position
    position_needs = {}
    for position, requirements in roster_requirements.items():
        current_count = len(current_roster[position])
        starters_needed = max(0, requirements["starters"] - current_count)
        depth_needed = max(0, requirements["recommended_depth"] - current_count)

        # Determine urgency
        if current_count == 0 and requirements["starters"] > 0:
            urgency = "Critical"
            urgency_multiplier = 2.0
        elif starters_needed > 0:
            urgency = "High"
            urgency_multiplier = 1.5
        elif depth_needed > 0:
            urgency = "Medium"
            urgency_multiplier = 1.2
        elif current_count < requirements["max_useful"]:
            urgency = "Low"
            urgency_multiplier = 1.0
        else:
            urgency = "None"
            urgency_multiplier = 0.8  # Already have enough

        position_needs[position] = {
            "current_count": current_count,
            "starters_needed": starters_needed,
            "depth_needed": depth_needed,
            "urgency": urgency,
            "urgency_multiplier": urgency_multiplier,
            "current_players": [
                p.get("player_name") or p.get("player", "")
                for p in current_roster[position]
            ],
        }

    return {
        "position_needs": position_needs,
        "current_roster": current_roster,
        "roster_balance_score": _calculate_roster_balance_score(
            current_roster, roster_requirements
        ),
    }


def _calculate_roster_balance_score(current_roster: Dict, requirements: Dict) -> float:
    """Calculate how balanced the current roster is (0-100)"""
    total_score = 0
    total_positions = 0

    for position, reqs in requirements.items():
        current_count = len(current_roster[position])
        optimal_count = reqs["recommended_depth"]

        # Score based on how close to optimal depth
        if current_count >= optimal_count:
            position_score = 100
        else:
            position_score = (current_count / optimal_count) * 100

        # Weight by position importance (starters need more weight)
        weight = reqs["starters"] * 2 + 1  # QB=3, RB=5, WR=5, TE=3, K=2, DST=2

        total_score += position_score * weight
        total_positions += weight

    return round(total_score / total_positions, 1) if total_positions > 0 else 0


def _calculate_strategy_multiplier(
    player: Dict, roster_analysis: Dict, strategy: str, current_round: int
) -> float:
    """Calculate strategy-specific multiplier for a player"""

    position = player["position"]
    tier_rank = player["value_metrics"]["tier_rank"]
    scarcity = player["scarcity_analysis"]["position_scarcity"]
    avg_rank = player["average_rank"]

    if strategy == "best_available":
        # Pure value play - highest ranked available
        if tier_rank <= 2:  # Elite/Tier 1
            return 1.8
        elif tier_rank <= 3:  # Tier 2
            return 1.4
        else:
            return 1.0

    elif strategy == "balanced":
        # Balance value with roster needs
        position_urgency = (
            roster_analysis["position_needs"].get(position, {}).get("urgency", "None")
        )

        if position_urgency == "Critical":
            return 1.6  # Must fill starter spots
        elif position_urgency == "High" and tier_rank <= 3:
            return 1.4  # Good value at needed position
        elif tier_rank <= 2:  # Elite talent
            return 1.3  # Always valuable
        elif position_urgency in ["Medium", "High"]:
            return 1.1  # Slight boost for roster needs
        else:
            return 1.0

    elif strategy == "upside":
        # Target high ceiling players, especially early in draft
        if current_round <= 5:  # Early rounds - still want elite talent
            if tier_rank <= 2:
                return 1.5
            elif scarcity == "High" and tier_rank <= 3:
                return 1.3  # Scarce position talent
            else:
                return 1.0
        else:  # Later rounds - swing for upside
            if avg_rank > 100 and player.get(
                "commentary"
            ):  # Sleeper pick with analysis
                return 1.4
            elif scarcity == "High":  # Positional upside
                return 1.2
            else:
                return 1.0

    elif strategy == "safe":
        # Target consistent, reliable players
        if tier_rank <= 3 and scarcity != "High":  # Avoid risky positions
            return 1.4
        elif position in ["RB", "WR"] and tier_rank <= 4:  # Safe skill positions
            return 1.2
        elif position in ["K", "DST"]:  # Don't reach for safe K/DST
            return 0.7
        else:
            return 1.0

    return 1.0


def _generate_pick_reasoning(
    player: Dict,
    roster_analysis: Dict,
    strategy: str,
    current_round: int,
    consider_bye_weeks: bool,
    is_alternative: bool = False,
) -> List[str]:
    """Generate detailed reasoning for a pick recommendation"""

    reasoning = []
    position = player["position"]
    name = player["name"]
    tier = player["value_metrics"]["tier"]
    avg_rank = player["average_rank"]
    strategy_score = player["strategy_score"]

    # Lead with recommendation type
    if is_alternative:
        reasoning.append(
            f"Alternative option: {name} ({position}) offers different strategic value"
        )
    else:
        reasoning.append(
            f"Primary recommendation: {name} ({position}) - Rank {avg_rank:.0f}"
        )

    # Value reasoning
    if tier in ["Elite", "Tier 1"]:
        reasoning.append(
            f"Excellent value - {tier} player still available at this pick"
        )
    elif tier == "Tier 2":
        reasoning.append(f"Good value - Solid {tier} option with reliable production")

    # Position need reasoning
    position_need = roster_analysis["position_needs"].get(position, {})
    urgency = position_need.get("urgency", "None")
    current_count = position_need.get("current_count", 0)

    if urgency == "Critical":
        reasoning.append(
            f"Critical need - You have {current_count} {position}s and need starters"
        )
    elif urgency == "High":
        reasoning.append(
            f"Important need - Helps fill starting lineup depth at {position}"
        )
    elif urgency == "Medium":
        reasoning.append(f"Depth play - Adds valuable {position} depth to your roster")

    # Strategy-specific reasoning
    if strategy == "best_available":
        reasoning.append("Best available player regardless of position needs")
    elif strategy == "balanced":
        if urgency in ["Critical", "High"]:
            reasoning.append("Perfect balance of value and roster need")
        else:
            reasoning.append("Best available player with roster construction in mind")
    elif strategy == "upside":
        if current_round <= 5:
            reasoning.append("High-ceiling player with league-winning potential")
        else:
            reasoning.append("Upside play - Could outperform ADP significantly")
    elif strategy == "safe":
        reasoning.append("Reliable, consistent production with low bust risk")

    # Scarcity reasoning
    scarcity = player["scarcity_analysis"]["position_scarcity"]
    pos_rank = player["value_metrics"]["positional_rank"]

    if scarcity == "High":
        reasoning.append(
            f"Positional scarcity - Only {pos_rank} quality {position}s left available"
        )
    elif position in ["TE", "QB"] and pos_rank <= 8:
        reasoning.append(
            f"Position timing - Good value for {position}{pos_rank} at this draft stage"
        )

    # Bye week reasoning
    if consider_bye_weeks:
        bye_week_severity = player["bye_week_analysis"]["conflict_severity"]
        bye_week = player["bye_week_analysis"]["bye_week"]

        if bye_week_severity == "High":
            reasoning.append(
                f"⚠️ Bye week concern - Week {bye_week} creates roster conflicts"
            )
        elif (
            bye_week_severity == "None"
            and player["bye_week_analysis"]["helps_bye_diversity"]
        ):
            reasoning.append(
                f"✓ Bye week help - Week {bye_week} improves roster flexibility"
            )

    # Final strategic note
    if strategy_score > 60:
        reasoning.append("Strong overall fit for your team and strategy")
    elif strategy_score > 40:
        reasoning.append("Solid pick that addresses multiple factors")
    else:
        reasoning.append("Reasonable option given current board state")

    return reasoning


def _get_round_specific_guidance(
    current_round: int, draft_rules: Dict, strategy: str
) -> Dict[str, Any]:
    """Provide round-specific strategic guidance"""

    auction_rounds = draft_rules.get("auction_rounds", [1, 2, 3])
    keeper_round = draft_rules.get("keeper_round", 4)

    if current_round in auction_rounds:
        return {
            "round_type": "auction",
            "key_focus": "Target specific players you want",
            "strategy_notes": [
                "Focus on elite talent and positional scarcity",
                "Don't worry about traditional draft value",
                "Target players that fit your long-term roster construction",
                "Consider which positions will be thin in snake rounds",
            ],
        }
    elif current_round == keeper_round:
        return {
            "round_type": "keeper",
            "key_focus": "Value opportunity if drafting",
            "strategy_notes": [
                "Limited participation creates value opportunities",
                "Good chance for above-ADP picks",
                "Fill gaps not covered by your keeper",
                "Consider positions that will be scarce later",
            ],
        }
    elif current_round <= 6:
        return {
            "round_type": "early_snake",
            "key_focus": "Secure elite talent and fill critical needs",
            "strategy_notes": [
                "Priority on RB/WR scarcity positions",
                "Avoid QB/TE/K/DST unless elite tier",
                "Build foundation with consistent producers",
                "Consider positional runs and timing",
            ],
        }
    elif current_round <= 12:
        return {
            "round_type": "mid_snake",
            "key_focus": "Balance starters and depth",
            "strategy_notes": [
                "Fill remaining starter needs",
                "Begin building bench depth",
                "Consider QB/TE if not addressed",
                "Target high-upside players in deeper positions",
            ],
        }
    else:
        return {
            "round_type": "late_snake",
            "key_focus": "Depth, upside, and late-round value",
            "strategy_notes": [
                "Target handcuffs and lottery tickets",
                "Fill K/DST if not done yet",
                "Look for breakout candidates",
                "Consider stashing injured players",
            ],
        }


def _get_position_specific_recommendations(
    available_players: List[Dict], roster_analysis: Dict, strategy: str
) -> Dict[str, Any]:
    """Get position-specific recommendations"""

    recommendations = {}

    for position in ["QB", "RB", "WR", "TE", "K", "DST"]:
        pos_players = [p for p in available_players if p["position"] == position][:3]
        position_need = roster_analysis["position_needs"].get(position, {})

        if pos_players:
            recommendations[position] = {
                "urgency": position_need.get("urgency", "None"),
                "current_count": position_need.get("current_count", 0),
                "top_available": [
                    {
                        "name": p["name"],
                        "rank": p["average_rank"],
                        "tier": p["value_metrics"]["tier"],
                        "value": p["value_metrics"]["overall_value"],
                    }
                    for p in pos_players
                ],
                "recommendation": _get_position_timing_rec(
                    position, position_need, pos_players, strategy
                ),
            }

    return recommendations


def _get_position_timing_rec(
    position: str, position_need: Dict, available_players: List[Dict], strategy: str
) -> str:
    """Get timing recommendation for a specific position"""

    urgency = position_need.get("urgency", "None")
    current_count = position_need.get("current_count", 0)
    best_available = available_players[0] if available_players else None

    if not best_available:
        return f"No quality {position}s available"

    best_tier = best_available["value_metrics"]["tier"]
    best_rank = best_available["average_rank"]

    if urgency == "Critical":
        return f"Draft now - Critical need and {best_available['name']} ({best_tier}) available"
    elif urgency == "High" and best_tier in ["Elite", "Tier 1", "Tier 2"]:
        return f"Strong consideration - {best_available['name']} fills need with good value"
    elif position in ["K", "DST"]:
        if best_rank < 150:
            return "Wait - Don't reach for K/DST this early"
        else:
            return f"Reasonable timing for {best_available['name']}"
    elif position == "QB" and current_count == 0:
        if best_tier in ["Elite", "Tier 1"]:
            return f"Consider now - {best_available['name']} is elite QB talent"
        elif best_rank > 100:
            return "Can wait - QB depth still available later"
        else:
            return f"Solid timing for {best_available['name']}"
    elif position == "TE" and current_count == 0:
        if best_tier in ["Elite", "Tier 1"]:
            return f"Consider now - Elite TE {best_available['name']} available"
        else:
            return "Can wait - TE streaming options available"
    else:
        if urgency in ["Medium", "High"]:
            return (
                f"Good depth option - {best_available['name']} adds roster flexibility"
            )
        else:
            return f"Optional - {best_available['name']} available if value aligns"
