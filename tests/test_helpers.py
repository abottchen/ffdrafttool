"""Test helper classes and utilities for Fantasy Football Draft Assistant tests."""

from typing import Any, Dict, List

from src.services.sheets_service import SheetsProvider


class MockSheetsProvider(SheetsProvider):
    """Mock sheets provider for testing"""

    def __init__(self):
        self.mock_data = {
            "test_sheet_123": {
                "Draft!A1:V24": [
                    ["Pick", "Team", "Player", "Position"],
                    ["1", "Team Alpha", "Christian McCaffrey", "RB"],
                    ["2", "Team Beta", "Tyreek Hill", "WR"],
                    ["3", "Team Gamma", "Justin Jefferson", "WR"],
                ]
            }
        }

    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Return mock sheet data"""
        if sheet_id in self.mock_data and range_name in self.mock_data[sheet_id]:
            return self.mock_data[sheet_id][range_name]
        return []

