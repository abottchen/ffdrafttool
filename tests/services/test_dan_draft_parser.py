"""Tests for DanDraftParser class."""

import pytest

from src.models.draft_pick import DraftPick
from src.models.draft_state_simple import DraftState
from src.models.injury_status import InjuryStatus
from src.models.player_simple import Player
from src.services.dan_draft_parser import DanDraftParser
from src.services.sheet_parser import ParseError


class TestDanDraftParser:
    """Test suite for DanDraftParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DanDraftParser()

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
            ["no", "team", "structure"],
        ]

        with pytest.raises(
            ParseError, match="Sheet data does not match Dan's draft format"
        ):
            await self.parser.parse_draft_data(malformed_data)

    @pytest.mark.asyncio
    async def test_parse_minimal_valid_sheet_data(self):
        """Test parsing minimal valid sheet data returns empty DraftState."""
        minimal_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow"],
            ["", "Team 1", "", "Team 2"],
            ["", "Player", "Pos", "Player", "Pos"],
            ["1", "", "", "", ""],  # Empty round to meet minimum length requirement
        ]

        result = await self.parser.parse_draft_data(minimal_data)

        assert isinstance(result, DraftState)
        assert len(result.picks) == 0
        assert len(result.teams) == 2
        assert result.teams[0]["owner"] == "Buffy"
        assert result.teams[1]["owner"] == "Willow"

    def test_detect_format_valid_dan_format(self):
        """Test detect_format returns True for valid Dan format."""
        valid_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow"],
            ["", "Team 1", "", "Team 2"],
            ["", "Player", "Pos", "Player", "Pos"],
            ["1", "Josh Allen   BUF", "QB", "CMC   SF", "RB"],
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

    def test_parse_player_info_with_team(self):
        """Test _parse_player_info with team abbreviation."""
        name, team = self.parser._parse_player_info("Josh Allen   BUF")
        assert name == "Josh Allen"
        assert team == "BUF"

    def test_parse_player_info_with_hyphen_team(self):
        """Test _parse_player_info with hyphen-separated team."""
        name, team = self.parser._parse_player_info("DJ Moore -  CHI")
        assert name == "DJ Moore"
        assert team == "CHI"

    def test_parse_player_info_no_team(self):
        """Test _parse_player_info without team abbreviation."""
        name, team = self.parser._parse_player_info("Just A Name")
        assert name == "Just A Name"
        assert team == "UNK"

    def test_parse_player_info_empty_string(self):
        """Test _parse_player_info with empty string."""
        name, team = self.parser._parse_player_info("")
        assert name == ""
        assert team == "UNK"

    def test_parse_player_info_complex_name(self):
        """Test _parse_player_info with complex player name."""
        name, team = self.parser._parse_player_info("A.J. Brown   PHI")
        assert name == "A.J. Brown"
        assert team == "PHI"

    def test_extract_teams_and_owners_basic(self):
        """Test _extract_teams_and_owners with basic team structure."""
        sheet_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow", "", "Xander"],
            ["", "Slayers", "", "Witches", "", "Crew"],
            ["", "Player", "Pos", "Player", "Pos", "Player", "Pos"],
        ]

        teams = self.parser._extract_teams_and_owners(sheet_data)

        assert len(teams) == 3
        assert teams[0]["owner"] == "Buffy"
        assert teams[0]["team_name"] == "Slayers"
        assert teams[1]["owner"] == "Willow"
        assert teams[1]["team_name"] == "Witches"
        assert teams[2]["owner"] == "Xander"
        assert teams[2]["team_name"] == "Crew"

    def test_extract_teams_and_owners_with_gaps(self):
        """Test _extract_teams_and_owners handles gaps in sheet structure."""
        sheet_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "", "Willow", ""],
            ["", "Slayers", "", "", "Witches", ""],
            ["", "Player", "Pos", "", "Player", "Pos"],
        ]

        teams = self.parser._extract_teams_and_owners(sheet_data)

        assert len(teams) == 2
        assert teams[0]["owner"] == "Buffy"
        assert teams[1]["owner"] == "Willow"

    @pytest.mark.asyncio
    async def test_parse_draft_data_with_picks(self):
        """Test parsing sheet data with actual draft picks."""
        sheet_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow"],
            ["", "Slayers", "", "Witches"],
            ["", "Player", "Pos", "Player", "Pos"],
            ["1", "Josh Allen   BUF", "QB", "CMC   SF", "RB"],
            ["2", "Tyreek Hill   MIA", "WR", "Travis Kelce   KC", "TE"],
        ]

        result = await self.parser.parse_draft_data(sheet_data)

        assert isinstance(result, DraftState)
        assert len(result.picks) == 4
        assert len(result.teams) == 2

        # Check first pick
        first_pick = result.picks[0]
        assert isinstance(first_pick, DraftPick)
        assert first_pick.player.name == "Josh Allen"
        assert first_pick.player.team == "BUF"
        assert first_pick.player.position == "QB"
        assert first_pick.owner == "Buffy"

    def test_create_player_from_pick(self):
        """Test _create_player_from_pick creates proper Player object."""
        pick_data = {"player_name": "Josh Allen   BUF", "position": "QB"}

        player = self.parser._create_player_from_pick(pick_data)

        assert isinstance(player, Player)
        assert player.name == "Josh Allen"
        assert player.team == "BUF"
        assert player.position == "QB"
        assert player.bye_week == 0
        assert player.ranking == 0
        assert player.projected_points == 0.0
        assert player.injury_status == InjuryStatus.HEALTHY
        assert player.notes == ""

    def test_find_team_by_pick_position_odd_round(self):
        """Test _find_team_by_pick_position for odd round (1->N)."""
        teams = [
            {"team_number": 1, "owner": "Buffy"},
            {"team_number": 2, "owner": "Willow"},
            {"team_number": 3, "owner": "Xander"},
        ]

        # Round 1, Pick 1 should go to Buffy
        result = self.parser._find_team_by_pick_position(teams, 1, 3, 1)
        assert result["owner"] == "Buffy"

        # Round 1, Pick 3 should go to Xander
        result = self.parser._find_team_by_pick_position(teams, 3, 3, 1)
        assert result["owner"] == "Xander"

    def test_find_team_by_pick_position_even_round(self):
        """Test _find_team_by_pick_position for even round (N->1)."""
        teams = [
            {"team_number": 1, "owner": "Buffy"},
            {"team_number": 2, "owner": "Willow"},
            {"team_number": 3, "owner": "Xander"},
        ]

        # Round 2, Pick 4 should go to Xander (snake back)
        result = self.parser._find_team_by_pick_position(teams, 4, 3, 2)
        assert result["owner"] == "Xander"

        # Round 2, Pick 6 should go to Buffy
        result = self.parser._find_team_by_pick_position(teams, 6, 3, 2)
        assert result["owner"] == "Buffy"

    def test_find_team_by_pick_position_invalid_inputs(self):
        """Test _find_team_by_pick_position with invalid inputs."""
        teams = [{"team_number": 1, "owner": "Giles"}]

        # Empty teams
        result = self.parser._find_team_by_pick_position([], 1, 0, 1)
        assert result is None

        # Zero total teams
        result = self.parser._find_team_by_pick_position(teams, 1, 0, 1)
        assert result is None

    def test_rebuild_full_teams_structure(self):
        """Test _rebuild_full_teams_structure creates proper team structure."""
        sheet_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow"],
            ["", "Slayers", "", "Witches"],
            ["", "Player", "Pos", "Player", "Pos"],
        ]

        teams = self.parser._rebuild_full_teams_structure(sheet_data)

        assert len(teams) == 2
        assert teams[0]["owner"] == "Buffy"
        assert teams[0]["team_name"] == "Slayers"
        assert teams[0]["player_col"] == 1
        assert teams[0]["position_col"] == 2
        assert teams[1]["owner"] == "Willow"
        assert teams[1]["team_name"] == "Witches"
        assert teams[1]["player_col"] == 3
        assert teams[1]["position_col"] == 4

    @pytest.mark.asyncio
    async def test_parse_draft_data_snake_draft_order(self):
        """Test that snake draft pick order is correctly calculated."""
        sheet_data = [
            ["2024 Fantasy Draft"],
            ["", "Buffy", "", "Willow"],  # Row 1: Owners
            ["", "Slayers", "", "Witches"],  # Row 2: Team names
            ["", "Player", "Pos", "Player", "Pos"],
            ["1", "Josh Allen   BUF", "QB", "CMC   SF", "RB"],
            [
                "2",
                "Tyreek Hill   MIA",
                "WR",
                "Travis Kelce   KC",
                "TE",
            ],  # Snake back in round 2
        ]

        result = await self.parser.parse_draft_data(sheet_data)

        # Verify snake draft order: Buffy->Willow, then Willow->Buffy
        assert result.picks[0].player.name == "Josh Allen"  # Buffy, Pick 1
        assert result.picks[0].owner == "Buffy"

        assert result.picks[1].player.name == "CMC"  # Willow, Pick 2
        assert result.picks[1].owner == "Willow"

        # Round 2 should snake back - parser correctly assigns picks by snake logic, not column position
        assert (
            result.picks[2].player.name == "Tyreek Hill"
        )  # Willow, Pick 3 (from Buffy's column but assigned to Willow)
        assert result.picks[2].owner == "Willow"

        assert (
            result.picks[3].player.name == "Travis Kelce"
        )  # Buffy, Pick 4 (from Willow's column but assigned to Buffy)
        assert result.picks[3].owner == "Buffy"
