import logging
from typing import Dict, List, Optional

from ..models.player import Player, Position
from .web_scraper import (
    ESPNScraper,
    FantasyProsScraper,
    InjuryReportScraper,
    WebScraper,
    YahooScraper,
)

logger = logging.getLogger(__name__)


class RankingsService:
    """Service for aggregating rankings from multiple web scrapers"""

    def __init__(self):
        self.scrapers: Dict[str, WebScraper] = {
            "ESPN": ESPNScraper(),
            "Yahoo": YahooScraper(),
            "FantasyPros": FantasyProsScraper(),
        }
        self.injury_scraper = InjuryReportScraper()

    async def get_aggregated_rankings(
        self,
        sources: List[str],
        position: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Player]:
        """Get aggregated rankings from specified sources"""
        all_players: Dict[str, Player] = {}

        # Convert position string to enum if provided
        position_enum = None
        if position:
            try:
                position_enum = Position(position)
            except ValueError:
                logger.warning(f"Invalid position: {position}")

        # Fetch from each scraper
        for source in sources:
            if source not in self.scrapers:
                logger.warning(f"Unknown source: {source}")
                continue

            scraper = self.scrapers[source]
            players = await scraper.scrape_rankings(position_enum)

            # Merge player data
            for player in players:
                key = f"{player.name}_{player.team}"
                if key in all_players:
                    # Merge rankings
                    for ranking_source, ranking_data in player.rankings.items():
                        all_players[key].rankings[ranking_source] = ranking_data
                else:
                    all_players[key] = player

        # Get injury reports and update player statuses
        try:
            injury_reports = await self.injury_scraper.scrape_injury_reports()
            for player in all_players.values():
                if player.name in injury_reports:
                    player.update_injury_status(injury_reports[player.name])
        except Exception as e:
            logger.warning(f"Failed to fetch injury reports: {e}")

        # Sort by average rank
        sorted_players = sorted(
            all_players.values(),
            key=lambda p: p.average_rank if p.average_rank else float("inf"),
        )

        # Apply limit if specified
        if limit:
            sorted_players = sorted_players[:limit]

        return sorted_players
