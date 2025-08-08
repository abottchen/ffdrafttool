"""Tests for the PlayerRankings cache model."""

import pytest
from datetime import datetime
from src.models.player_rankings import PlayerRankings
from src.models.player_simple import Player
from src.models.injury_status import InjuryStatus


class TestPlayerRankings:
    def test_player_rankings_creation(self):
        """Test creating an empty player rankings cache."""
        cache = PlayerRankings()
        
        assert cache.position_data == {}
        assert cache.last_updated == {}

    def test_set_position_data(self):
        """Test setting player data for a position."""
        cache = PlayerRankings()
        
        qb_players = [
            Player(
                name="Josh Allen",
                team="BUF",
                position="QB",
                bye_week=12,
                ranking=1,
                projected_points=325.5
            ),
            Player(
                name="Lamar Jackson",
                team="BAL", 
                position="QB",
                bye_week=14,
                ranking=2,
                projected_points=315.0
            )
        ]
        
        cache.set_position_data("QB", qb_players)
        
        assert "QB" in cache.position_data
        assert len(cache.position_data["QB"]) == 2
        assert cache.position_data["QB"][0].name == "Josh Allen"
        assert cache.position_data["QB"][1].name == "Lamar Jackson"
        assert "QB" in cache.last_updated
        assert isinstance(cache.last_updated["QB"], datetime)

    def test_get_position_data(self):
        """Test getting player data for a position."""
        cache = PlayerRankings()
        
        rb_players = [
            Player(
                name="Christian McCaffrey",
                team="SF",
                position="RB", 
                bye_week=9,
                ranking=1,
                projected_points=285.2
            )
        ]
        
        cache.set_position_data("RB", rb_players)
        result = cache.get_position_data("RB")
        
        assert result == rb_players
        assert len(result) == 1
        assert result[0].name == "Christian McCaffrey"

    def test_get_position_data_not_cached(self):
        """Test getting data for position that's not cached."""
        cache = PlayerRankings()
        
        result = cache.get_position_data("WR")
        
        assert result is None

    def test_has_position_data(self):
        """Test checking if position data is cached."""
        cache = PlayerRankings()
        
        assert cache.has_position_data("QB") == False
        
        qb_players = [
            Player(
                name="Josh Allen",
                team="BUF",
                position="QB",
                bye_week=12,
                ranking=1, 
                projected_points=325.5
            )
        ]
        
        cache.set_position_data("QB", qb_players)
        
        assert cache.has_position_data("QB") == True
        assert cache.has_position_data("RB") == False

    def test_search_players(self):
        """Test searching for players across all cached positions."""
        cache = PlayerRankings()
        
        qb_players = [
            Player(
                name="Josh Allen",
                team="BUF",
                position="QB",
                bye_week=12,
                ranking=1,
                projected_points=325.5
            ),
            Player(
                name="Lamar Jackson", 
                team="BAL",
                position="QB",
                bye_week=14,
                ranking=2,
                projected_points=315.0
            )
        ]
        
        rb_players = [
            Player(
                name="Christian McCaffrey",
                team="SF",
                position="RB",
                bye_week=9,
                ranking=1,
                projected_points=285.2
            ),
            Player(
                name="Josh Jacobs",
                team="LV", 
                position="RB",
                bye_week=6,
                ranking=8,
                projected_points=220.5
            )
        ]
        
        cache.set_position_data("QB", qb_players)
        cache.set_position_data("RB", rb_players)
        
        # Search by last name
        josh_results = cache.search_players(last_name="Allen")
        assert len(josh_results) == 1
        assert josh_results[0].name == "Josh Allen"
        
        # Search by last name (multiple results) 
        jacobs_results = cache.search_players(last_name="Jacobs")
        assert len(jacobs_results) == 1  # Should dedupe
        assert jacobs_results[0].name == "Josh Jacobs"
        
        # Search by team
        buf_results = cache.search_players(team="BUF")
        assert len(buf_results) == 1
        assert buf_results[0].name == "Josh Allen"
        
        # Search by position
        qb_results = cache.search_players(position="QB")
        assert len(qb_results) == 2  # Josh Allen and Lamar Jackson from QB cache
        
        # Search by first and last name
        josh_allen_results = cache.search_players(first_name="Josh", last_name="Allen")
        assert len(josh_allen_results) == 1
        assert josh_allen_results[0].name == "Josh Allen"

    def test_clear_cache(self):
        """Test clearing all cached data."""
        cache = PlayerRankings()
        
        qb_players = [
            Player(
                name="Josh Allen",
                team="BUF",
                position="QB",
                bye_week=12,
                ranking=1,
                projected_points=325.5
            )
        ]
        
        cache.set_position_data("QB", qb_players)
        assert cache.has_position_data("QB") == True
        
        cache.clear_cache()
        
        assert cache.has_position_data("QB") == False
        assert cache.position_data == {}
        assert cache.last_updated == {}

    def test_get_all_positions(self):
        """Test getting list of all cached positions."""
        cache = PlayerRankings()
        
        assert cache.get_all_positions() == []
        
        cache.set_position_data("QB", [])
        cache.set_position_data("RB", [])
        
        positions = cache.get_all_positions()
        assert set(positions) == {"QB", "RB"}