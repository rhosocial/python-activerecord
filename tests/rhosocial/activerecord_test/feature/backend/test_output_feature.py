# tests/rhosocial/activerecord_test/feature/backend/test_output.py
import pytest
import json
import csv
import io
import logging
from unittest.mock import MagicMock, patch
from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
from rhosocial.activerecord.backend.output_rich import RichOutputProvider

@pytest.fixture
def sample_data():
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ]

class TestJsonOutputProvider:
    def test_display_results(self, capsys, sample_data):
        provider = JsonOutputProvider()
        provider.display_results(sample_data)
        captured = capsys.readouterr()
        # The output should be a JSON string of the sample data
        # We can load the captured output and compare it to the original data
        output_data = json.loads(captured.out)
        assert output_data == sample_data

    def test_display_no_data(self, caplog):
        provider = JsonOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_no_data()
        assert "No data returned." in caplog.text

    def test_display_query(self, caplog):
        provider = JsonOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_query("SELECT * FROM users", is_async=False)
        assert "Executing synchronous query: SELECT * FROM users" in caplog.text

class TestCsvOutputProvider:
    def test_display_results(self, capsys, sample_data):
        provider = CsvOutputProvider()
        provider.display_results(sample_data)
        captured = capsys.readouterr()
        
        # The output should be a CSV string
        # We can read the captured output using the csv module
        output_file = io.StringIO(captured.out)
        reader = csv.reader(output_file)
        
        # First row should be the headers
        headers = next(reader)
        assert headers == ["id", "name", "email"]
        
        # Subsequent rows should match the sample data
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0] == ["1", "Alice", "alice@example.com"]
        assert rows[1] == ["2", "Bob", "bob@example.com"]

    def test_display_no_data(self, caplog):
        provider = CsvOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_no_data()
        assert "No data returned for CSV output." in caplog.text

class TestTsvOutputProvider:
    def test_display_results(self, capsys, sample_data):
        provider = TsvOutputProvider()
        provider.display_results(sample_data)
        captured = capsys.readouterr()
        
        # The output should be a TSV string
        output_file = io.StringIO(captured.out)
        reader = csv.reader(output_file, delimiter='	')
        
        # First row should be the headers
        headers = next(reader)
        assert headers == ["id", "name", "email"]
        
        # Subsequent rows should match the sample data
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0] == ["1", "Alice", "alice@example.com"]
        assert rows[1] == ["2", "Bob", "bob@example.com"]

    def test_display_no_data(self, caplog):
        provider = TsvOutputProvider()
        with caplog.at_level(logging.INFO):
            provider.display_no_data()
        assert "No data returned for TSV output." in caplog.text

class TestRichOutputProvider:
    @pytest.fixture
    def mock_console(self):
        return MagicMock()

    def test_display_results(self, mock_console, sample_data):
        provider = RichOutputProvider(console=mock_console)
        provider.display_results(sample_data)
        
        # Check that the print method of the console was called
        mock_console.print.assert_called()

    def test_display_no_data(self, mock_console):
        provider = RichOutputProvider(console=mock_console)
        provider.display_no_data()
        mock_console.print.assert_called_with("[yellow]No data returned for table output.[/yellow]")

    def test_display_connection_error(self, mock_console):
        provider = RichOutputProvider(console=mock_console)
        provider.display_connection_error(Exception("Connection failed"))
        mock_console.print.assert_called()

    def test_display_results_not_list(self, mock_console):
        provider = RichOutputProvider(console=mock_console)
        provider.display_results("not a list")
        mock_console.print.assert_called_with("not a list")

    def test_display_results_list_of_not_dict(self, mock_console):
        provider = RichOutputProvider(console=mock_console)
        provider.display_results(["not a dict"])
        mock_console.print.assert_called_with(["not a dict"])
