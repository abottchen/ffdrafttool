"""Integration tests for scraper + adapter workflow."""

import pytest

from src.models.player import Position as OldPosition
from src.models.player_simple import Player as SimplePlayer
from src.services.scraper_adapter import ScraperAdapter
from src.services.web_scraper import FantasySharksScraper


class TestScraperIntegration:
    @pytest.mark.asyncio
    async def test_fantasy_sharks_to_simple_player_workflow(self):
        """Test complete workflow from FantasySharks scraper to simple players."""
        # This test uses the existing FantasySharks parsing logic but doesn't
        # make real network calls - it uses the mock data and parsing methods

        scraper = FantasySharksScraper()
        adapter = ScraperAdapter()

        # Mock some HTML that matches FantasySharks structure
        from bs4 import BeautifulSoup

        mock_html = """
        <table id="toolData">
            <tr><th>Rank</th><th>Name</th><th>Team</th><th>Bye</th></tr>
            <tr><th>Overall Rank</th><th>Player</th><th>Team</th><th>Bye Week</th></tr>
            <tr>
                <td>1</td>
                <td>4</td>
                <td>Allen, Josh</td>
                <td>BUF</td>
                <td>12</td>
                <td>300</td><td>4000</td><td>30</td><td>10</td><td>5</td>
                <td>500</td><td>5</td><td>1</td><td>25</td><td>0</td>
                <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
                <td>0</td><td>0</td><td>0</td><td>325.5</td>
            </tr>
            <tr>
                <td></td>
                <td>Elite dual-threat QB with rushing upside and strong arm.</td>
            </tr>
            <tr>
                <td>2</td>
                <td>8</td>
                <td>Jackson, Lamar</td>
                <td>BAL</td>
                <td>14</td>
                <td>280</td><td>3800</td><td>28</td><td>8</td><td>6</td>
                <td>800</td><td>8</td><td>2</td><td>45</td><td>0</td>
                <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
                <td>0</td><td>0</td><td>0</td><td>315.0</td>
            </tr>
        </table>
        """

        soup = BeautifulSoup(mock_html, "html.parser")
        table = soup.find("table", {"id": "toolData"})
        rows = table.find_all("tr")[2:]  # Skip headers

        # Use scraper's parsing methods to create old-style players
        old_players = []
        i = 0
        while i < len(rows):
            player = scraper._parse_player_row(
                rows[i], OldPosition.QB, len(old_players) + 1
            )
            if player:
                # Check for commentary in next row
                if i + 1 < len(rows):
                    commentary = scraper._extract_player_commentary(rows[i + 1])
                    if commentary:
                        player.commentary = commentary
                old_players.append(player)
            i += 1

        # Convert to simple players using adapter
        simple_players = adapter.convert_players(old_players)

        # Verify the conversion worked correctly
        assert len(simple_players) >= 2

        # Check first player (Josh Allen)
        josh = simple_players[0]
        assert isinstance(josh, SimplePlayer)
        assert josh.name == "Josh Allen"
        assert josh.team == "BUF"
        assert josh.position == "QB"
        assert josh.bye_week == 12
        assert josh.ranking == 1
        assert josh.projected_points == 99.0  # FantasySharks uses 100-rank formula
        assert "dual-threat" in josh.notes or "Elite" in josh.notes

        # Check second player (Lamar Jackson)
        lamar = simple_players[1]
        assert isinstance(lamar, SimplePlayer)
        assert lamar.name == "Lamar Jackson"
        assert lamar.team == "BAL"
        assert lamar.position == "QB"
        assert lamar.bye_week == 14
        assert lamar.ranking == 2
        assert lamar.projected_points == 98.0  # FantasySharks uses 100-rank formula

    def test_adapter_handles_scraper_output_format(self):
        """Test that adapter correctly handles the specific format from FantasySharks scraper."""
        adapter = ScraperAdapter()

        # Create old player in exactly the format that FantasySharks scraper creates
        from src.models.player import Player as OldPlayer
        from src.models.player import Position as OldPosition
        from src.models.player import RankingSource

        old_player = OldPlayer(
            name="Christian McCaffrey",
            position=OldPosition.RB,
            team="SF",
            bye_week=9,
            commentary="Elite RB1 with receiving upside when healthy.",
        )

        # FantasySharks scraper stores data as RankingSource.OTHER
        old_player.add_ranking(RankingSource.OTHER, 1, 285.2)

        # Convert using adapter
        simple_player = adapter.convert_player(old_player)

        # Verify all fields converted correctly
        assert simple_player.name == "Christian McCaffrey"
        assert simple_player.team == "SF"
        assert simple_player.position == "RB"
        assert simple_player.bye_week == 9
        assert simple_player.ranking == 1
        assert simple_player.projected_points == 285.2
        assert simple_player.notes == "Elite RB1 with receiving upside when healthy."

    def test_adapter_maintains_position_specific_data(self):
        """Test adapter works correctly for different position types."""
        adapter = ScraperAdapter()

        from src.models.player import Player as OldPlayer
        from src.models.player import Position as OldPosition
        from src.models.player import RankingSource

        # Test different positions that FantasySharks supports
        test_cases = [
            ("Travis Kelce", OldPosition.TE, "KC", 10, 1, 195.5),
            ("Cooper Kupp", OldPosition.WR, "LAR", 7, 2, 245.0),
            ("Justin Tucker", OldPosition.K, "BAL", 14, 1, 125.0),
            ("Buffalo Bills", OldPosition.DST, "BUF", 12, 3, 115.5),
        ]

        for name, position, team, bye, rank, points in test_cases:
            old_player = OldPlayer(
                name=name, position=position, team=team, bye_week=bye
            )
            old_player.add_ranking(RankingSource.OTHER, rank, points)

            simple_player = adapter.convert_player(old_player)

            assert simple_player.name == name
            assert (
                simple_player.position == position.value
            )  # Position enum value as string
            assert simple_player.team == team
            assert simple_player.bye_week == bye
            assert simple_player.ranking == rank
            assert simple_player.projected_points == points
