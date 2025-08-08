"""Adapter to convert scraper data to simplified models."""

from typing import List

from src.models.injury_status import InjuryStatus as SimpleInjuryStatus
from src.models.player import Player as OldPlayer
from src.models.player import Position as OldPosition
from src.models.player import RankingSource
from src.models.player_simple import Player as SimplePlayer


class ScraperAdapter:
    """Converts old Player models from scrapers to simplified Player models."""

    def __init__(self):
        """Initialize the adapter with position mappings."""
        self.position_mapping = {
            OldPosition.QB: "QB",
            OldPosition.RB: "RB",
            OldPosition.WR: "WR",
            OldPosition.TE: "TE",
            OldPosition.K: "K",
            OldPosition.DST: "DST",
        }

    def convert_player(self, old_player: OldPlayer) -> SimplePlayer:
        """Convert a single old Player to simplified Player model.

        Args:
            old_player: Player from the old model system

        Returns:
            SimplePlayer: Converted player with simplified data
        """
        # Convert position
        position_str = self._convert_position(old_player.position)

        # Extract FantasySharks ranking data (stored as RankingSource.OTHER)
        ranking = 999  # Default for unranked players
        projected_points = 0.0  # Default for no projection

        if old_player.rankings and RankingSource.OTHER in old_player.rankings:
            fs_data = old_player.rankings[RankingSource.OTHER]
            ranking = int(fs_data.get("rank", 999))
            projected_points = float(fs_data.get("score", 0.0))

        # Convert injury status (old model uses same enum, just different import)
        injury_status = SimpleInjuryStatus.HEALTHY
        if hasattr(old_player, "injury_status") and old_player.injury_status:
            # Map old injury status to new one
            injury_mapping = {
                "HEALTHY": SimpleInjuryStatus.HEALTHY,
                "PROBABLE": SimpleInjuryStatus.HEALTHY,  # Treat probable as healthy
                "QUESTIONABLE": SimpleInjuryStatus.QUESTIONABLE,
                "DOUBTFUL": SimpleInjuryStatus.DOUBTFUL,
                "OUT": SimpleInjuryStatus.OUT,
            }
            injury_status = injury_mapping.get(
                old_player.injury_status.value, SimpleInjuryStatus.HEALTHY
            )

        # Get commentary/notes
        notes = old_player.commentary or ""

        return SimplePlayer(
            name=old_player.name,
            team=old_player.team,
            position=position_str,
            bye_week=old_player.bye_week,
            ranking=ranking,
            projected_points=projected_points,
            injury_status=injury_status,
            notes=notes,
        )

    def convert_players(self, old_players: List[OldPlayer]) -> List[SimplePlayer]:
        """Convert a list of old Players to simplified Players.

        Args:
            old_players: List of players from old model system

        Returns:
            List[SimplePlayer]: Converted players with simplified data
        """
        return [self.convert_player(player) for player in old_players]

    def _convert_position(self, old_position: OldPosition) -> str:
        """Convert old Position enum to position string.

        Args:
            old_position: Position from old enum system

        Returns:
            str: Position as string (QB, RB, WR, TE, K, DST)

        Raises:
            ValueError: If position is not supported
        """
        if old_position not in self.position_mapping:
            raise ValueError(f"Unsupported position: {old_position}")

        return self.position_mapping[old_position]
