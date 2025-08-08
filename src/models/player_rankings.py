"""PlayerRankings cache model for in-memory storage of player data."""

from datetime import datetime
from typing import Dict, List, Optional, Set

from .player_simple import Player


class PlayerRankings:
    """Container for cached rankings data by position."""
    
    def __init__(self):
        """Initialize empty cache."""
        self.position_data: Dict[str, List[Player]] = {}
        self.last_updated: Dict[str, datetime] = {}

    def set_position_data(self, position: str, players: List[Player]) -> None:
        """Set player data for a position and update timestamp."""
        self.position_data[position] = players.copy()
        self.last_updated[position] = datetime.now()

    def get_position_data(self, position: str) -> Optional[List[Player]]:
        """Get player data for a position, or None if not cached."""
        return self.position_data.get(position)

    def has_position_data(self, position: str) -> bool:
        """Check if data is cached for a position."""
        return position in self.position_data

    def search_players(
        self, 
        last_name: str = None, 
        first_name: str = None,
        team: str = None, 
        position: str = None
    ) -> List[Player]:
        """Search for players across all cached positions.
        
        Args:
            last_name: Player's last name (case insensitive)
            first_name: Player's first name (case insensitive)
            team: NFL team abbreviation (case insensitive)
            position: Position filter (case insensitive)
            
        Returns:
            List of matching players (deduplicated)
        """
        results: Set[Player] = set()
        
        # If position specified, only search that position's cache
        positions_to_search = [position.upper()] if position else self.position_data.keys()
        
        for pos in positions_to_search:
            if pos not in self.position_data:
                continue
                
            for player in self.position_data[pos]:
                # Check position match if specified
                if position and player.position.upper() != position.upper():
                    continue
                    
                # Check team match if specified
                if team and player.team.upper() != team.upper():
                    continue
                    
                # Check name matches if specified
                player_name_parts = player.name.lower().split()
                
                if last_name:
                    # Check if last name matches any part of player name
                    if not any(last_name.lower() in part for part in player_name_parts):
                        continue
                        
                if first_name:
                    # Check if first name matches any part of player name
                    if not any(first_name.lower() in part for part in player_name_parts):
                        continue
                
                results.add(player)
        
        return list(results)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.position_data.clear()
        self.last_updated.clear()

    def get_all_positions(self) -> List[str]:
        """Get list of all cached positions."""
        return list(self.position_data.keys())