"""Team abbreviation mapping between rankings sources and Google Sheets format."""

from typing import Dict

# Mapping from rankings data team abbreviations to Google Sheets format
# Based on analysis of actual data from FantasySharks rankings
RANKINGS_TO_SHEETS_MAPPING: Dict[str, str] = {
    # Standard NFL teams that match (no mapping needed for these)
    "ARI": "ARI",  # Arizona Cardinals
    "ATL": "ATL",  # Atlanta Falcons
    "BAL": "BAL",  # Baltimore Ravens
    "BUF": "BUF",  # Buffalo Bills
    "CAR": "CAR",  # Carolina Panthers
    "CHI": "CHI",  # Chicago Bears
    "CIN": "CIN",  # Cincinnati Bengals
    "CLE": "CLE",  # Cleveland Browns
    "DAL": "DAL",  # Dallas Cowboys
    "DEN": "DEN",  # Denver Broncos
    "DET": "DET",  # Detroit Lions
    "HOU": "HOU",  # Houston Texans
    "IND": "IND",  # Indianapolis Colts
    "JAC": "JAC",  # Jacksonville Jaguars (sometimes JAX in sheets)
    "LAC": "LAC",  # Los Angeles Chargers
    "LAR": "LAR",  # Los Angeles Rams
    "MIA": "MIA",  # Miami Dolphins
    "MIN": "MIN",  # Minnesota Vikings
    "NYG": "NYG",  # New York Giants
    "NYJ": "NYJ",  # New York Jets
    "PHI": "PHI",  # Philadelphia Eagles
    "PIT": "PIT",  # Pittsburgh Steelers
    "SEA": "SEA",  # Seattle Seahawks
    "TEN": "TEN",  # Tennessee Titans
    "WAS": "WAS",  # Washington Commanders
    # Teams with different abbreviations in rankings vs sheets
    "GBP": "GB",  # Green Bay Packers (rankings: GBP, sheets: GB)
    "KCC": "KC",  # Kansas City Chiefs (rankings: KCC, sheets: KC)
    "LVR": "LV",  # Las Vegas Raiders (rankings: LVR, sheets: LV)
    "NEP": "NE",  # New England Patriots (rankings: NEP, sheets: NE)
    "NOS": "NO",  # New Orleans Saints (rankings: NOS, sheets: NO)
    "SFO": "SF",  # San Francisco 49ers (rankings: SFO, sheets: SF)
    "TBB": "TB",  # Tampa Bay Buccaneers (rankings: TBB, sheets: TB)
    # Special cases to filter out (not actual teams)
    "FA": None,  # Free Agent - not a real team (if it appears)
}


def normalize_team_abbreviation(team_abbrev: str, source: str = "rankings") -> str:
    """
    Normalize team abbreviation to Google Sheets format.

    Args:
        team_abbrev: The team abbreviation to normalize
        source: The source of the abbreviation ("rankings" or "sheets")

    Returns:
        Normalized team abbreviation in Google Sheets format, or "UNK" if cannot be mapped
    """
    if not team_abbrev or team_abbrev == "UNK":
        return "UNK"

    team_upper = team_abbrev.upper().strip()

    if source == "rankings":
        # Map from rankings format to sheets format
        mapped_team = RANKINGS_TO_SHEETS_MAPPING.get(team_upper)

        if mapped_team is None:  # Explicitly mapped to None (invalid team)
            return "UNK"
        elif mapped_team:  # Successfully mapped
            return mapped_team
        else:  # Not in mapping, assume it's already in correct format
            return team_upper

    # If source is "sheets" or unknown, assume it's already in correct format
    return team_upper


def get_all_valid_sheet_teams() -> set[str]:
    """
    Get all valid NFL team abbreviations in Google Sheets format.

    Returns:
        Set of valid team abbreviations
    """
    return set(
        abbrev for abbrev in RANKINGS_TO_SHEETS_MAPPING.values() if abbrev is not None
    )


def is_valid_team_abbreviation(team_abbrev: str) -> bool:
    """
    Check if a team abbreviation is valid.

    Args:
        team_abbrev: Team abbreviation to check

    Returns:
        True if it's a valid NFL team abbreviation
    """
    if not team_abbrev or team_abbrev == "UNK":
        return False

    valid_teams = get_all_valid_sheet_teams()
    return team_abbrev.upper() in valid_teams


def normalize_position_for_rankings(position: str) -> str:
    """
    Normalize position string for rankings lookup.

    Maps various defense position formats to the standard DST format
    expected by the rankings scraper.

    Args:
        position: Position string from draft data (e.g., "D/ST", "DEF", "D")

    Returns:
        Normalized position string for rankings lookup
    """
    position_upper = position.upper().strip()

    # Map defense variations to DST (which FantasySharks expects)
    if position_upper in ["D/ST", "DEF", "D", "DST"]:
        return "DST"

    # Return other positions as-is
    return position_upper
