"""Abstract base class for Google Sheets draft format parsers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.models.draft_state_simple import DraftState


class SheetParser(ABC):
    """Abstract base class defining the interface for draft format parsers.
    
    Each parser handles a specific Google Sheets format (Dan, Adam, etc.)
    and converts the raw sheet data into a standardized DraftState object.
    """

    @abstractmethod
    async def parse_draft_data(
        self, 
        sheet_data: List[List], 
        rankings_cache: Optional[Dict] = None
    ) -> DraftState:
        """Parse raw Google Sheets data into DraftState object.
        
        Args:
            sheet_data: Raw 2D list from Google Sheets API
            rankings_cache: Optional player rankings for team lookup
            
        Returns:
            DraftState object with picks and team information
            
        Raises:
            ValueError: If sheet data doesn't match expected format
            ParseError: If sheet data is malformed
        """
        pass

    @abstractmethod
    def detect_format(self, sheet_data: List[List]) -> bool:
        """Validate that sheet data matches this parser's expected format.
        
        Args:
            sheet_data: Raw 2D list from Google Sheets API
            
        Returns:
            True if sheet data matches this parser's format, False otherwise
        """
        pass

    def _normalize_player_name(self, name: str) -> str:
        """Normalize player name for comparison (shared utility).
        
        Args:
            name: Raw player name from sheet
            
        Returns:
            Normalized player name for matching
        """
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


class ParseError(Exception):
    """Raised when sheet data cannot be parsed in the expected format."""
    pass