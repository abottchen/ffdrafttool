"""HTTP API service for tracker draft data."""

import logging
from typing import Dict, List

import aiohttp

logger = logging.getLogger(__name__)


class TrackerAPIService:
    """Service for making HTTP calls to the tracker API."""

    def __init__(self, base_url: str = "http://localhost:8175"):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def get_draft_state(self) -> Dict:
        """Fetch draft state from tracker API.

        Returns:
            Dict with teams array and other draft data

        Raises:
            aiohttp.ClientError: If API call fails
        """
        url = f"{self.base_url}/api/v1/draft-state"
        logger.info(f"Fetching draft state from {url}")

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(
                    f"Successfully fetched draft state with {len(data.get('teams', []))} teams"
                )
                return data

    async def get_owner_info(self, owner_id: int) -> Dict:
        """Fetch owner information by owner_id.

        Args:
            owner_id: The owner ID to lookup

        Returns:
            Dict with owner_name and team_name

        Raises:
            aiohttp.ClientError: If API call fails
        """
        url = f"{self.base_url}/api/v1/owners/{owner_id}"
        logger.debug(f"Fetching owner info for ID {owner_id} from {url}")

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(
                    f"Successfully fetched owner info: {data.get('owner_name')}"
                )
                return data

    async def get_all_players(self) -> List[Dict]:
        """Fetch all players from tracker API.

        Returns:
            List of player dictionaries with id, first_name, last_name, team, position

        Raises:
            aiohttp.ClientError: If API call fails
        """
        url = f"{self.base_url}/api/v1/players"
        logger.info(f"Fetching all players from {url}")

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"Successfully fetched {len(data)} players")
                return data
