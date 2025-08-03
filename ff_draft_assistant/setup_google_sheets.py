#!/usr/bin/env python3
"""
Google Sheets API Setup Script

This script helps set up Google Sheets API credentials for the FF Draft Assistant.
Follow these steps:

1. Go to https://console.developers.google.com/
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create credentials (OAuth 2.0 Client ID for desktop application)
5. Download the credentials JSON file and save it as 'credentials.json' in this directory
6. Run this script to test the authentication

The first time you run this, it will open a browser for authentication.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.sheets_service import GoogleSheetsProvider


async def test_authentication():
    """Test Google Sheets authentication"""

    # Check if credentials file exists
    credentials_file = Path("credentials.json")
    if not credentials_file.exists():
        print("ERROR: credentials.json file not found!")
        print("\nTo set up Google Sheets API:")
        print("1. Go to https://console.developers.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Sheets API")
        print("4. Create OAuth 2.0 credentials for desktop application")
        print("5. Download credentials JSON and save as 'credentials.json'")
        return False

    print("SUCCESS: Found credentials.json")

    # Test authentication
    try:
        print("Testing Google Sheets authentication...")
        provider = GoogleSheetsProvider(
            credentials_file=str(credentials_file),
            token_file="token.json"
        )

        # Test with a simple read (this will trigger authentication)
        test_sheet_id = "1eI5rPJK7y1DJ5IQO2fcsLowQil0LtUA736hCZRQlSLU"
        test_range = "Draft!A1:D10"

        print(f"Testing read from sheet: {test_sheet_id}")
        print(f"Range: {test_range}")

        data = await provider.read_range(test_sheet_id, test_range)

        print(f"Successfully authenticated and read {len(data)} rows!")
        print("Sample data:")
        for i, row in enumerate(data[:3]):  # Show first 3 rows
            print(f"  Row {i+1}: {row}")

        return True

    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        print("\nCommon issues:")
        print("- Make sure the Google Sheets API is enabled")
        print("- Check that credentials.json is from a desktop OAuth 2.0 client")
        print("- Ensure the sheet is publicly viewable or shared with your account")
        return False


def main():
    """Main setup function"""
    print("Google Sheets API Setup for FF Draft Assistant")
    print("=" * 50)

    # Run authentication test
    success = asyncio.run(test_authentication())

    if success:
        print("\nSetup complete! Google Sheets integration is ready.")
        print("Token saved to token.json for future use.")
    else:
        print("\nSetup failed. Please check the instructions above.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
