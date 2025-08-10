"""Tests for AdamDraftParser class."""

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.adam_draft_parser import AdamDraftParser
from src.services.sheet_parser import ParseError


class TestAdamDraftParser:
    """Test suite for AdamDraftParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock rankings cache for team/position lookup
        self.mock_rankings_cache = {
            "QB": {
                "players": [
                    {"name": "Josh Allen", "team": "BUF", "position": "QB"},
                    {"name": "Jalen Hurts", "team": "PHI", "position": "QB"},
                ]
            },
            "RB": {
                "players": [
                    {"name": "Breece Hall", "team": "NYJ", "position": "RB"},
                    {"name": "Christian McCaffrey", "team": "SF", "position": "RB"},
                ]
            },
            "WR": {
                "players": [
                    {"name": "Puka Nacua", "team": "LAR", "position": "WR"},
                ]
            },
        }
        self.parser = AdamDraftParser(self.mock_rankings_cache)

    @pytest.mark.asyncio
    async def test_parse_empty_sheet_data(self):
        """Test parsing empty sheet data raises ParseError."""
        with pytest.raises(ParseError, match="Sheet data is empty"):
            await self.parser.parse_draft_data([])

    @pytest.mark.asyncio
    async def test_parse_malformed_sheet_data(self):
        """Test parsing malformed sheet data raises ParseError."""
        malformed_data = [
            ["invalid", "data", "format"],
            ["no", "auction", "structure"],
        ]

        with pytest.raises(
            ParseError, match="Sheet data does not match Adam's draft format"
        ):
            await self.parser.parse_draft_data(malformed_data)

    def test_detect_format_valid_adam_format(self):
        """Test detect_format returns True for valid Adam format."""
        valid_data = [
            ["Buffy", "", "Willow"],  # Row 0: Owners
            ["Player", "$", "Player", "$"],  # Row 1: Headers
            ["Hall, Breece", "13", "McCaffrey, Christian", "56"],  # Row 2: Data
        ]

        assert self.parser.detect_format(valid_data) is True

    def test_detect_format_invalid_format(self):
        """Test detect_format returns False for invalid format."""
        invalid_data = [
            ["invalid", "csv", "format"],
        ]

        assert self.parser.detect_format(invalid_data) is False

    def test_detect_format_empty_data(self):
        """Test detect_format returns False for empty data."""
        assert self.parser.detect_format([]) is False
        assert self.parser.detect_format([[]]) is False

    def test_reverse_player_name_basic(self):
        """Test _reverse_player_name with basic format."""
        name = self.parser._reverse_player_name("Hall, Breece")
        assert name == "Breece Hall"

    def test_reverse_player_name_complex(self):
        """Test _reverse_player_name with complex names."""
        name = self.parser._reverse_player_name("McCaffrey, Christian")
        assert name == "Christian McCaffrey"

    def test_reverse_player_name_suffix(self):
        """Test _reverse_player_name with suffix."""
        name = self.parser._reverse_player_name("Harrison Jr., Marvin")
        assert name == "Marvin Harrison Jr."

    def test_reverse_player_name_no_comma(self):
        """Test _reverse_player_name with no comma (already normal format)."""
        name = self.parser._reverse_player_name("Breece Hall")
        assert name == "Breece Hall"

    def test_reverse_player_name_defense(self):
        """Test _reverse_player_name doesn't change defense format."""
        name = self.parser._reverse_player_name("Ravens D/ST")
        assert name == "Ravens D/ST"

    def test_is_defense_detection(self):
        """Test _is_defense correctly identifies defense teams."""
        assert self.parser._is_defense("Ravens D/ST") is True
        assert self.parser._is_defense("Steelers D/ST") is True
        assert self.parser._is_defense("Hall, Breece") is False

    def test_parse_defense_known_teams(self):
        """Test _parse_defense for known team mappings."""
        team, pos = self.parser._parse_defense("Ravens D/ST")
        assert team == "BAL"
        assert pos == "DST"

        team, pos = self.parser._parse_defense("Bills D/ST")
        assert team == "BUF"
        assert pos == "DST"

    def test_parse_defense_unknown_team(self):
        """Test _parse_defense for unknown team."""
        team, pos = self.parser._parse_defense("Unknown D/ST")
        assert team == "UNK"
        assert pos == "DST"

    def test_lookup_team_from_cache_found(self):
        """Test _lookup_team_from_cache finds team in cache."""
        team = self.parser._lookup_team_from_cache("Breece Hall")
        assert team == "NYJ"

    def test_lookup_team_from_cache_not_found(self):
        """Test _lookup_team_from_cache returns UNK when not found."""
        team = self.parser._lookup_team_from_cache("Unknown Player")
        assert team == "UNK"

    def test_lookup_position_from_cache_found(self):
        """Test _lookup_position_from_cache finds position in cache."""
        position = self.parser._lookup_position_from_cache("Breece Hall")
        assert position == "RB"

    def test_lookup_position_from_cache_not_found(self):
        """Test _lookup_position_from_cache returns FLEX when not found."""
        position = self.parser._lookup_position_from_cache("Unknown Player")
        assert position == "FLEX"

    def test_extract_teams_and_owners_basic(self):
        """Test _extract_teams_and_owners with basic structure."""
        sheet_data = [
            ["Buffy", "", "Willow", "", "Xander"],  # Row 0: Owners
            ["Player", "$", "Player", "$", "Player", "$"],  # Row 1: Headers
        ]

        teams = self.parser._extract_teams_and_owners(sheet_data)

        assert len(teams) == 3
        assert teams[0]["owner"] == "Buffy"
        assert teams[0]["team_name"] == "Buffy's Team"
        assert teams[1]["owner"] == "Willow"
        assert teams[1]["team_name"] == "Willow's Team"
        assert teams[2]["owner"] == "Xander"
        assert teams[2]["team_name"] == "Xander's Team"

    @pytest.mark.asyncio
    async def test_parse_draft_data_with_picks(self):
        """Test parsing sheet data with actual draft picks."""
        sheet_data = [
            ["Buffy", "", "Willow"],  # Row 0: Owners
            ["Player", "$", "Player", "$"],  # Row 1: Headers
            ["Hall, Breece", "13", "McCaffrey, Christian", "56"],  # Row 2: Data
            ["Allen, Josh", "11", "", ""],  # Row 3: Unequal rosters
        ]

        result = await self.parser.parse_draft_data(sheet_data)

        assert isinstance(result, DraftState)
        assert len(result.picks) == 3  # Breece Hall, Christian McCaffrey, Josh Allen
        assert len(result.teams) == 2

        # Check first pick (Breece Hall for Buffy)
        first_pick = result.picks[0]
        assert isinstance(first_pick, DraftPick)
        assert first_pick.player.name == "Breece Hall"
        assert first_pick.player.team == "NYJ"  # From cache lookup
        assert first_pick.player.position == "RB"
        assert first_pick.owner == "Buffy"

        # Check second pick (Christian McCaffrey for Willow)
        second_pick = result.picks[1]
        assert second_pick.player.name == "Christian McCaffrey"
        assert second_pick.player.team == "SF"  # From cache lookup
        assert second_pick.owner == "Willow"

        # Check third pick (Josh Allen for Buffy)
        third_pick = result.picks[2]
        assert third_pick.player.name == "Josh Allen"
        assert third_pick.player.team == "BUF"  # From cache lookup
        assert third_pick.owner == "Buffy"

    @pytest.mark.asyncio
    async def test_parse_draft_data_with_defense(self):
        """Test parsing sheet data with defense picks."""
        sheet_data = [
            ["Buffy"],  # Row 0: Owner
            ["Player", "$"],  # Row 1: Header
            ["Ravens D/ST", "6"],  # Row 2: Defense pick
        ]

        result = await self.parser.parse_draft_data(sheet_data)

        assert len(result.picks) == 1
        defense_pick = result.picks[0]
        assert defense_pick.player.name == "Ravens D/ST"
        assert defense_pick.player.team == "BAL"
        assert defense_pick.player.position == "DST"
        assert defense_pick.owner == "Buffy"

    def test_create_player_from_pick_normal_player(self):
        """Test _create_player_from_pick with normal player."""
        player = self.parser._create_player_from_pick("Hall, Breece")

        assert isinstance(player, Player)
        assert player.name == "Breece Hall"
        assert player.team == "NYJ"  # From cache lookup
        assert player.position == "RB"
        assert player.bye_week == 0
        assert player.ranking == 0
        assert player.projected_points == 0.0
        assert player.injury_status == InjuryStatus.HEALTHY
        assert player.notes == ""

    def test_create_player_from_pick_defense(self):
        """Test _create_player_from_pick with defense."""
        player = self.parser._create_player_from_pick("Ravens D/ST")

        assert isinstance(player, Player)
        assert player.name == "Ravens D/ST"
        assert player.team == "BAL"
        assert player.position == "DST"

    @pytest.mark.asyncio
    async def test_parse_minimal_valid_sheet_data(self):
        """Test parsing minimal valid sheet data returns empty DraftState."""
        minimal_data = [
            ["Buffy"],  # Row 0: Owner
            ["Player", "$"],  # Row 1: Header
            # No data rows
        ]

        result = await self.parser.parse_draft_data(minimal_data)

        assert isinstance(result, DraftState)
        assert len(result.picks) == 0
        assert len(result.teams) == 1
        assert result.teams[0]["owner"] == "Buffy"

    def test_parser_without_rankings_cache(self):
        """Test parser works without rankings cache (returns UNK/FLEX)."""
        parser = AdamDraftParser()  # No cache

        player = parser._create_player_from_pick("Unknown, Player")
        assert player.name == "Player Unknown"
        assert player.team == "UNK"
        assert player.position == "FLEX"
