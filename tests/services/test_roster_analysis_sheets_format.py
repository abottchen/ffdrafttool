from unittest.mock import patch

import pytest

from src.tools.draft_suggestions import suggest_draft_pick


class TestRosterAnalysisSheetsFormat:
    """Test that roster analysis works with Google Sheets data format"""

    @pytest.mark.asyncio
    async def test_roster_analysis_with_column_team_field(self):
        """Test roster analysis with column_team field from sheets data"""

        # Mock draft state using actual Google Sheets data format
        mock_draft_state = {
            "picks": [
                # Team picks using column_team field (from sheets)
                {
                    "pick": 10,
                    "round": 1,
                    "player": "Bijan Robinson ATL",  # Note: 'player' not 'player_name'
                    "position": "RB",
                    "column_team": "Test Team",  # Note: 'column_team' not 'team'
                },
                {
                    "pick": 20,
                    "round": 2,
                    "player": "Brock Purdy SF",
                    "position": "QB",
                    "column_team": "Test Team",
                },
                {
                    "pick": 30,
                    "round": 3,
                    "player": "Puka Nacua LAR",
                    "position": "WR",
                    "column_team": "Test Team",
                },
                {
                    "pick": 40,
                    "round": 4,
                    "player": "Travis Kelce KC",
                    "position": "TE",
                    "column_team": "Test Team",
                },
                # Other team's pick should not be counted
                {
                    "pick": 1,
                    "round": 1,
                    "player": "Christian McCaffrey SF",
                    "position": "RB",
                    "column_team": "Other Team",
                },
            ],
            "teams": [
                {"team_name": "Test Team", "owner": "Test Owner", "team_number": 1},
                {"team_name": "Other Team", "owner": "Other Owner", "team_number": 2},
            ],
            "current_pick": 50,
        }

        # Mock rankings response
        mock_rankings_result = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Available Player",
                        "position": "WR",
                        "team": "FA",
                        "bye_week": 10,
                        "average_rank": 100,
                        "average_score": 100,
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.player_rankings.get_player_rankings") as mock_rankings:
            mock_rankings.return_value = mock_rankings_result

            result = await suggest_draft_pick(mock_draft_state, owner_name="Test Owner")

            # Verify success
            assert result["success"] is True, f"Function failed: {result.get('error')}"
            assert "roster_analysis" in result

            roster_analysis = result["roster_analysis"]
            position_needs = roster_analysis["position_needs"]
            current_roster = roster_analysis["current_roster"]

            # Verify correct counts with column_team field
            assert position_needs["QB"]["current_count"] == 1, "Should find 1 QB"
            assert position_needs["RB"]["current_count"] == 1, "Should find 1 RB"
            assert position_needs["WR"]["current_count"] == 1, "Should find 1 WR"
            assert position_needs["TE"]["current_count"] == 1, "Should find 1 TE"

            # Verify players are in roster (using 'player' field)
            assert len(current_roster["QB"]) == 1
            assert "Brock Purdy" in current_roster["QB"][0].get("player", "")

            assert len(current_roster["RB"]) == 1
            assert "Bijan Robinson" in current_roster["RB"][0].get("player", "")

            # Verify other team's picks are NOT counted
            all_players = []
            for position_players in current_roster.values():
                for p in position_players:
                    all_players.append(p.get("player", ""))

            assert not any(
                "Christian McCaffrey" in player for player in all_players
            ), "Other team's picks should not be in Test Team's roster"

    @pytest.mark.asyncio
    async def test_roster_analysis_mixed_field_formats(self):
        """Test roster analysis handles both old and new field formats"""

        # Mix of field formats that might occur during transition
        mock_draft_state = {
            "picks": [
                # New format from test data
                {
                    "pick_number": 1,
                    "round": 1,
                    "player_name": "Player One",
                    "position": "QB",
                    "team": "Test Team",
                },
                # Old format from sheets
                {
                    "pick": 2,
                    "round": 1,
                    "player": "Player Two",
                    "position": "RB",
                    "column_team": "Test Team",
                },
            ],
            "teams": [{"team_name": "Test Team", "owner": "Test Owner"}],
            "current_pick": 3,
        }

        mock_rankings_result = {
            "success": True,
            "aggregated": {
                "players": [
                    {
                        "name": "Available Player",
                        "position": "WR",
                        "team": "FA",
                        "bye_week": 10,
                        "average_rank": 100,
                        "average_score": 100,
                        "injury_status": None,
                    }
                ]
            },
        }

        with patch("src.tools.player_rankings.get_player_rankings") as mock_rankings:
            mock_rankings.return_value = mock_rankings_result

            result = await suggest_draft_pick(mock_draft_state, owner_name="Test Owner")

            # Should handle both formats
            assert result["success"] is True, f"Function failed: {result.get('error')}"
            position_needs = result["roster_analysis"]["position_needs"]

            assert position_needs["QB"]["current_count"] == 1
            assert position_needs["RB"]["current_count"] == 1
