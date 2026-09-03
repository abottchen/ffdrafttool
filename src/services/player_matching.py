"""Helpers for matching players and positions across data sources.

Dan's draft sheet and the FantasySharks rankings describe the same players with
different vocabularies. These helpers translate both into a common form so
drafted players can be recognized in the rankings.
"""

# Position labels that differ from the rankings vocabulary (QB/RB/WR/TE/K/DST).
# Dan's sheet populates its Pos column from a Data tab that labels defenses
# "D/ST".
POSITION_ALIASES = {
    "D/ST": "DST",
    "DEF": "DST",
}


def normalize_position(position: str) -> str:
    """Normalize a position label to the vocabulary the rankings use.

    Args:
        position: Raw position label from a draft source

    Returns:
        Uppercased position with known aliases resolved; empty string for a
        missing label
    """
    if not position:
        return ""

    normalized = position.strip().upper()
    return POSITION_ALIASES.get(normalized, normalized)


def normalize_player_name(name: str) -> str:
    """Normalize a player name for comparison across sources."""
    normalized = name.lower()
    # Remove common punctuation and suffixes
    normalized = normalized.replace(".", "").replace("'", "").replace("-", "")
    normalized = (
        normalized.replace(" jr", "")
        .replace(" sr", "")
        .replace(" iii", "")
        .replace(" ii", "")
        .replace(" iv", "")
    )
    return " ".join(normalized.split()).strip()


def player_match_key(name: str, team: str, position: str) -> str:
    """Build a key identifying one player across data sources.

    Defenses are keyed by NFL team rather than by name: Dan's sheet records
    "Texans D/ST" while the rankings say "Houston Texans", so their names never
    match. Every other player is keyed by normalized name.

    Args:
        name: Player name as the source spells it
        team: NFL team abbreviation
        position: Position label from the same source

    Returns:
        Key that is equal for the same player from different sources
    """
    if normalize_position(position) == "DST":
        return f"DST:{team.strip().upper()}"

    return normalize_player_name(name)
