import pytest

from src.models.player import Position, RankingSource
from src.services.web_scraper import (
    ESPNScraper,
    FantasyProsScraper,
    FantasySharksScraper,
    ScraperConfig,
    YahooScraper,
)


class TestWebScrapers:
    @pytest.mark.asyncio
    async def test_espn_scraper_mock_data(self):
        """Test ESPN scraper returns mock data"""
        scraper = ESPNScraper()
        players = await scraper.scrape_rankings()

        assert len(players) > 0
        assert all(RankingSource.ESPN in p.rankings for p in players)

    @pytest.mark.asyncio
    async def test_yahoo_scraper_mock_data(self):
        """Test Yahoo scraper returns mock data"""
        scraper = YahooScraper()
        players = await scraper.scrape_rankings()

        assert len(players) > 0
        assert all(RankingSource.YAHOO in p.rankings for p in players)

    @pytest.mark.asyncio
    async def test_scraper_position_filter(self):
        """Test position filtering works"""
        scraper = ESPNScraper()
        rb_players = await scraper.scrape_rankings(position=Position.RB)

        assert all(p.position == Position.RB for p in rb_players)

    @pytest.mark.asyncio
    async def test_scraper_config(self):
        """Test scraper configuration"""
        config = ScraperConfig(
            user_agent="Test Agent", timeout=60, retry_attempts=5, retry_delay=2.0
        )
        scraper = ESPNScraper(config)

        assert scraper.config.user_agent == "Test Agent"
        assert scraper.config.timeout == 60
        assert scraper.config.retry_attempts == 5
        assert scraper.config.retry_delay == 2.0

    @pytest.mark.asyncio
    async def test_fantasy_pros_scraper(self):
        """Test FantasyPros scraper returns mock data"""
        scraper = FantasyProsScraper()
        players = await scraper.scrape_rankings()

        assert len(players) > 0
        assert all(RankingSource.FANTASYPROS in p.rankings for p in players)

    @pytest.mark.asyncio
    async def test_fantasy_sharks_scraper_structure(self):
        """Test FantasySharks scraper basic structure"""
        scraper = FantasySharksScraper()

        # Test position parameter mapping
        assert scraper.POSITION_PARAMS[Position.QB] == "QB"
        assert scraper.POSITION_PARAMS[Position.RB] == "RB"
        assert scraper.POSITION_PARAMS[Position.WR] == "WR"
        assert scraper.POSITION_PARAMS[Position.TE] == "TE"
        assert scraper.POSITION_PARAMS[Position.K] == "PK"  # FantasySharks uses PK
        assert scraper.POSITION_PARAMS[Position.DST] == "D"  # FantasySharks uses D

    @pytest.mark.asyncio
    async def test_fantasy_sharks_scraper_position_validation(self):
        """Test FantasySharks scraper validates positions correctly"""
        scraper = FantasySharksScraper()

        # Test valid positions
        for position in [
            Position.QB,
            Position.RB,
            Position.WR,
            Position.TE,
            Position.K,
            Position.DST,
        ]:
            # Should not raise an exception
            try:
                # We're not actually making network calls, just testing validation
                url = f"{scraper.BASE_URL}?l=2&pos={scraper.POSITION_PARAMS[position]}&RosterSize=&SalaryCap=&Rookie=false&Comments=true"
                assert scraper.POSITION_PARAMS[position] in url
            except Exception:
                pytest.fail(f"Position {position} should be valid")

        # Test invalid position
        with pytest.raises(ValueError):
            await scraper.scrape_rankings(
                Position.FLEX
            )  # FLEX not supported by FantasySharks

    @pytest.mark.asyncio
    async def test_fantasy_sharks_name_parsing(self):
        """Test FantasySharks name parsing logic"""
        scraper = FantasySharksScraper()

        # Test "Last, First" format conversion
        from bs4 import BeautifulSoup

        # Mock a table row with "Last, First" format
        html = """
        <tr>
            <td>1</td>
            <td>4</td>
            <td>Allen, Josh</td>
            <td>BUF</td>
            <td>7</td>
            <td>300</td><td>4000</td><td>30</td><td>10</td><td>5</td>
            <td>500</td><td>5</td><td>1</td><td>25</td><td>0</td>
            <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
            <td>0</td><td>0</td><td>0</td><td>450</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")

        player = scraper._parse_player_row(row, Position.QB, 1)

        assert player is not None
        assert (
            player.name == "Josh Allen"
        )  # Should convert "Allen, Josh" to "Josh Allen"
        assert player.team == "BUF"
        assert player.bye_week == 7
        assert player.position == Position.QB

    @pytest.mark.asyncio
    async def test_fantasy_sharks_commentary_extraction(self):
        """Test FantasySharks commentary extraction logic"""
        scraper = FantasySharksScraper()

        # Mock a commentary row
        from bs4 import BeautifulSoup

        html = """
        <tr>
            <td></td>
            <td>The second overall selection in the 2024 draft, Daniels took the league by storm last season, rocketing into the upper echelon of fantasy quarterbacks with an impressive QB5 showing and capturing well-deserved Offensive Rookie of the Year honors.</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")

        commentary = scraper._extract_player_commentary(row)

        assert commentary is not None
        assert "second overall selection" in commentary
        assert len(commentary) > 50  # Should be substantial text

        # Test non-commentary row (tier marker)
        tier_html = """
        <tr>
            <td></td>
            <td>Tier 2</td>
        </tr>
        """
        soup = BeautifulSoup(tier_html, "html.parser")
        tier_row = soup.find("tr")

        tier_commentary = scraper._extract_player_commentary(tier_row)
        assert tier_commentary is None  # Should ignore tier markers
    
    def test_fantasy_sharks_header_detection(self):
        """Test that FantasySharks scraper properly detects and skips header rows."""
        scraper = FantasySharksScraper()
        
        # Test cases for header/stats row detection
        test_cases = [
            # (name, team, bye, should_be_skipped)
            ("TDs", "TD1-9", "1", True),  # Statistical data row
            ("Name (Team)", "", "Bye", True),  # Header row with parentheses
            ("Name", "Team", "Bye", True),  # Column headers
            ("Pass", "ATT", "1", True),  # Passing stats header
            ("Rec", "TD10-15", "2", True),  # Receiving stats with numbers
            ("Josh Allen", "BUF", "7", False),  # Valid player
            ("Patrick Mahomes", "KC", "10", False),  # Valid player
            ("Christian McCaffrey", "SF", "9", False),  # Valid player
        ]
        
        for name, team, bye, should_skip in test_cases:
            result = scraper._is_header_or_stats_row(name, team, bye)
            assert result == should_skip, (
                f"Expected {should_skip} for '{name}'/'{team}'/'{bye}', but got {result}"
            )
    
    def test_fantasy_sharks_edge_cases(self):
        """Test edge cases for header detection."""
        scraper = FantasySharksScraper()
        
        # Edge cases that should NOT be skipped
        edge_cases = [
            ("John Player", "LAR", "8", False),  # Name ending with "Player" 
            ("D.K. Metcalf", "SEA", "5", False),  # Name with periods
            ("Geno Smith", "", "", False),  # Empty team/bye (handled elsewhere)
            ("Mike Williams", "NYJ", "-", False),  # Dash as bye week indicator
        ]
        
        for name, team, bye, should_skip in edge_cases:
            result = scraper._is_header_or_stats_row(name, team, bye)
            assert result == should_skip, (
                f"Expected {should_skip} for '{name}'/'{team}'/'{bye}', but got {result}"
            )


class TestRankingsIntegration:
    @pytest.mark.asyncio
    async def test_multiple_scrapers_aggregate_rankings(self):
        """Test that rankings from multiple sources can be aggregated"""
        espn_scraper = ESPNScraper()
        yahoo_scraper = YahooScraper()

        espn_players = await espn_scraper.scrape_rankings()
        yahoo_players = await yahoo_scraper.scrape_rankings()

        # Find a common player
        espn_mccaffrey = next(p for p in espn_players if "McCaffrey" in p.name)
        yahoo_mccaffrey = next(p for p in yahoo_players if "McCaffrey" in p.name)

        # They should be the same player but with different rankings
        assert espn_mccaffrey.name == yahoo_mccaffrey.name
        assert espn_mccaffrey.team == yahoo_mccaffrey.team

        # ESPN and Yahoo might have different rankings
        espn_rank = espn_mccaffrey.rankings[RankingSource.ESPN]["rank"]
        yahoo_rank = yahoo_mccaffrey.rankings[RankingSource.YAHOO]["rank"]

        # Rankings exist but might differ
        assert espn_rank > 0
        assert yahoo_rank > 0
