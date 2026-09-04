# tests/rhosocial/activerecord_test/feature/backend/query/test_output_extended.py
import pytest
import io
import logging
import datetime
import decimal
from unittest.mock import MagicMock
from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
from rhosocial.activerecord.backend.output_rich import RichOutputProvider


def _capture_logger_output(func, logger_name="rhosocial.activerecord.backend.output"):
    """Capture log output from a module-level logger (propagate=False safe)."""
    logger = logging.getLogger(logger_name)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    original_level = logger.level
    original_propagate = logger.propagate
    original_handlers = list(logger.handlers)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        func()
        return stream.getvalue()
    finally:
        logger.handlers.clear()
        for h in original_handlers:
            logger.addHandler(h)
        logger.setLevel(original_level)
        logger.propagate = original_propagate


class TestJsonOutputProviderExtended:
    def test_json_serializer(self):
        provider = JsonOutputProvider()

        # Test datetime serialization
        now = datetime.datetime.now()
        assert provider._json_serializer(now) == now.isoformat()

        # Test timedelta serialization
        delta = datetime.timedelta(days=1)
        assert provider._json_serializer(delta) == str(delta)

        # Test decimal serialization
        dec = decimal.Decimal("10.5")
        assert provider._json_serializer(dec) == "10.5"

        # Test unserializable type
        with pytest.raises(TypeError):
            provider._json_serializer(object())

    def test_display_methods(self):
        provider = JsonOutputProvider()

        output = _capture_logger_output(lambda: provider.display_success(1, 0.1))
        assert "Query executed successfully" in output

        output = _capture_logger_output(lambda: provider.display_no_result_object())
        assert "Query executed, but no result object returned." in output

        output = _capture_logger_output(lambda: provider.display_connection_error(Exception("Conn error")))
        assert "Database connection error: Conn error" in output

        output = _capture_logger_output(lambda: provider.display_query_error(Exception("Query error")))
        assert "Database query error: Query error" in output

        output = _capture_logger_output(
            lambda: provider.display_unexpected_error(Exception("Unexpected"), is_async=False)
        )
        assert "An unexpected error occurred during synchronous execution: Unexpected" in output

        output = _capture_logger_output(lambda: provider.display_disconnect(is_async=True))
        assert "Disconnected from database (asynchronous)." in output

        output = _capture_logger_output(lambda: provider.display_greeting())
        assert "Output format set to JSON." in output


class TestCsvTsvOutputProviderExtended:
    @pytest.mark.parametrize(
        "provider_class, expected_no_data_msg",
        [
            (CsvOutputProvider, "No data returned for CSV output."),
            (TsvOutputProvider, "No data returned for TSV output."),
        ],
    )
    def test_display_no_data(self, provider_class, expected_no_data_msg):
        provider = provider_class()
        output = _capture_logger_output(lambda: provider.display_no_data())
        assert expected_no_data_msg in output

    @pytest.mark.parametrize(
        "provider_class, expected_no_result_msg",
        [
            (CsvOutputProvider, "Query executed, but no result object returned for CSV output."),
            (TsvOutputProvider, "Query executed, but no result object returned for TSV output."),
        ],
    )
    def test_display_no_result_object(self, provider_class, expected_no_result_msg):
        provider = provider_class()
        output = _capture_logger_output(lambda: provider.display_no_result_object())
        assert expected_no_result_msg in output

    @pytest.mark.parametrize("provider_class", [CsvOutputProvider, TsvOutputProvider])
    def test_all_display_methods(self, provider_class):
        provider = provider_class()

        output = _capture_logger_output(lambda: provider.display_query("SELECT 1", is_async=True))
        assert "Executing asynchronous query: SELECT 1" in output

        output = _capture_logger_output(lambda: provider.display_success(5, 0.5))
        assert "Query executed successfully. Affected rows: 5, Duration: 0.5000s" in output

        output = _capture_logger_output(lambda: provider.display_connection_error(Exception("Test conn error")))
        assert "Database connection error: Test conn error" in output

        output = _capture_logger_output(lambda: provider.display_query_error(Exception("Test query error")))
        assert "Database query error: Test query error" in output

        output = _capture_logger_output(
            lambda: provider.display_unexpected_error(Exception("Test unexpected error"), is_async=True)
        )
        assert "An unexpected error occurred during asynchronous execution: Test unexpected error" in output

        output = _capture_logger_output(lambda: provider.display_disconnect(is_async=False))
        assert "Disconnected from database (synchronous)." in output

        output = _capture_logger_output(lambda: provider.display_greeting())
        if isinstance(provider, CsvOutputProvider):
            assert "Output format set to CSV." in output
        else:
            assert "Output format set to TSV." in output


class TestRichOutputProviderExtended:
    @pytest.fixture
    def mock_console(self):
        return MagicMock()

    def test_all_display_methods(self, mock_console):
        provider = RichOutputProvider(console=mock_console)

        provider.display_query("SELECT *", is_async=False)
        mock_console.print.assert_called_with("Executing synchronous query: [bold cyan]SELECT *[/bold cyan]")

        provider.display_success(10, 0.1234)
        mock_console.print.assert_called_with(
            "[bold green]Query executed successfully.[/bold green] Affected rows: [bold cyan]10[/bold cyan], Duration: [bold cyan]0.1234s[/bold cyan]"  # noqa: E501
        )

        provider.display_no_result_object()
        mock_console.print.assert_called_with(
            "[yellow]Query executed, but no result object returned for table output.[/yellow]"
        )

        provider.display_query_error(Exception("Test query error"))
        mock_console.print.assert_called()

        provider.display_unexpected_error(Exception("Test unexpected error"), is_async=True)
        mock_console.print.assert_called()

        provider.display_disconnect(is_async=False)
        mock_console.print.assert_called_with("[dim]Disconnected from database (synchronous).[/dim]")

        provider.display_greeting()
        mock_console.print.assert_called_with(
            "[bold green]Rich library detected. Using beautified table output.[/bold green]"
        )
