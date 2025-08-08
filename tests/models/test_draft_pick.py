"""Tests for the DraftPick model."""

import pytest
from src.models.draft_pick import DraftPick
from src.models.player_simple import Player
from src.models.injury_status import InjuryStatus


class TestDraftPick:
    def test_draft_pick_creation(self):
        """Test creating a draft pick with player and owner."""
        player = Player(
            name="Josh Allen",
            team="BUF", 
            position="QB",
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )
        
        pick = DraftPick(player=player, owner="Buffy")
        
        assert pick.player == player
        assert pick.owner == "Buffy"

    def test_draft_pick_equality(self):
        """Test draft pick equality based on player and owner."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB", 
            bye_week=12,
            ranking=1,
            projected_points=325.5
        )
        
        pick1 = DraftPick(player=player, owner="Buffy")
        pick2 = DraftPick(player=player, owner="Buffy")
        pick3 = DraftPick(player=player, owner="Willow")
        
        assert pick1 == pick2
        assert pick1 != pick3
        assert hash(pick1) == hash(pick2)

    def test_draft_pick_str_representation(self):
        """Test string representation of draft pick."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12, 
            ranking=1,
            projected_points=325.5
        )
        
        pick = DraftPick(player=player, owner="Buffy")
        
        assert str(pick) == "Buffy: Josh Allen (QB - BUF)"

    def test_draft_pick_to_dict(self):
        """Test converting draft pick to dictionary."""
        player = Player(
            name="Josh Allen",
            team="BUF",
            position="QB",
            bye_week=12,
            injury_status=InjuryStatus.HEALTHY,
            ranking=1,
            projected_points=325.5,
            notes="Elite QB"
        )
        
        pick = DraftPick(player=player, owner="Buffy")
        
        expected = {
            "owner": "Buffy",
            "player": {
                "name": "Josh Allen",
                "team": "BUF",
                "position": "QB",
                "bye_week": 12,
                "injury_status": "HEALTHY",
                "ranking": 1,
                "projected_points": 325.5,
                "notes": "Elite QB"
            }
        }
        
        assert pick.to_dict() == expected

    def test_draft_pick_from_dict(self):
        """Test creating draft pick from dictionary."""
        data = {
            "owner": "Buffy",
            "player": {
                "name": "Josh Allen",
                "team": "BUF",
                "position": "QB",
                "bye_week": 12,
                "injury_status": "HEALTHY",
                "ranking": 1,
                "projected_points": 325.5,
                "notes": "Elite QB"
            }
        }
        
        pick = DraftPick.from_dict(data)
        
        assert pick.owner == "Buffy"
        assert pick.player.name == "Josh Allen"
        assert pick.player.team == "BUF"
        assert pick.player.position == "QB"
        assert pick.player.ranking == 1