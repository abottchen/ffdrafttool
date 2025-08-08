"""CSV-based sheets provider for comprehensive integration testing."""

import csv
from pathlib import Path
from typing import Any, List

from src.services.sheets_service import SheetsProvider


class CSVSheetsProvider(SheetsProvider):
    """Sheets provider that reads from CSV files for testing with real Google Sheets format."""

    def __init__(self, csv_file_path: str):
        """Initialize with path to CSV fixture file."""
        self.csv_file_path = Path(csv_file_path)
        if not self.csv_file_path.exists():
            raise FileNotFoundError(f"CSV fixture not found: {csv_file_path}")

    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Read CSV data and return as sheets format (list of lists).

        This simulates the exact format that Google Sheets API returns:
        - Row 1: Title
        - Row 2: Owner names
        - Row 3: Team names
        - Row 4: Headers (Player, Pos, Player, Pos, ...)
        - Row 5+: Draft picks by round
        """
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = [row for row in reader]

                # Ensure we have enough columns to match the range format
                # The range Draft!A1:V24 expects 22 columns (A through V)
                max_cols = 22
                normalized_rows = []
                for row in rows:
                    # Pad row to ensure consistent column count
                    while len(row) < max_cols:
                        row.append("")
                    normalized_rows.append(row[:max_cols])  # Truncate if too long

                return normalized_rows
        except Exception as e:
            raise Exception(f"Failed to read CSV fixture: {e}")


    def get_row_count(self) -> int:
        """Helper method to get number of rows in CSV (including header)."""
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
