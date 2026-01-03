# tests/rhosocial/activerecord_test/feature/backend/test_output_final.py
import pytest
import logging
from rhosocial.activerecord.backend.output import CsvOutputProvider, TsvOutputProvider

@pytest.mark.parametrize("provider_class", [CsvOutputProvider, TsvOutputProvider])
def test_display_results_with_no_data(capsys, provider_class):
    """
    Tests that display_results calls display_no_data when data is empty.
    This test covers the if not data: return branch in display_results.
    """
    provider = provider_class()
    # Mock display_no_data to check if it's called
    from unittest.mock import MagicMock
    provider.display_no_data = MagicMock()
    
    provider.display_results([])
    
    # Check that display_no_data was called
    provider.display_no_data.assert_called_once()
    
    # Check that nothing was written to stdout
    captured = capsys.readouterr()
    assert captured.out == ""

@pytest.mark.parametrize("provider_class", [CsvOutputProvider, TsvOutputProvider])
def test_format_value_with_none(provider_class):
    """
    Tests the _format_value method with None to cover the else branch.
    """
    provider = provider_class()
    assert provider._format_value(None) == ""
