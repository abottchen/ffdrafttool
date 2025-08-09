"""Tests for the scraper data adapter."""

import pytest

from src.models.injury_status import InjuryStatus as SimpleInjuryStatus
from src.models.player import Player as OldPlayer
from src.models.player import Position as OldPosition
from src.models.player import RankingSource
from src.models.player_simple import Player as SimplePlayer
from src.services.scraper_adapter import ScraperAdapter


class TestScraperAdapter:
    def test_convert_old_player_to_simple(self):
        """Test converting old Player model to simplified Player model."""
        # Create an old-style player with FantasySharks data
        old_player = OldPlayer(
            name="Josh Allen",
            position=OldPosition.QB,
            team="BUF",
            bye_week=12,
            commentary="Elite dual-threat QB with rushing upside",
        )
        old_player.add_ranking(
            RankingSource.OTHER, 1, 325.5
        )  # FantasySharks uses OTHER

        adapter = ScraperAdapter()
        simple_player = adapter.convert_player(old_player)

        assert isinstance(simple_player, SimplePlayer)
        assert simple_player.name == "Josh Allen"
        assert simple_player.team == "BUF"
        assert simple_player.position == "QB"
        assert simple_player.bye_week == 12
        assert simple_player.injury_status == SimpleInjuryStatus.HEALTHY
        assert simple_player.ranking == 1
        assert simple_player.projected_points == 325.5
        assert simple_player.notes == "Elite dual-threat QB with rushing upside"

    def test_convert_player_with_different_positions(self):
        """Test converting players with different positions."""
        adapter = ScraperAdapter()

        positions_to_test = [
            (OldPosition.QB, "QB"),
            (OldPosition.RB, "RB"),
            (OldPosition.WR, "WR"),
            (OldPosition.TE, "TE"),
            (OldPosition.K, "K"),
            (OldPosition.DST, "DST"),
        ]

        for old_pos, expected_pos_str in positions_to_test:
            old_player = OldPlayer(
                name="Test Player", position=old_pos, team="TEST", bye_week=5
            )
            old_player.add_ranking(RankingSource.OTHER, 10, 100.0)

            simple_player = adapter.convert_player(old_player)
            assert simple_player.position == expected_pos_str

    def test_convert_player_with_no_rankings(self):
        """Test converting player with no rankings data."""
        old_player = OldPlayer(
            name="Unknown Player", position=OldPosition.RB, team="UNK", bye_week=8
        )

        adapter = ScraperAdapter()
        simple_player = adapter.convert_player(old_player)

        # Should have default values when no rankings
        assert simple_player.ranking == 999  # Default for unranked
        assert simple_player.projected_points == 0.0  # Default for no projection

    def test_convert_player_with_commentary(self):
        """Test that commentary is properly transferred."""
        old_player = OldPlayer(
            name="Player With Commentary",
            position=OldPosition.WR,
            team="TEST",
            bye_week=6,
            commentary="This player has detailed commentary about their season outlook.",
        )
        old_player.add_ranking(RankingSource.OTHER, 15, 180.5)

        adapter = ScraperAdapter()
        simple_player = adapter.convert_player(old_player)

        assert (
            simple_player.notes
            == "This player has detailed commentary about their season outlook."
        )

    def test_convert_player_without_commentary(self):
        """Test that missing commentary becomes empty string."""
        old_player = OldPlayer(
            name="Player Without Commentary",
            position=OldPosition.TE,
            team="TEST",
            bye_week=9,
        )
        old_player.add_ranking(RankingSource.OTHER, 8, 120.0)

        adapter = ScraperAdapter()
        simple_player = adapter.convert_player(old_player)

        assert simple_player.notes == ""

    def test_convert_multiple_players(self):
        """Test converting a list of old players."""
        old_players = [
            OldPlayer(
                name="Player 1", position=OldPosition.QB, team="BUF", bye_week=12
            ),
            OldPlayer(name="Player 2", position=OldPosition.RB, team="SF", bye_week=9),
            OldPlayer(name="Player 3", position=OldPosition.WR, team="MIA", bye_week=6),
        ]

        # Add rankings to each
        for i, player in enumerate(old_players):
            player.add_ranking(RankingSource.OTHER, i + 1, 300.0 - (i * 50))

        adapter = ScraperAdapter()
        simple_players = adapter.convert_players(old_players)

        assert len(simple_players) == 3
        assert all(isinstance(p, SimplePlayer) for p in simple_players)
        assert simple_players[0].name == "Player 1"
        assert simple_players[1].name == "Player 2"
        assert simple_players[2].name == "Player 3"
        assert simple_players[0].ranking == 1
        assert simple_players[1].ranking == 2
        assert simple_players[2].ranking == 3

    def test_convert_empty_list(self):
        """Test converting empty list of players."""
        adapter = ScraperAdapter()
        result = adapter.convert_players([])

        assert result == []

    def test_position_mapping_completeness(self):
        """Test that all supported positions are mapped correctly."""
        adapter = ScraperAdapter()

        # Test that all OldPosition values we use have mappings
        expected_mappings = {
            OldPosition.QB: "QB",
            OldPosition.RB: "RB",
            OldPosition.WR: "WR",
            OldPosition.TE: "TE",
            OldPosition.K: "K",
            OldPosition.DST: "DST",
        }

        for old_pos, expected_str in expected_mappings.items():
            result = adapter._convert_position(old_pos)
            assert result == expected_str

    def test_unsupported_position_handling(self):
        """Test handling of unsupported positions like FLEX."""
        adapter = ScraperAdapter()

        # FLEX should raise an error or return a default
        with pytest.raises(ValueError):
            adapter._convert_position(OldPosition.FLEX)
    
    def test_team_mapping_integration(self):
        """Test that team abbreviations are properly mapped from rankings format."""
        adapter = ScraperAdapter()
        
        # Test players with team abbreviations that need mapping
        test_cases = [
            ("SFO", "SF"),   # San Francisco 49ers
            ("GBP", "GB"),   # Green Bay Packers  
            ("KCC", "KC"),   # Kansas City Chiefs
            ("NEP", "NE"),   # New England Patriots
            ("NOS", "NO"),   # New Orleans Saints
            ("TBB", "TB"),   # Tampa Bay Buccaneers
            ("LVR", "LV"),   # Las Vegas Raiders
            ("BUF", "BUF"),  # Buffalo Bills (no mapping needed)
        ]
        
        for rankings_team, expected_sheet_team in test_cases:
            old_player = OldPlayer(
                name=f"Test Player {rankings_team}",
                position=OldPosition.QB,
                team=rankings_team,  # Team in rankings format
                bye_week=12,
            )
            
            simple_player = adapter.convert_player(old_player)
            
            assert simple_player.team == expected_sheet_team, (
                f"Expected team {expected_sheet_team} for rankings team {rankings_team}, "
                f"but got {simple_player.team}"
            )
    
    def test_invalid_teams_filtered(self):
        """Test that invalid team abbreviations are filtered to UNK."""
        adapter = ScraperAdapter()
        
        # Test with FA (free agent) which might appear in data
        invalid_teams = ["FA"]
        
        for invalid_team in invalid_teams:
            old_player = OldPlayer(
                name=f"Test Player {invalid_team}",
                position=OldPosition.QB,
                team=invalid_team,
                bye_week=12,
            )
            
            simple_player = adapter.convert_player(old_player)
            
            assert simple_player.team == "UNK", (
                f"Expected UNK for invalid team {invalid_team}, "
                f"but got {simple_player.team}"
            )
