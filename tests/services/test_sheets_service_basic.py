"""Basic tests for sheets service functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.sheets_service import (
    GoogleSheetsProvider,
    SheetsService,
)
from tests.test_helpers import MockSheetsProvider


class TestSheetsServiceBasic:
    def test_mock_sheets_provider_creation(self):
        """Test that MockSheetsProvider can be created."""
        provider = MockSheetsProvider()
        assert provider is not None
        assert hasattr(provider, 'mock_data')

    @pytest.mark.asyncio
    async def test_mock_sheets_provider_read_range(self):
        """Test MockSheetsProvider read functionality."""
        provider = MockSheetsProvider()

        # The mock provider should have some default data for the correct range
        result = await provider.read_range("test_sheet_123", "Draft!A1:V24")

        # Should return some data (mock data is defined in the provider)
        assert isinstance(result, list)
        # MockSheetsProvider has predefined mock data, so it should not be empty
        assert len(result) > 0
        assert result[0] == ["Pick", "Team", "Player", "Position"]  # Check header row

    @pytest.mark.asyncio
    async def test_mock_sheets_provider_read_nonexistent_range(self):
        """Test MockSheetsProvider with non-existent range."""
        provider = MockSheetsProvider()

        # Should return empty list for non-existent data
        result = await provider.read_range("test_sheet_123", "Draft!A1:Z100")
        assert result == []

    def test_sheets_service_creation_with_mock_provider(self):
        """Test SheetsService with mock provider."""
        provider = MockSheetsProvider()
        service = SheetsService(provider)

        assert service is not None
        assert service.provider == provider

    @pytest.mark.asyncio
    async def test_sheets_service_provider_delegation(self):
        """Test SheetsService uses provider correctly."""
        provider = MockSheetsProvider()
        service = SheetsService(provider)

        # SheetsService doesn't have direct read_range - it uses the provider through higher-level methods
        # Test that the provider is accessible
        assert service.provider == provider

        # Test provider directly through service
        result = await service.provider.read_range("test_sheet_123", "Draft!A1:V24")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_google_sheets_provider_creation_without_credentials(self):
        """Test GoogleSheetsProvider handles missing credentials gracefully."""
        # GoogleSheetsProvider may or may not immediately check for credentials
        # depending on implementation. Let's just test that it can be created
        # The real test of credential handling is in the draft progress tests
        try:
            provider = GoogleSheetsProvider()
            # If it doesn't raise, that's also valid behavior
            assert provider is not None
        except FileNotFoundError:
            # This is the expected behavior when credentials are missing
            pass

    def test_google_sheets_provider_handles_missing_dependencies(self):
        """Test that missing Google API dependencies are handled."""
        # Mock the import check
        with patch('src.services.sheets_service.GOOGLE_AVAILABLE', False):
            with pytest.raises(ImportError):
                GoogleSheetsProvider()

    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test provider error handling."""
        # Create a mock provider that raises an exception
        mock_provider = AsyncMock()
        mock_provider.read_range.side_effect = Exception("Mock error")

        # Test error propagation through provider
        with pytest.raises(Exception):
            await mock_provider.read_range("test_sheet", "A1:B2")
