# src/rhosocial/activerecord/backend/output.py
import datetime
import decimal
import json
import logging
import sys
import csv
from typing import Any, List, Dict

from .output_abc import OutputProvider

logger = logging.getLogger(__name__)


class JsonOutputProvider(OutputProvider):
    """Output provider for JSON text logging."""

    def _json_serializer(self, obj: Any) -> str:
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def display_query(self, query: str, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Executing {mode} query: {query}")

    def display_success(self, affected_rows: int, duration: float):
        logger.info(f"Query executed successfully. Affected rows: {affected_rows}, Duration: {duration:.4f}s")

    def display_results(self, data: List[Dict[str, Any]], **kwargs):
        if not data:
            self.display_no_data()
            return
        sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False, default=self._json_serializer) + '\n')

    def display_no_data(self):
        logger.info("No data returned.")

    def display_no_result_object(self):
        logger.info("Query executed, but no result object returned.")

    def display_connection_error(self, error: Exception):
        logger.error(f"Database connection error: {error}")

    def display_query_error(self, error: Exception):
        logger.error(f"Database query error: {error}")

    def display_unexpected_error(self, error: Exception, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.error(f"An unexpected error occurred during {mode} execution: {error}", exc_info=True)

    def display_disconnect(self, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Disconnected from database ({mode}).")

    def display_greeting(self):
        logger.info("Output format set to JSON.")


class CsvOutputProvider(OutputProvider):
    """Output provider for CSV format."""

    def _format_value(self, value: Any) -> str:
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return str(value)
        return str(value) if value is not None else ""

    def display_query(self, query: str, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Executing {mode} query: {query}")

    def display_success(self, affected_rows: int, duration: float):
        logger.info(f"Query executed successfully. Affected rows: {affected_rows}, Duration: {duration:.4f}s")

    def display_results(self, data: List[Dict[str, Any]], **kwargs):
        if not data:
            self.display_no_data()
            return

        headers = list(data[0].keys())
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        for row in data:
            writer.writerow([self._format_value(row.get(header)) for header in headers])

    def display_no_data(self):
        logger.info("No data returned for CSV output.")

    def display_no_result_object(self):
        logger.info("Query executed, but no result object returned for CSV output.")

    def display_connection_error(self, error: Exception):
        logger.error(f"Database connection error: {error}")

    def display_query_error(self, error: Exception):
        logger.error(f"Database query error: {error}")

    def display_unexpected_error(self, error: Exception, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.error(f"An unexpected error occurred during {mode} execution: {error}", exc_info=True)

    def display_disconnect(self, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Disconnected from database ({mode}).")

    def display_greeting(self):
        logger.info("Output format set to CSV.")


class TsvOutputProvider(OutputProvider):
    """Output provider for TSV format."""

    def _format_value(self, value: Any) -> str:
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return str(value)
        return str(value) if value is not None else ""

    def display_query(self, query: str, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Executing {mode} query: {query}")

    def display_success(self, affected_rows: int, duration: float):
        logger.info(f"Query executed successfully. Affected rows: {affected_rows}, Duration: {duration:.4f}s")

    def display_results(self, data: List[Dict[str, Any]], **kwargs):
        if not data:
            self.display_no_data()
            return

        headers = list(data[0].keys())
        writer = csv.writer(sys.stdout, delimiter='\t')
        writer.writerow(headers)
        for row in data:
            writer.writerow([self._format_value(row.get(header)) for header in headers])

    def display_no_data(self):
        logger.info("No data returned for TSV output.")

    def display_no_result_object(self):
        logger.info("Query executed, but no result object returned for TSV output.")

    def display_connection_error(self, error: Exception):
        logger.error(f"Database connection error: {error}")

    def display_query_error(self, error: Exception):
        logger.error(f"Database query error: {error}")

    def display_unexpected_error(self, error: Exception, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.error(f"An unexpected error occurred during {mode} execution: {error}", exc_info=True)

    def display_disconnect(self, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Disconnected from database ({mode}).")

    def display_greeting(self):
        logger.info("Output format set to TSV.")
