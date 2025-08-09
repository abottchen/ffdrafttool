import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for web scraping"""

    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


class WebScraper(ABC):
    """Abstract base class for web scrapers"""

    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()

    async def fetch_page(self, url: str) -> str:
        """Fetch a web page with retries"""
        headers = {"User-Agent": self.config.user_agent}

        for attempt in range(self.config.retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as response:
                        response.raise_for_status()
                        return await response.text()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise

    @abstractmethod
    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape rankings from the website"""
        pass


class ESPNScraper(WebScraper):
    """Scraper for ESPN fantasy football rankings"""

    BASE_URL = "https://www.espn.com/fantasy/football/ffl/rankings"

    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape ESPN rankings"""
        # TODO: Implement actual ESPN scraping logic
        # This would parse the ESPN rankings page
        logger.info("Scraping ESPN rankings...")

        # For now, return mock data
        return await self._get_mock_data(position)

    async def _get_mock_data(self, position: Optional[str] = None) -> List[Player]:
        """Return mock data for testing"""
        mock_players = [
            ("Christian McCaffrey", "RB", "SF", 9, 1, 99.5),
            ("Tyreek Hill", "WR", "MIA", 10, 2, 98.0),
            ("Justin Jefferson", "WR", "MIN", 13, 3, 97.5),
            ("Josh Allen", "QB", "BUF", 13, 4, 96.0),
            ("Austin Ekeler", "RB", "LAC", 5, 5, 95.5),
        ]

        players = []
        for name, pos, team, bye, rank, score in mock_players:
            if position and pos != position:
                continue

            player = Player(
                name=name,
                team=team,
                position=pos,
                bye_week=bye,
                ranking=rank,
                projected_points=score,
                notes="ESPN mock data",
            )
            players.append(player)

        return players


class YahooScraper(WebScraper):
    """Scraper for Yahoo fantasy football rankings"""

    BASE_URL = "https://football.fantasysports.yahoo.com/f1/draftanalysis"

    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape Yahoo rankings"""
        # TODO: Implement actual Yahoo scraping logic
        logger.info("Scraping Yahoo rankings...")

        # For now, return mock data
        return await self._get_mock_data(position)

    async def _get_mock_data(self, position: Optional[str] = None) -> List[Player]:
        """Return mock data for testing"""
        mock_players = [
            ("Christian McCaffrey", "RB", "SF", 9, 2, 98.5),
            ("Justin Jefferson", "WR", "MIN", 13, 1, 99.0),
            ("Tyreek Hill", "WR", "MIA", 10, 3, 97.0),
            ("Josh Allen", "QB", "BUF", 13, 5, 95.0),
            ("Austin Ekeler", "RB", "LAC", 5, 4, 96.0),
        ]

        players = []
        for name, pos, team, bye, rank, score in mock_players:
            if position and pos != position:
                continue

            player = Player(
                name=name,
                team=team,
                position=pos,
                bye_week=bye,
                ranking=rank,
                projected_points=score,
                notes="Yahoo mock data",
            )
            players.append(player)

        return players


class FantasyProsScraper(WebScraper):
    """Scraper for FantasyPros consensus rankings"""

    BASE_URL = "https://www.fantasypros.com/nfl/rankings/consensus-cheatsheets.php"

    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape FantasyPros consensus rankings"""
        # TODO: Implement actual FantasyPros scraping logic
        logger.info("Scraping FantasyPros rankings...")

        # For now, return mock data
        return await self._get_mock_data(position)

    async def _get_mock_data(self, position: Optional[str] = None) -> List[Player]:
        """Return mock data for testing"""
        mock_players = [
            ("Christian McCaffrey", "RB", "SF", 9, 1, 99.0),
            ("Justin Jefferson", "WR", "MIN", 13, 2, 98.5),
            ("Tyreek Hill", "WR", "MIA", 10, 3, 97.5),
            ("Josh Allen", "QB", "BUF", 13, 4, 96.5),
            ("Austin Ekeler", "RB", "LAC", 5, 5, 95.0),
        ]

        players = []
        for name, pos, team, bye, rank, score in mock_players:
            if position and pos != position:
                continue

            player = Player(
                name=name,
                team=team,
                position=pos,
                bye_week=bye,
                ranking=rank,
                projected_points=score,
                notes="FantasyPros mock data",
            )
            players.append(player)

        return players


class FantasySharksScraper(WebScraper):
    """Scraper for FantasySharks rankings and projections"""

    BASE_URL = "https://www.fantasysharks.com/apps/Projections/SeasonProjections.php"

    POSITION_PARAMS = {
        "QB": "QB",
        "RB": "RB",
        "WR": "WR",
        "TE": "TE",
        "K": "PK",  # FantasySharks uses "PK" for kickers
        "DST": "D",  # FantasySharks uses "D" for defenses
    }

    async def scrape_rankings(self, position: Optional[str] = None) -> List[Player]:
        """Scrape FantasySharks rankings for specified position"""
        if position and position not in self.POSITION_PARAMS:
            raise ValueError(
                f"Position {position} not supported by FantasySharks scraper"
            )

        logger.info(
            f"Scraping FantasySharks rankings for {position if position else 'all positions'}..."
        )

        players = []
        positions_to_scrape = (
            [position] if position else list(self.POSITION_PARAMS.keys())
        )

        for pos in positions_to_scrape:
            try:
                pos_players = await self._scrape_position(pos)
                players.extend(pos_players)
            except Exception as e:
                logger.error(f"Failed to scrape {pos} from FantasySharks: {str(e)}")

        return players

    async def _scrape_position(self, position: str) -> List[Player]:
        """Scrape rankings for a specific position"""
        url = f"{self.BASE_URL}?l=2&pos={self.POSITION_PARAMS[position]}&RosterSize=&SalaryCap=&Rookie=false&Comments=true"

        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            # Find the main rankings table - FantasySharks uses id="toolData"
            table = soup.find("table", {"id": "toolData"})
            if not table:
                # Try alternative selectors
                table = soup.find("table", {"class": "datatable"}) or soup.find(
                    "table", {"id": "projections"}
                )
                if not table:
                    table = soup.find("table")

            if not table:
                logger.warning(f"Could not find rankings table for {position}")
                # Debug: Show what we found
                all_tables = soup.find_all("table")
                logger.debug(f"Found {len(all_tables)} tables total")
                return []

            logger.debug(f"Found table for {position} scraping")

            players = []
            rows = table.find_all("tr")[
                2:
            ]  # Skip first 2 header rows for FantasySharks

            logger.debug(f"Found {len(rows)} data rows in table")

            i = 0
            while i < len(
                rows
            ):  # Process all rows looking for player + commentary pairs
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
                                logger.debug(
                                    f"Added commentary for {player.name}: {commentary[:50]}..."
                                )

                        players.append(player)
                        logger.debug(f"Row {i+1}: Parsed {player.name}")
                    else:
                        logger.debug(f"Row {i+1}: No player parsed")

                except Exception as e:
                    logger.warning(
                        f"Failed to parse row {i+1} for {position}: {str(e)}"
                    )

                i += 1

            logger.info(
                f"Successfully scraped {len(players)} {position} players from FantasySharks"
            )
            return players

        except Exception as e:
            logger.error(f"Error scraping FantasySharks {position}: {str(e)}")
            return []

    def _parse_player_row(self, row, position: str, rank: int) -> Optional[Player]:
        """Parse a single player row from the table"""
        cells = row.find_all(["td", "th"])
        logger.debug(f"Row {rank}: Found {len(cells)} cells")

        if len(cells) < 4:
            logger.debug(f"Row {rank}: Too few cells ({len(cells)})")
            return None

        try:
            # FantasySharks structure: Rank, ADP, Name, Team, Bye, [stats...]
            # Based on debug output: Row 3: 24 cells: ['1', '4', 'Allen, Josh', 'BUF', '7']

            if len(cells) < 5:
                logger.debug(f"Row {rank}: Not enough cells for FantasySharks format")
                return None

            # Extract data from known positions
            try:
                # rank_text = cells[0].get_text(strip=True)  # Position 0: Rank
                # adp_text = cells[1].get_text(strip=True)   # Position 1: ADP

                # Extract name text while excluding <sup> tags (rookie indicators)
                name_cell = cells[2]
                # Remove any <sup> tags before extracting text
                for sup_tag in name_cell.find_all("sup"):
                    sup_tag.decompose()  # Remove the tag completely
                name_text = name_cell.get_text(strip=True)  # Position 2: Name (cleaned)

                team_text = cells[3].get_text(strip=True)  # Position 3: Team
                bye_text = cells[4].get_text(strip=True)  # Position 4: Bye

                # Check for injury information in the name cell
                injury_info = self._extract_injury_info(name_cell)

                # Validate we have actual data
                if not name_text or not team_text:
                    logger.debug(f"Row {rank}: Missing name or team data")
                    return None

                # Check if this is a header row or statistical summary row
                if self._is_header_or_stats_row(name_text, team_text, bye_text):
                    logger.debug(f"Row {rank}: Detected header/stats row, skipping")
                    return None

                # Clean up name (handle "Last, First" format)
                if "," in name_text:
                    # Convert "Allen, Josh" to "Josh Allen"
                    parts = name_text.split(",")
                    if len(parts) == 2:
                        name = f"{parts[1].strip()} {parts[0].strip()}"
                    else:
                        name = name_text.strip()
                else:
                    name = name_text.strip()

                # Extract team
                team = team_text.strip()
                if not team or len(team) > 4:  # Team should be 2-4 characters
                    team = "UNK"
                    # Log error when team cannot be determined from rankings data
                    logger.error(
                        f"Unable to extract NFL team for player '{name}' from FantasySharks rankings. "
                        f"Team data was: '{team_text}'. Player will be marked with team 'UNK'. "
                        f"This may affect player matching and analysis."
                    )

                # Extract bye week
                bye_week = 1
                try:
                    if bye_text.isdigit():
                        bye_week = int(bye_text)
                        if not (1 <= bye_week <= 18):
                            bye_week = 1
                except (ValueError, TypeError):
                    bye_week = 1

                logger.debug(f"Row {rank}: Parsed {name} ({team}) Bye:{bye_week}")
                if injury_info:
                    logger.debug(f"Row {rank}: Injury info: {injury_info}")

            except (IndexError, AttributeError) as e:
                logger.debug(f"Row {rank}: Error accessing cell data: {str(e)}")
                return None

            # Extract projected fantasy points from FantasySharks table
            # Projected points are always in the last cell, regardless of position
            # (QBs have 24 cells, WRs have 23 cells, etc.)
            projected_points = 0.0
            try:
                if (
                    len(cells) >= 6
                ):  # Make sure we have at least basic cells (rank, adp, name, team, bye, stats...)
                    points_text = cells[-1].get_text(
                        strip=True
                    )  # Last cell is always FantasyPoints
                    if (
                        points_text
                        and points_text.replace(".", "").replace("-", "").isdigit()
                    ):
                        projected_points = float(points_text)
                        logger.debug(
                            f"Row {rank}: Extracted projected points: {projected_points} from last cell (index {len(cells)-1})"
                        )
                    else:
                        logger.debug(
                            f"Row {rank}: Could not parse projected points from last cell '{points_text}'"
                        )
                else:
                    logger.debug(
                        f"Row {rank}: Not enough cells for projected points parsing ({len(cells)} cells)"
                    )
            except (IndexError, ValueError, AttributeError) as e:
                logger.debug(f"Row {rank}: Error parsing projected points: {str(e)}")
                projected_points = 0.0

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

            # Create new Pydantic Player object
            player = Player(
                name=name,
                team=team,
                position=position,
                bye_week=bye_week,
                ranking=rank,
                projected_points=projected_points,
                injury_status=injury_status,
                notes=notes,
            )

            return player

        except Exception as e:
            logger.warning(f"Failed to parse player row: {str(e)}")
            return None

    def _is_header_or_stats_row(
        self, name_text: str, team_text: str, bye_text: str
    ) -> bool:
        """
        Detect if a row is a header or statistical summary row that should be skipped.

        Args:
            name_text: Text from the name column
            team_text: Text from the team column
            bye_text: Text from the bye week column

        Returns:
            True if the row should be skipped (header/stats row)
        """
        # Common header indicators that are exact matches or at start/end
        exact_header_names = [
            "Name",
            "TDs",
            "TD",
            "Pass",
            "Rush",
            "Rec",
            "Pts",
            "Proj",
            "Rank",
            "ADP",
            "Position",
        ]

        # Check for exact header matches
        if name_text in exact_header_names:
            return True

        # Check for "Player" only if it's the whole word or at the start
        if name_text == "Player" or name_text.startswith("Player "):
            return True

        # Check if name contains parentheses indicating a header like "Name (Team)"
        if "(" in name_text and ")" in name_text:
            return True

        # Check for statistical data patterns in team column
        # Like "TD1-9" which indicates touchdown statistics
        if team_text and ("TD" in team_text or "-" in team_text):
            # But make sure it's not a legitimate hyphenated team name
            if len(team_text) > 4 or any(char.isdigit() for char in team_text):
                return True

        # Check for non-numeric bye weeks (headers often have text here)
        if bye_text and not bye_text.isdigit():
            # But allow empty bye weeks for some positions
            if bye_text not in ["", "-", "N/A"]:
                return True

        return False

    def _extract_player_commentary(self, row) -> Optional[str]:
        """Extract player commentary from a commentary row"""
        try:
            cells = row.find_all(["td", "th"])

            # Commentary rows typically have 2 cells: empty + commentary text
            if len(cells) == 2:
                commentary_text = cells[1].get_text(strip=True)

                # Make sure it's actually commentary (long text, not just a tier marker)
                if (
                    commentary_text
                    and len(commentary_text) > 50
                    and not commentary_text.startswith("Tier")
                ):
                    return commentary_text

            return None

        except Exception as e:
            logger.debug(f"Failed to extract commentary: {str(e)}")
            return None

    def _extract_injury_info(self, cell) -> Optional[Dict[str, any]]:
        """Extract injury information from a table cell containing injury img tags"""
        try:
            # Look for injury images in the cell
            injury_imgs = cell.find_all("img", src=re.compile(r"injured\d*\.gif"))

            if not injury_imgs:
                return None

            for img in injury_imgs:
                # Extract injury details from ONMOUSEOVER attribute
                onmouseover = img.get("onmouseover", "")
                if not onmouseover:
                    continue

                # Parse the popup content using regex
                # Example: popup("&lt;b&gt; Out&lt;/b&gt; Expected back Preseason Week 2")
                popup_match = re.search(
                    r'popup\(["\']([^"\']+)["\']', onmouseover, re.IGNORECASE
                )
                if not popup_match:
                    continue

                popup_content = popup_match.group(1)
                # Decode HTML entities
                popup_content = (
                    popup_content.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&quot;", '"')
                )

                # Extract injury details
                injury_details = self._parse_injury_details(popup_content)
                if injury_details:
                    logger.debug(f"Extracted injury info: {injury_details}")
                    return injury_details

            return None

        except Exception as e:
            logger.debug(f"Failed to extract injury info: {str(e)}")
            return None

    def _parse_injury_details(self, popup_content: str) -> Optional[Dict[str, any]]:
        """Parse injury details from popup content and classify severity"""
        try:
            # Remove HTML tags
            clean_content = re.sub(r"<[^>]+>", "", popup_content).strip()

            if not clean_content:
                return None

            # Determine injury status based on keywords
            content_lower = clean_content.lower()

            injury_status = InjuryStatus.QUESTIONABLE  # Default
            is_long_term = False

            if "out" in content_lower:
                injury_status = InjuryStatus.OUT
                # Check for long-term indicators (but exclude preseason)
                if (
                    any(
                        indicator in content_lower
                        for indicator in [
                            "season",
                            "year",
                            "months",
                            "week 8",
                            "week 9",
                            "week 10",
                            "week 11",
                            "week 12",
                            "week 13",
                            "week 14",
                            "week 15",
                            "week 16",
                            "week 17",
                            "week 18",
                            "playoffs",
                        ]
                    )
                    and "preseason" not in content_lower
                ):
                    is_long_term = True
            elif "doubtful" in content_lower:
                injury_status = InjuryStatus.DOUBTFUL
            elif "questionable" in content_lower:
                injury_status = InjuryStatus.QUESTIONABLE
            elif "probable" in content_lower:
                injury_status = InjuryStatus.PROBABLE

            return {
                "status": injury_status,
                "details": clean_content,
                "is_long_term": is_long_term,
            }

        except Exception as e:
            logger.debug(f"Failed to parse injury details: {str(e)}")
            return None


class InjuryReportScraper(WebScraper):
    """Scraper for NFL injury reports"""

    BASE_URL = "https://www.espn.com/nfl/injuries"

    async def scrape_injury_reports(self) -> Dict[str, InjuryStatus]:
        """Scrape current injury reports"""
        # TODO: Implement actual injury report scraping
        logger.info("Scraping injury reports...")

        # For now, return mock data
        return {
            "Saquon Barkley": InjuryStatus.QUESTIONABLE,
            "Cooper Kupp": InjuryStatus.DOUBTFUL,
            "Mike Evans": InjuryStatus.PROBABLE,
        }
