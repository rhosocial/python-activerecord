# tests/rhosocial/activerecord_test/backend/common/test_output.py
import datetime
import decimal
import io
import json
import logging

import pytest

from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider


@pytest.fixture
def sample_data():
    """Provides a sample list of dictionaries for testing output providers."""
    return [
        {
            "id": 1,
            "name": "Test User 1",
            "amount": decimal.Decimal("123.45"),
            "timestamp": datetime.datetime(2023, 1, 1, 12, 0, 0),
            "is_active": True,
            "extra_field": "present"
        },
        {
            "id": 2,
            "name": "Test User 2",
            "amount": decimal.Decimal("67.89"),
            "timestamp": datetime.datetime(2023, 1, 2, 18, 30, 0),
            "is_active": False,
            "extra_field": None
        },
    ]


class TestJsonOutputProvider:
    def test_display_results(self, sample_data, mocker):
        """Test that JSON output is correctly formatted."""
        stdout_mock = mocker.patch('sys.stdout', new_callable=io.StringIO)
        provider = JsonOutputProvider()

        provider.display_results(sample_data)

        output = stdout_mock.getvalue()
        # Verify that the output is valid JSON
        parsed_output = json.loads(output)

        assert len(parsed_output) == 2
        # Check if special types are serialized correctly
        assert parsed_output[0]['amount'] == "123.45"
        assert parsed_output[0]['timestamp'] == "2023-01-01T12:00:00"
        assert parsed_output[1]['is_active'] is False

    def test_display_no_data(self, caplog):
        """Test the message when no data is provided."""
        provider = JsonOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_results([])
        assert "No data returned." in caplog.text

    def test_display_query_error(self, caplog):
        """Test logging of query errors."""
        provider = JsonOutputProvider()
        error = ValueError("Test query error")
        with caplog.at_level(logging.ERROR):
            provider.display_query_error(error)
        assert "Database query error: Test query error" in caplog.text


class TestCsvOutputProvider:
    def test_display_results(self, sample_data, mocker):
        """Test that CSV output is correctly formatted."""
        stdout_mock = mocker.patch('sys.stdout', new_callable=io.StringIO)
        provider = CsvOutputProvider()

        provider.display_results(sample_data)

        output = stdout_mock.getvalue().rstrip('\r\n')
        lines = output.splitlines()

        # Check header
        assert lines[0] == "id,name,amount,timestamp,is_active,extra_field"
        # Check data rows
        assert lines[1] == "1,Test User 1,123.45,2023-01-01T12:00:00,True,present"
        assert lines[2] == "2,Test User 2,67.89,2023-01-02T18:30:00,False,"

    def test_display_no_data(self, caplog):
        """Test the message when no data is provided for CSV."""
        provider = CsvOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_results([])
        assert "No data returned for CSV output." in caplog.text


class TestTsvOutputProvider:
    def test_display_results(self, sample_data, mocker):
        """Test that TSV output is correctly formatted."""
        stdout_mock = mocker.patch('sys.stdout', new_callable=io.StringIO)
        provider = TsvOutputProvider()

        provider.display_results(sample_data)

        output = stdout_mock.getvalue().rstrip('\r\n')
        lines = output.splitlines()

        # Check header (tab-separated)
        assert lines[0] == "id\tname\tamount\ttimestamp\tis_active\textra_field"
        # Check data rows (tab-separated)
        assert lines[1] == "1\tTest User 1\t123.45\t2023-01-01T12:00:00\tTrue\tpresent"
        assert lines[2] == "2\tTest User 2\t67.89\t2023-01-02T18:30:00\tFalse\t"
