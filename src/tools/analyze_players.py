import logging
from typing import Any, Dict, Optional

from src.config import USER_OWNER_NAME
from src.models.player import Position
from src.tools.player_rankings import get_player_rankings

logger = logging.getLogger(__name__)


def _extract_player_name_and_team(player_field: str) -> tuple[str, str]:
    """
    Extract player name and team from draft data format.

    Examples:
    - "Jahmyr Gibbs DET" -> ("Jahmyr Gibbs", "DET")
    - "Saquon Barkley NYG" -> ("Saquon Barkley", "NYG")
    - "Player Name" -> ("Player Name", "")

    Args:
        player_field: The player field from draft data

    Returns:
        tuple of (player_name, team_abbreviation)
    """
    if not player_field:
        return "", ""

    # Known NFL team abbreviations
    NFL_TEAMS = {
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAC",
        "JAX",
        "KC",
        "LAC",
        "LAR",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    }

    # Split by spaces and check if last part is a known team abbreviation
    parts = player_field.strip().split()
    if not parts:
        return "", ""

    # Check if the last part is a known NFL team abbreviation
    if len(parts) > 1 and parts[-1].upper() in NFL_TEAMS:
        team = parts[-1].upper()
        name = " ".join(parts[:-1])
        return name, team
    else:
        # No team found, return full string as name
        return player_field, ""


async def analyze_available_players(
    draft_state: Dict[str, Any],
    position_filter: Optional[str] = None,
    limit: int = 20,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Analyze available players with value metrics and scarcity.

    Args:
        draft_state: Current draft state with picks and team info
        position_filter: Optional position filter ("QB", "RB", "WR", "TE", "K", "DST")
        limit: Number of players to return (default: 20)
        force_refresh: If True, bypass cache and fetch fresh rankings data

    Returns:
        Dict containing analyzed players with value metrics, scarcity info, and recommendations
    """
    import time

    start_time = time.time()
    logger.info(
        f"Analyzing available players with position filter: {position_filter}, limit: {limit}, force_refresh: {force_refresh}"
    )

    try:
        # Parse position filter
        if position_filter:
            try:
                Position(position_filter.upper())
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid position filter: {position_filter}. Valid positions: QB, RB, WR, TE, K, DST",
                }

        # Extract drafted players and analyze current roster composition
        picks = draft_state.get("picks", [])
        drafted_players = set()
        current_roster = {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DST": []}
        bye_week_conflicts = {}  # bye_week -> {position: [players]}

        # Determine which team we're analyzing for - ALWAYS look for FF_OWNER's team by owner name
        teams = draft_state.get("teams", [])
        analysis_team = None  # The team we're providing analysis for (FF_OWNER's team)

        # Always try to find user's team by owner name (ignore current_team as it's who's on the clock)
        if teams:
            # Try to match by owner name (exact match first, then partial match)
            for team in teams:
                owner_name = team.get("owner", "").strip()
                if owner_name.lower() == USER_OWNER_NAME.lower():
                    analysis_team = team
                    logger.info(
                        f"Found FF_OWNER's team by exact owner match: {team.get('team_name')} (owner: {owner_name})"
                    )
                    break

            # If exact match fails, try partial match (in case of formatting differences)
            if not analysis_team:
                for team in teams:
                    owner_name = team.get("owner", "").strip()
                    if (
                        USER_OWNER_NAME.lower() in owner_name.lower()
                        or owner_name.lower() in USER_OWNER_NAME.lower()
                    ):
                        analysis_team = team
                        logger.info(
                            f"Found FF_OWNER's team by partial owner match: {team.get('team_name')} (owner: {owner_name})"
                        )
                        break

        if analysis_team:
            logger.info(
                f"Analyzing for FF_OWNER's team: {analysis_team.get('team_name')} (owner: {analysis_team.get('owner')})"
            )
        else:
            logger.info(
                f"Providing general analysis (no specific team identified for {USER_OWNER_NAME})"
            )

        for pick in picks:
            player_field = pick.get("player", "").strip()
            if player_field:
                # Extract player name and team from formats like "Jahmyr Gibbs DET" or "Jahmyr Gibbs"
                player_name, player_team = _extract_player_name_and_team(player_field)

                # Create a normalized key for comparison: "name|team"
                normalized_name = player_name.lower()
                # Remove team abbreviations in parentheses like "(BUF)" FIRST
                if "(" in normalized_name:
                    normalized_name = normalized_name.split("(")[0]
                normalized_name = (
                    normalized_name.replace(".", "").replace("'", "").replace("-", "")
                )
                normalized_name = (
                    normalized_name.replace("jr", "")
                    .replace("sr", "")
                    .replace("iii", "")
                    .replace("ii", "")
                )
                normalized_name = " ".join(normalized_name.split()).strip()

                # Create composite key to handle players with same name on different teams
                composite_key = (
                    f"{normalized_name}|{player_team.upper()}"
                    if player_team
                    else normalized_name
                )
                drafted_players.add(composite_key)

                logger.info(
                    f"DRAFT_DEBUG: Raw='{player_field}' -> Name='{player_name}' Team='{player_team}' -> Key='{composite_key}'"
                )

                # Track FF_OWNER's team roster for bye week analysis
                # Use column_team (actual column position) instead of team (snake draft logic)
                pick_team = pick.get("column_team") or pick.get("team")
                if analysis_team and pick_team == analysis_team.get("team_name"):
                    position = pick.get("position", "").upper()
                    bye_week = pick.get("bye_week", 0)

                    if position in current_roster:
                        current_roster[position].append(
                            {
                                "name": player_name,
                                "position": position,
                                "bye_week": bye_week,
                            }
                        )

                        # Track bye week conflicts
                        if bye_week not in bye_week_conflicts:
                            bye_week_conflicts[bye_week] = {}
                        if position not in bye_week_conflicts[bye_week]:
                            bye_week_conflicts[bye_week][position] = []
                        bye_week_conflicts[bye_week][position].append(player_name)

        logger.info(f"Found {len(drafted_players)} drafted players")
        if analysis_team:
            logger.info(
                f"Analyzing bye weeks for team: {analysis_team.get('team_name')}"
            )

        # Get current player rankings from all available sources
        ranking_sources = ["fantasysharks", "espn", "yahoo", "fantasypros"]
        rankings_result = await get_player_rankings(
            sources=ranking_sources,
            position=position_filter,
            limit=None,  # Get all players for analysis
            force_refresh=force_refresh,
        )

        if not rankings_result.get("success"):
            return {
                "success": False,
                "error": "Failed to fetch player rankings for analysis",
                "ranking_error": rankings_result.get("error"),
            }

        all_players = rankings_result["aggregated"]["players"]
        logger.info(f"Retrieved {len(all_players)} players from rankings")

        # Filter out drafted players
        available_players = []
        for player in all_players:
            # Clean the display name to remove team abbreviations
            clean_name = player["name"]
            # Remove team abbreviations in parentheses like "(BUF)"
            if "(" in clean_name:
                clean_name = clean_name.split("(")[0].strip()

            # Apply normalization for filtering comparison
            rankings_name = clean_name.lower()
            rankings_name = (
                rankings_name.replace(".", "").replace("'", "").replace("-", "")
            )
            rankings_name = (
                rankings_name.replace("jr", "")
                .replace("sr", "")
                .replace("iii", "")
                .replace("ii", "")
            )
            rankings_name = " ".join(rankings_name.split()).strip()

            # Create composite key for available player: "name|team"
            player_team = player.get("team", "").upper()
            available_composite_key = (
                f"{rankings_name}|{player_team}" if player_team else rankings_name
            )

            # Check if player is drafted using flexible team matching
            is_drafted = False

            # First check exact composite key match (for backwards compatibility)
            if available_composite_key in drafted_players:
                is_drafted = True
            # Then check name-only match (for cases where team info might be missing)
            elif rankings_name in drafted_players:
                is_drafted = True
            # Finally, check for team abbreviation variations (e.g., SF vs SFO)
            elif player_team:
                for drafted_key in drafted_players:
                    if "|" in drafted_key:
                        drafted_name, drafted_team = drafted_key.split("|", 1)
                        if drafted_name == rankings_name:
                            # Check if teams are compatible using substring matching
                            # This handles cases like SF/SFO, GB/GBP, NO/NOS, NE/NEP, TB/TBB
                            if (
                                drafted_team in player_team
                                or player_team in drafted_team
                                or (
                                    len(drafted_team) >= 2
                                    and len(player_team) >= 2
                                    and drafted_team[:2] == player_team[:2]
                                )
                            ):
                                is_drafted = True
                                break

            if not is_drafted:
                # Update the player object with the cleaned name
                player_copy = player.copy()
                player_copy["name"] = clean_name
                available_players.append(player_copy)
            else:
                logger.info(
                    f"Filtered out drafted player: {player['name']} -> '{clean_name}' (key: '{available_composite_key}')"
                )

        logger.info(
            f"Found {len(available_players)} available players after filtering drafted"
        )

        # Calculate positional scarcity and value metrics
        analyzed_players = []
        position_counts = {}

        # Count available players by position
        for player in available_players:
            pos = player["position"]
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Analyze each available player
        for player in available_players:
            pos = player["position"]
            avg_rank = player.get("average_rank", 999)
            avg_score = player.get("average_score", 0)

            # Calculate positional scarcity based on realistic fantasy value curves
            position_depth = position_counts.get(pos, 0)

            # Calculate positional rank among available players for this position
            same_pos_players = [p for p in available_players if p["position"] == pos]
            same_pos_players.sort(key=lambda p: p.get("average_rank", 999))
            pos_rank = next(
                (
                    i + 1
                    for i, p in enumerate(same_pos_players)
                    if p["name"] == player["name"]
                ),
                999,
            )

            # Position-specific scarcity based on real fantasy value curves
            if pos == "QB":
                # Only top 10 QBs worth drafting, massive drop-off after top 5
                if pos_rank <= 5:
                    scarcity_multiplier = 1.8  # Elite QB tier
                elif pos_rank <= 10:
                    scarcity_multiplier = 1.4  # QB1 tier
                elif pos_rank <= 20 and avg_score > 60:  # High upside rookies/breakouts
                    scarcity_multiplier = 1.1  # Upside plays
                else:
                    scarcity_multiplier = 0.8  # Likely undraftable

            elif pos == "RB":
                # Top 5 highly desirable, steep drop after ~30
                if pos_rank <= 5:
                    scarcity_multiplier = 1.6  # Elite RB tier
                elif pos_rank <= 15:
                    scarcity_multiplier = 1.3  # RB1/2 tier
                elif pos_rank <= 30:
                    scarcity_multiplier = 1.1  # Solid RB3/flex
                else:
                    scarcity_multiplier = 0.9  # Pedestrian/handcuff tier

            elif pos == "WR":
                # Deeper position, more even value distribution
                if pos_rank <= 10:
                    scarcity_multiplier = 1.4  # Elite WR tier
                elif pos_rank <= 25:
                    scarcity_multiplier = 1.2  # WR1/2 tier
                elif pos_rank <= 50:
                    scarcity_multiplier = 1.0  # Solid WR3/flex
                else:
                    scarcity_multiplier = 0.95  # Depth/bye week filler

            elif pos == "TE":
                # Very top-heavy position, huge drop after elite tier
                if pos_rank <= 3:
                    scarcity_multiplier = 2.0  # Elite TE (Kelce, Andrews tier)
                elif pos_rank <= 8:
                    scarcity_multiplier = 1.3  # TE1 tier
                elif pos_rank <= 15:
                    scarcity_multiplier = 1.0  # Streaming tier
                else:
                    scarcity_multiplier = 0.8  # Waiver wire fodder

            elif pos in ["K", "DST"]:
                # Don't draft until late rounds regardless of scarcity
                # Apply penalty for drafting too early
                if avg_rank < 150:  # Being drafted too early
                    scarcity_multiplier = 0.3  # Heavy penalty
                elif avg_rank < 200:  # Late round targets
                    scarcity_multiplier = 0.8  # Slight penalty
                else:
                    scarcity_multiplier = 1.0  # Appropriate timing
            else:
                scarcity_multiplier = 1.0

            # Bye week conflict analysis
            player_bye_week = player.get("bye_week", 0)
            bye_week_penalty = 1.0
            bye_week_conflicts_found = []

            if analysis_team and player_bye_week > 0:
                # Check for bye week conflicts with current roster
                conflicts_this_week = bye_week_conflicts.get(player_bye_week, {})

                # Define minimum roster requirements per position for bye weeks
                min_requirements = {
                    "QB": 1,  # Need 1 starting QB
                    "RB": 2,  # Need 2 starting RBs
                    "WR": 2,  # Need 2 starting WRs (could flex a 3rd)
                    "TE": 1,  # Need 1 starting TE
                    "K": 1,  # Need 1 starting K
                    "DST": 1,  # Need 1 starting DST
                }

                # Check if adding this player would create problematic conflicts
                position_conflicts = conflicts_this_week.get(pos, [])
                current_at_position = len(current_roster.get(pos, []))

                # Calculate conflict severity
                if pos in min_requirements:
                    min_needed = min_requirements[pos]
                    players_on_bye = len(position_conflicts)

                    # If we already have players on bye this week at this position
                    if players_on_bye > 0:
                        total_after_draft = current_at_position + 1
                        players_on_bye_after = players_on_bye + 1

                        # For skill positions (RB/WR), consider FLEX eligibility
                        if pos in ["RB", "WR"]:
                            # Check cross-position conflicts for FLEX consideration
                            rb_conflicts = len(conflicts_this_week.get("RB", []))
                            wr_conflicts = len(conflicts_this_week.get("WR", []))
                            total_skill_conflicts = rb_conflicts + wr_conflicts
                            if pos == "RB":
                                total_skill_conflicts += 1  # Adding this RB
                            else:  # WR
                                total_skill_conflicts += 1  # Adding this WR

                            total_skill_players = (
                                len(current_roster.get("RB", []))
                                + len(current_roster.get("WR", []))
                                + 1
                            )

                            # Need at least 3 skill players not on bye (2 RB + 2 WR + 1 FLEX)
                            if total_skill_conflicts >= total_skill_players - 2:
                                bye_week_penalty = 0.7  # Moderate penalty
                                bye_week_conflicts_found.append(
                                    f"FLEX conflict on bye week {player_bye_week}"
                                )
                            elif total_skill_conflicts >= total_skill_players - 3:
                                bye_week_penalty = 0.85  # Light penalty
                                bye_week_conflicts_found.append(
                                    f"Potential FLEX issue on bye week {player_bye_week}"
                                )
                        else:
                            # For non-skill positions, direct conflict check
                            if players_on_bye_after >= total_after_draft:
                                bye_week_penalty = (
                                    0.5  # Heavy penalty - complete positional shutdown
                                )
                                bye_week_conflicts_found.append(
                                    f"Complete {pos} bye week conflict on week {player_bye_week}"
                                )
                            elif players_on_bye_after >= min_needed:
                                bye_week_penalty = (
                                    0.75  # Moderate penalty - starter conflict
                                )
                                bye_week_conflicts_found.append(
                                    f"{pos} starter conflict on bye week {player_bye_week}"
                                )

                # Bonus for filling bye week gaps
                if (
                    player_bye_week not in bye_week_conflicts
                    or pos not in bye_week_conflicts.get(player_bye_week, {})
                ):
                    # This player helps with bye week diversity
                    if (
                        current_at_position < min_requirements.get(pos, 1) * 2
                    ):  # Still building depth
                        bye_week_penalty = 1.05  # Small bonus for bye week diversity

            # Value over replacement calculation
            # Lower average rank is better, so invert for value calculation
            rank_value = max(0, 200 - avg_rank) if avg_rank < 200 else 0

            # Combine ranking value with scarcity and bye week considerations
            overall_value = (rank_value * scarcity_multiplier * bye_week_penalty) + (
                avg_score * 0.1
            )

            # Tier analysis based on average rank
            if avg_rank <= 12:
                tier = "Elite"
                tier_rank = 1
            elif avg_rank <= 36:
                tier = "Tier 1"
                tier_rank = 2
            elif avg_rank <= 60:
                tier = "Tier 2"
                tier_rank = 3
            elif avg_rank <= 100:
                tier = "Tier 3"
                tier_rank = 4
            elif avg_rank <= 150:
                tier = "Tier 4"
                tier_rank = 5
            else:
                tier = "Deep"
                tier_rank = 6

            analyzed_player = {
                "name": player["name"],
                "position": pos,
                "team": player["team"],
                "bye_week": player["bye_week"],
                "rank": player.get("rank", avg_rank),
                "score": player.get("score", avg_score),
                "average_rank": avg_rank,
                "average_score": avg_score,
                "commentary": player.get("commentary"),
                # Value analysis
                "value_metrics": {
                    "overall_value": round(overall_value, 2),
                    "rank_value": round(rank_value, 2),
                    "scarcity_multiplier": round(scarcity_multiplier, 2),
                    "tier": tier,
                    "tier_rank": tier_rank,
                    "positional_rank": pos_rank,
                    "position_depth": position_depth,
                },
                # Scarcity analysis
                "scarcity_analysis": {
                    "position_scarcity": (
                        "High"
                        if scarcity_multiplier > 1.3
                        else "Medium" if scarcity_multiplier > 1.1 else "Low"
                    ),
                    "available_at_position": position_depth,
                    "position_rank": pos_rank,
                    "is_positional_run": pos_rank <= 5
                    and position_depth < 20,  # Top 5 at shallow position
                },
                # Bye week analysis
                "bye_week_analysis": {
                    "bye_week": player_bye_week,
                    "bye_week_penalty": round(bye_week_penalty, 3),
                    "conflict_severity": (
                        "High"
                        if bye_week_penalty <= 0.6
                        else (
                            "Medium"
                            if bye_week_penalty <= 0.8
                            else "Low" if bye_week_penalty < 1.0 else "None"
                        )
                    ),
                    "conflicts_found": bye_week_conflicts_found,
                    "helps_bye_diversity": bye_week_penalty > 1.0,
                },
            }

            analyzed_players.append(analyzed_player)

        # Sort by overall value (descending)
        analyzed_players.sort(
            key=lambda p: p["value_metrics"]["overall_value"], reverse=True
        )

        # Apply limit
        if limit > 0:
            analyzed_players = analyzed_players[:limit]

        # Generate analysis summary - calculate current round from picks and teams
        # But respect existing current_round in draft_state if provided (for tests)
        existing_round = draft_state.get("draft_state", {}).get("current_round")
        if existing_round:
            current_round = existing_round
            logger.info(
                f"Using existing current_round from draft_state: {current_round}"
            )
        else:
            total_picks = len(draft_state.get("picks", []))
            teams = draft_state.get("teams", [])
            total_teams = len(teams) if teams else 10
            current_pick = total_picks + 1
            current_round = ((current_pick - 1) // total_teams) + 1
            logger.info(
                f"Calculated current round: pick {current_pick}, round {current_round}, {total_teams} teams"
            )

        # Determine round strategy
        draft_rules = draft_state.get("draft_state", {}).get("draft_rules", {})
        auction_rounds = draft_rules.get("auction_rounds", [1, 2, 3])
        keeper_round = draft_rules.get("keeper_round", 4)

        if current_round in auction_rounds:
            round_type = "auction"
            strategy_note = "Focus on elite talent and positional scarcity. Target players you specifically want."
        elif current_round == keeper_round:
            round_type = "keeper"
            strategy_note = (
                "Limited participation. Good opportunity for value if you're drafting."
            )
        else:
            round_type = "snake"
            strategy_note = (
                "Traditional snake draft. Consider positional needs and upcoming picks."
            )

        # Position breakdown
        position_breakdown = {}
        for player in analyzed_players:
            pos = player["position"]
            if pos not in position_breakdown:
                position_breakdown[pos] = {
                    "count": 0,
                    "best_available": None,
                    "scarcity_level": "Low",
                }

            position_breakdown[pos]["count"] += 1
            if position_breakdown[pos]["best_available"] is None:
                position_breakdown[pos]["best_available"] = {
                    "name": player["name"],
                    "rank": player["average_rank"],
                    "value": player["value_metrics"]["overall_value"],
                }

            # Update scarcity level based on best player at position
            if player == analyzed_players[0]:  # First player in value order
                scarcity = player["scarcity_analysis"]["position_scarcity"]
                position_breakdown[pos]["scarcity_level"] = scarcity

        # Analyze bye week landscape for recommendations
        bye_week_summary = {}
        problematic_bye_weeks = []

        if analysis_team:
            # Identify problematic bye weeks
            for bye_week, conflicts in bye_week_conflicts.items():
                total_conflicts = sum(len(players) for players in conflicts.values())
                if total_conflicts >= 2:  # 2+ players on same bye week
                    problematic_bye_weeks.append(bye_week)
                    bye_week_summary[bye_week] = {
                        "total_players": total_conflicts,
                        "positions_affected": list(conflicts.keys()),
                        "severity": "High" if total_conflicts >= 3 else "Medium",
                    }

        logger.info(
            f"analyze_available_players completed in {time.time() - start_time:.2f} seconds"
        )
        return {
            "success": True,
            "analysis": {
                "total_available": len(available_players),
                "analyzed_count": len(analyzed_players),
                "current_round": current_round,
                "round_type": round_type,
                "strategy_note": strategy_note,
                "team_analyzed": (
                    analysis_team.get("team_name")
                    if analysis_team
                    else "General (no specific team)"
                ),
            },
            "players": analyzed_players,
            "position_breakdown": position_breakdown,
            "bye_week_analysis": {
                "current_conflicts": bye_week_summary,
                "problematic_weeks": problematic_bye_weeks,
                "roster_summary": {
                    pos: len(players)
                    for pos, players in current_roster.items()
                    if players
                },
            },
            "filters": {"position_filter": position_filter, "limit": limit},
            "recommendations": {
                "high_value_targets": [
                    p
                    for p in analyzed_players[:5]
                    if p["value_metrics"]["overall_value"] > 50
                ],
                "scarcity_picks": [
                    p
                    for p in analyzed_players
                    if p["scarcity_analysis"]["position_scarcity"] == "High"
                ][:3],
                "tier_breaks": [
                    p for p in analyzed_players if p["value_metrics"]["tier_rank"] <= 2
                ][:5],
                "bye_week_safe": [
                    p
                    for p in analyzed_players
                    if p["bye_week_analysis"]["conflict_severity"] == "None"
                ][:5],
                "bye_week_helpers": [
                    p
                    for p in analyzed_players
                    if p["bye_week_analysis"]["helps_bye_diversity"]
                ][:3],
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing available players: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "analysis_failed",
            "troubleshooting": {
                "problem": f"Failed to analyze available players: {str(e)}",
                "next_steps": [
                    "1. Verify draft_state contains valid picks data",
                    "2. Check that player rankings are available",
                    "3. Ensure network connection for fetching rankings",
                    "4. Verify position filter is valid if specified",
                ],
            },
        }
