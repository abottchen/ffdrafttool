#!/usr/bin/env python3
"""
Test player rankings caching functionality.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.mcp_tools import _rankings_cache, clear_rankings_cache, get_player_rankings


class TestRankingsCache:
    """Test suite for player rankings caching"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Clear cache before each test"""
        clear_rankings_cache()
        yield
        clear_rankings_cache()

    @pytest.fixture
    def mock_scraper_results(self):
        """Mock scraper results for testing"""
        return [
            {
                "name": "Player One",
                "position": "QB",
                "team": "KC",
                "bye_week": 10,
                "rankings": {"fantasysharks": {"rank": 1, "score": 95.0}},
            },
            {
                "name": "Player Two",
                "position": "RB",
                "team": "SF",
                "bye_week": 9,
                "rankings": {"fantasysharks": {"rank": 2, "score": 92.0}},
            },
        ]

    @pytest.mark.asyncio
    async def test_initial_fetch_populates_cache(self, mock_scraper_results):
        """Test that initial fetch populates the cache"""

        # Mock all scrapers
        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers to return data
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # First call should fetch fresh data
            result = await get_player_rankings(["fantasysharks"])

            assert result["success"] is True
            assert "from_cache" not in result  # First call is not from cache

            # Cache should be populated
            assert _rankings_cache["data"] is not None
            assert _rankings_cache["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_subsequent_calls_use_cache(self, mock_scraper_results):
        """Test that subsequent calls use cached data"""

        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # First call
            result1 = await get_player_rankings(["fantasysharks"])

            # Second call should use cache
            result2 = await get_player_rankings(["fantasysharks"])

            assert result2["from_cache"] is True
            assert result2["aggregated"]["count"] == result1["aggregated"]["count"]

            # Scrapers should only be called once
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                assert mock_instance.scrape_rankings.call_count <= 1

    @pytest.mark.asyncio
    async def test_position_filter_uses_cache(self, mock_scraper_results):
        """Test that position filtering works with cached data"""

        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # First call without filter to populate cache
            await get_player_rankings(["fantasysharks"])

            # Second call with position filter should use cache
            result_qb = await get_player_rankings(["fantasysharks"], position="QB")

            assert result_qb["from_cache"] is True
            assert result_qb["position"] == "QB"
            assert all(
                p["position"] == "QB" for p in result_qb["aggregated"]["players"]
            )

            # Scrapers should only be called once
            MockSharks.return_value.scrape_rankings.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, mock_scraper_results):
        """Test that force_refresh bypasses the cache"""

        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # First call
            await get_player_rankings(["fantasysharks"])

            # Second call with force_refresh should fetch fresh data
            result = await get_player_rankings(["fantasysharks"], force_refresh=True)

            assert "from_cache" not in result

            # Scrapers should be called twice
            assert MockSharks.return_value.scrape_rankings.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_expiration(self, mock_scraper_results):
        """Test that cache expires after duration"""

        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # First call
            await get_player_rankings(["fantasysharks"])

            # Manually expire the cache
            _rankings_cache["timestamp"] = datetime.now() - timedelta(hours=25)

            # Next call should fetch fresh data
            result = await get_player_rankings(["fantasysharks"])

            assert "from_cache" not in result
            assert MockSharks.return_value.scrape_rankings.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_cache_function(self, mock_scraper_results):
        """Test that clear_rankings_cache works correctly"""

        with (
            patch("tools.mcp_tools.FantasySharksScraper") as MockSharks,
            patch("tools.mcp_tools.ESPNScraper") as MockESPN,
            patch("tools.mcp_tools.YahooScraper") as MockYahoo,
            patch("tools.mcp_tools.FantasyProsScraper") as MockPros,
        ):

            # Setup mock scrapers
            for MockScraper in [MockSharks, MockESPN, MockYahoo, MockPros]:
                mock_instance = MockScraper.return_value
                mock_instance.scrape_rankings = AsyncMock(
                    return_value=mock_scraper_results
                )

            # Populate cache
            await get_player_rankings(["fantasysharks"])
            assert _rankings_cache["data"] is not None

            # Clear cache
            clear_rankings_cache()

            # Cache should be empty
            assert _rankings_cache["data"] is None
            assert _rankings_cache["timestamp"] is None

            # Next call should fetch fresh data
            result = await get_player_rankings(["fantasysharks"])
            assert "from_cache" not in result


if __name__ == "__main__":
    pytest.main([__file__])
