"""Auction state tool implementation.

Exposes the live auction data the tracker API provides: per-team budgets and
maximum bids, the player currently on the block, and the nomination order.

This is tracker-only. Dan's draft is a snake format with no budgets or
nominations, so the tool refuses any other configured format.
"""

import logging
from typing import Any, Dict, Optional

from src.config import DRAFT_FORMAT, _config
from src.services.team_mapping import (
    normalize_position_for_rankings,
    normalize_team_abbreviation,
)
from src.services.tracker_api_service import TrackerAPIService

logger = logging.getLogger(__name__)


def _tracker_base_url() -> str:
    """Get the tracker API base URL from configuration."""
    tracker_config = _config["draft"]["formats"].get("tracker", {})
    return tracker_config.get("base_url", "http://localhost:8175")


def _resolve_nomination(
    nominated: Optional[Dict[str, Any]],
    player_lookup: Dict[int, Dict[str, Any]],
    owner_names: Dict[int, str],
) -> Optional[Dict[str, Any]]:
    """Turn the tracker's ID-based nomination into names the client can use."""
    if not nominated:
        return None

    player_info = player_lookup.get(nominated["player_id"])
    if player_info:
        player = {
            "name": f"{player_info['first_name']} {player_info['last_name']}",
            "team": normalize_team_abbreviation(player_info["team"], source="tracker"),
            "position": normalize_position_for_rankings(player_info["position"]),
        }
    else:
        logger.warning(
            f"Nominated player ID {nominated['player_id']} not found in players list"
        )
        player = None

    return {
        "player": player,
        "current_bid": nominated.get("current_bid"),
        "current_bidder": owner_names.get(nominated.get("current_bidder_id")),
        "nominating_owner": owner_names.get(nominated.get("nominating_owner_id")),
    }


async def get_auction_state() -> Dict[str, Any]:
    """
    Get live auction state: team budgets, max bids, and the current nomination.

    Returns:
        Dict with per-team budgets, the nominated player, and nomination order,
        or an error dict the client can surface.
    """
    import time

    start_time = time.time()
    logger.info("Getting auction state from tracker API")

    if DRAFT_FORMAT != "tracker":
        return {
            "success": False,
            "error": (
                f"Auction state is only available for the tracker format, "
                f"but the configured draft format is '{DRAFT_FORMAT}'."
            ),
            "error_type": "unsupported_format",
            "draft_format": DRAFT_FORMAT,
        }

    try:
        api_service = TrackerAPIService(_tracker_base_url())

        draft_state = await api_service.get_draft_state()
        players_raw = await api_service.get_all_players()
        player_lookup = {p["id"]: p for p in players_raw}

        teams_raw = draft_state.get("teams", [])

        # Resolve every owner ID that appears anywhere in the auction state
        owner_ids = {team["owner_id"] for team in teams_raw}
        for key in ("next_to_nominate", "up_next"):
            if draft_state.get(key) is not None:
                owner_ids.add(draft_state[key])
        nominated_raw = draft_state.get("nominated")
        if nominated_raw:
            for key in ("current_bidder_id", "nominating_owner_id"):
                if nominated_raw.get(key) is not None:
                    owner_ids.add(nominated_raw[key])

        owner_names: Dict[int, str] = {}
        owner_teams: Dict[int, str] = {}
        for owner_id in sorted(owner_ids):
            owner_info = await api_service.get_owner_info(owner_id)
            owner_names[owner_id] = owner_info["owner_name"]
            owner_teams[owner_id] = owner_info["team_name"]

        teams = [
            {
                "owner": owner_names.get(team["owner_id"], f"Owner {team['owner_id']}"),
                "team_name": owner_teams.get(team["owner_id"]),
                "budget_remaining": team.get("budget_remaining"),
                "max_bid": team.get("max_bid"),
                "roster_size": len(team.get("picks", [])),
            }
            for team in teams_raw
        ]

        result = {
            "success": True,
            "teams": teams,
            "nominated": _resolve_nomination(nominated_raw, player_lookup, owner_names),
            "next_to_nominate": owner_names.get(draft_state.get("next_to_nominate")),
            "up_next": owner_names.get(draft_state.get("up_next")),
        }

        logger.info(
            f"get_auction_state completed in {time.time() - start_time:.2f} seconds "
            f"for {len(teams)} teams"
        )
        return result

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error fetching auction state from tracker API: {error_message}")

        return {
            "success": False,
            "error": error_message,
            "error_type": "api_access_failed",
            "source": "tracker_api",
            "troubleshooting": {
                "problem": f"Could not reach the draft tracker: {error_message}",
                "solution": f"Confirm the tracker is running at {_tracker_base_url()}",
                "next_steps": [
                    "1. Verify the tracker application is started",
                    "2. Check draft.formats.tracker.base_url in config.json",
                    "3. Retry the request",
                ],
            },
        }
