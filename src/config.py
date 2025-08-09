"""
Configuration settings for the Fantasy Football Draft Assistant.
"""

import json
from pathlib import Path


def load_config():
    """Load configuration from config.json file."""
    config_path = Path(__file__).parent.parent / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            "Please copy config.json.example to config.json and update with your settings."
        )

    with open(config_path, "r") as f:
        return json.load(f)


# Load configuration
_config = load_config()

# User Configuration
USER_OWNER_NAME = _config["draft"]["owner_name"]
"""
The owner name to use when interpreting first-person references.
When users say "I", "me", "my team", etc., the assistant will look for
this owner name in the draft data.

Set in config.json under draft.owner_name.
"""

# Draft Configuration
DEFAULT_SHEET_ID = _config["google_sheets"]["default_sheet_id"]
"""Default Google Sheet ID for draft tracking."""

DEFAULT_SHEET_RANGE = _config["google_sheets"]["default_range"]
"""Default range to read from the draft sheet."""

# Cache Configuration
RANKINGS_CACHE_HOURS = _config["cache"]["rankings_cache_hours"]
"""How many hours to cache player rankings data."""

DRAFT_CACHE_MINUTES = _config["cache"]["draft_cache_minutes"]
"""How many minutes to cache draft state data."""

DRAFT_STATE_CACHE_TTL_SECONDS = _config["cache"].get("draft_state_ttl_seconds", 60)
"""TTL in seconds for draft state cache (default: 60 seconds)."""

# Logging Configuration
LOG_LEVEL = _config.get("logging", {}).get("level", "INFO")
"""Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
