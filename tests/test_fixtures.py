"""Test fixtures for Fantasy Football Draft Assistant tests."""

from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.web_scraper import WebScraper


class FixtureFantasySharksScraper(WebScraper):
    """
    Mock FantasySharks scraper that uses HTML fixtures instead of live web requests.

    This is used in tests to avoid 403 Forbidden errors in CI environments.
    The fixture should be updated annually before draft season if needed.
    """

    def __init__(self):
        super().__init__()
        self.fixtures_path = Path(__file__).parent / "fixtures"

    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape rankings using HTML fixtures instead of web requests."""
        if not position:
            # For simplicity, just return QB data when no position specified
            position = "QB"

        # Map position to fixture file
        fixture_files = {
            "QB": "fantasy_sharks_qb.html",
            "RB": "fantasy_sharks_qb.html",  # Reuse QB fixture for other positions in tests
            "WR": "fantasy_sharks_qb.html",
            "TE": "fantasy_sharks_qb.html",
            "K": "fantasy_sharks_qb.html",
            "DST": "fantasy_sharks_qb.html",
        }

        fixture_file = fixture_files.get(position)
        if not fixture_file:
            return []

        fixture_path = self.fixtures_path / fixture_file
        if not fixture_path.exists():
            return []

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            table = soup.find("table", {"id": "toolData"})
            if not table:
                return []

            players = []
            rows = table.find_all("tr")[2:]  # Skip header rows

            i = 0
            while i < len(rows):
                try:
                    current_row = rows[i]
                    player = self._parse_player_row(
                        current_row, position, len(players) + 1
                    )

                    if player:
                        # Look for commentary in the next row
                        if i + 1 < len(rows):
                            next_row = rows[i + 1]
                            commentary = self._extract_player_commentary(next_row)
                            if commentary:
                                # Update notes with additional commentary
                                if player.notes:
                                    player.notes = f"{player.notes} | {commentary}"
                                else:
                                    player.notes = commentary

                        players.append(player)

                except Exception:
                    pass  # Skip failed rows

                i += 1

            return players

        except Exception:
            return []

    def _parse_player_row(self, row, position: str, rank: int) -> Optional[Player]:
        """Parse a single player row from the fixture table."""
        try:
            cells = row.find_all(["td", "th"])

            if len(cells) < 5:
                return None

            # Extract name text while excluding <sup> tags
            name_cell = cells[2]
            for sup_tag in name_cell.find_all("sup"):
                sup_tag.decompose()
            name_text = name_cell.get_text(strip=True)

            team_text = cells[3].get_text(strip=True)
            bye_text = cells[4].get_text(strip=True)

            # Check for injury information
            injury_info = self._extract_injury_info(name_cell)

            if not name_text or not team_text:
                return None

            # Clean up name (handle "Last, First" format)
            if "," in name_text:
                parts = name_text.split(",")
                if len(parts) == 2:
                    name = f"{parts[1].strip()} {parts[0].strip()}"
                else:
                    name = name_text.strip()
            else:
                name = name_text.strip()

            team = team_text.strip()
            if not team or len(team) > 4:
                team = "UNK"

            bye_week = 1
            try:
                if bye_text.isdigit():
                    bye_week = int(bye_text)
                    if not (1 <= bye_week <= 18):
                        bye_week = 1
            except (ValueError, TypeError):
                bye_week = 1

            # Create player with injury status and notes
            injury_status = (
                injury_info.get("status", InjuryStatus.HEALTHY)
                if injury_info
                else InjuryStatus.HEALTHY
            )

            # Prepare notes with injury details if available
            notes = ""
            if injury_info and injury_info.get("details"):
                notes = f"Injury: {injury_info['details']}"

            # Calculate projected points
            score = max(0, 100 - rank)

            # Create new Pydantic Player object
            player = Player(
                name=name,
                team=team,
                position=position,
                bye_week=bye_week,
                ranking=rank,
                projected_points=float(score),
                injury_status=injury_status,
                notes=notes,
            )

            return player

        except Exception:
            return None

    def _extract_player_commentary(self, row) -> Optional[str]:
        """Extract player commentary from a commentary row."""
        try:
            cells = row.find_all(["td", "th"])

            if len(cells) == 1 and cells[0].get("colspan"):
                commentary_text = cells[0].get_text(strip=True)
                if commentary_text and len(commentary_text) > 20:
                    return commentary_text

            return None

        except Exception:
            return None

    def _extract_injury_info(self, cell) -> Optional[Dict[str, any]]:
        """Extract injury information from a table cell containing injury img tags."""
        try:
            injury_imgs = cell.find_all("img", src=lambda x: x and "injured" in x)

            if not injury_imgs:
                return None

            for img in injury_imgs:
                onmouseover = img.get("onmouseover", "")
                if not onmouseover:
                    continue

                # Parse injury status from popup
                if "Out" in onmouseover:
                    return {
                        "status": InjuryStatus.OUT,
                        "details": "Out - Expected back Week 1",
                        "is_long_term": False,
                    }
                elif "Doubtful" in onmouseover:
                    return {
                        "status": InjuryStatus.DOUBTFUL,
                        "details": "Doubtful for this week",
                        "is_long_term": False,
                    }
                elif "Questionable" in onmouseover:
                    return {
                        "status": InjuryStatus.QUESTIONABLE,
                        "details": "Questionable for this week",
                        "is_long_term": False,
                    }

            return None

        except Exception:
            return None
