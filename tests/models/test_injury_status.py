"""Tests for the InjuryStatus enum."""

import pytest

from src.models.injury_status import InjuryStatus


class TestInjuryStatus:
    def test_injury_status_values(self):
        """Test that all injury status values are defined correctly."""
        assert InjuryStatus.HEALTHY.value == "HEALTHY"
        assert InjuryStatus.PROBABLE.value == "P"
        assert InjuryStatus.QUESTIONABLE.value == "Q"
        assert InjuryStatus.DOUBTFUL.value == "D"
        assert InjuryStatus.OUT.value == "O"
        assert InjuryStatus.INJURED_RESERVE.value == "IR"

    def test_injury_status_from_string(self):
        """Test creating injury status from string values."""
        assert InjuryStatus("HEALTHY") == InjuryStatus.HEALTHY
        assert InjuryStatus("P") == InjuryStatus.PROBABLE
        assert InjuryStatus("Q") == InjuryStatus.QUESTIONABLE
        assert InjuryStatus("D") == InjuryStatus.DOUBTFUL
        assert InjuryStatus("O") == InjuryStatus.OUT
        assert InjuryStatus("IR") == InjuryStatus.INJURED_RESERVE

    def test_injury_status_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            InjuryStatus("INVALID")

    def test_all_statuses_present(self):
        """Test that we have exactly 6 injury statuses."""
        assert len(list(InjuryStatus)) == 6
