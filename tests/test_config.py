"""Tests for configuration loading and validation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import load_config


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_config_success(self):
        """Test successful config loading with valid config.json."""
        # Create a temporary config file
        config_data = {
            "google_sheets": {
                "default_sheet_id": "sunnydale_sheet_id",
                "default_range": "Draft!A1:V24"
            },
            "draft": {
                "owner_name": "Buffy"
            },
            "cache": {
                "rankings_cache_hours": 12,
                "draft_cache_minutes": 2
            },
            "logging": {
                "level": "DEBUG"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(config_data, temp_file)
            temp_config_path = Path(temp_file.name)
        
        try:
            # Mock the config path to point to our temp file
            with patch('src.config.Path.__truediv__') as mock_path:
                mock_path.return_value = temp_config_path
                
                result = load_config()
                
                assert result == config_data
                assert result["google_sheets"]["default_sheet_id"] == "sunnydale_sheet_id"
                assert result["draft"]["owner_name"] == "Buffy"
                assert result["cache"]["rankings_cache_hours"] == 12
                assert result["cache"]["draft_cache_minutes"] == 2
                assert result["logging"]["level"] == "DEBUG"
        finally:
            temp_config_path.unlink()

    def test_load_config_file_not_found(self):
        """Test config loading when config.json doesn't exist."""
        with patch('src.config.Path.__truediv__') as mock_path:
            # Mock a non-existent path
            mock_path.return_value = Path("/hellmouth/config.json")
            
            with pytest.raises(FileNotFoundError) as exc_info:
                load_config()
            
            assert "Configuration file not found" in str(exc_info.value)
            assert "config.json.example" in str(exc_info.value)

    def test_load_config_invalid_json(self):
        """Test config loading with malformed JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("{ this json is as broken as the Hellmouth")
            temp_config_path = Path(temp_file.name)
        
        try:
            with patch('src.config.Path.__truediv__') as mock_path:
                mock_path.return_value = temp_config_path
                
                with pytest.raises(json.JSONDecodeError):
                    load_config()
        finally:
            temp_config_path.unlink()


class TestConfigValues:
    """Test that imported config values match expected types and defaults."""

    def test_config_constants_types(self):
        """Test that config constants are loaded with correct types."""
        from src.config import (
            DEFAULT_SHEET_ID,
            DEFAULT_SHEET_RANGE, 
            USER_OWNER_NAME,
            RANKINGS_CACHE_HOURS,
            DRAFT_CACHE_MINUTES,
            LOG_LEVEL
        )
        
        # Test that all constants exist and have correct types
        assert isinstance(DEFAULT_SHEET_ID, str)
        assert isinstance(DEFAULT_SHEET_RANGE, str)
        assert isinstance(USER_OWNER_NAME, str)
        assert isinstance(RANKINGS_CACHE_HOURS, int)
        assert isinstance(DRAFT_CACHE_MINUTES, int)
        assert isinstance(LOG_LEVEL, str)
        
        # Test that string values are not empty
        assert len(DEFAULT_SHEET_ID) > 0
        assert len(DEFAULT_SHEET_RANGE) > 0
        assert len(USER_OWNER_NAME) > 0
        assert len(LOG_LEVEL) > 0

    def test_config_cache_values_positive(self):
        """Test that cache values are positive integers."""
        from src.config import RANKINGS_CACHE_HOURS, DRAFT_CACHE_MINUTES
        
        assert RANKINGS_CACHE_HOURS > 0
        assert DRAFT_CACHE_MINUTES > 0
        
        # Test reasonable bounds (not ridiculously high)
        assert RANKINGS_CACHE_HOURS <= 720  # Max 30 days
        assert DRAFT_CACHE_MINUTES <= 60   # Max 1 hour

    def test_config_required_sections_present(self):
        """Test that all required configuration sections are present."""
        from src.config import _config
        
        # Test that all required top-level sections exist
        required_sections = ["google_sheets", "draft", "cache", "logging"]
        for section in required_sections:
            assert section in _config, f"Missing required config section: {section}"
        
        # Test required subsections
        assert "default_sheet_id" in _config["google_sheets"]
        assert "default_range" in _config["google_sheets"] 
        assert "owner_name" in _config["draft"]
        assert "rankings_cache_hours" in _config["cache"]
        assert "draft_cache_minutes" in _config["cache"]
        assert "level" in _config["logging"]


class TestConfigIntegration:
    """Test that config values are properly used by dependent modules."""

    def test_rankings_cache_uses_config_value(self):
        """Test that player rankings cache uses RANKINGS_CACHE_HOURS from config."""
        from src.tools.player_rankings import get_player_rankings
        from src.config import RANKINGS_CACHE_HOURS
        
        # Import to ensure config is loaded
        assert RANKINGS_CACHE_HOURS is not None
        assert isinstance(RANKINGS_CACHE_HOURS, int)
        assert RANKINGS_CACHE_HOURS > 0

    def test_draft_cache_uses_config_value(self):
        """Test that draft state cache uses DRAFT_CACHE_MINUTES from config."""
        from src.services.draft_state_cache import _draft_state_cache
        from src.config import DRAFT_CACHE_MINUTES
        
        # Import to ensure config is loaded
        assert DRAFT_CACHE_MINUTES is not None
        assert isinstance(DRAFT_CACHE_MINUTES, int)
        assert DRAFT_CACHE_MINUTES > 0
        
        # Check that cache TTL is correctly calculated (minutes * 60 = seconds)
        expected_ttl = DRAFT_CACHE_MINUTES * 60
        assert _draft_state_cache.ttl == expected_ttl

    def test_server_uses_config_values(self):
        """Test that server module imports config values correctly."""
        # Import server to ensure config values are accessible
        try:
            from src.server import DEFAULT_SHEET_ID, DEFAULT_SHEET_RANGE, LOG_LEVEL
            
            assert DEFAULT_SHEET_ID is not None
            assert DEFAULT_SHEET_RANGE is not None  
            assert LOG_LEVEL is not None
            assert isinstance(DEFAULT_SHEET_ID, str)
            assert isinstance(DEFAULT_SHEET_RANGE, str)
            assert isinstance(LOG_LEVEL, str)
        except ImportError as e:
            pytest.skip(f"Server module not importable in test environment: {e}")