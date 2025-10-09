# tests/rhosocial/activerecord_test/feature/backend/common/test_helpers_misc.py
import pytest
from unittest.mock import Mock, patch
import time

from rhosocial.activerecord.backend.helpers import measure_time
from rhosocial.activerecord.backend.typing import QueryResult


class TestMeasureTime:
    def test_measure_time_function(self):
        # Define a test function
        @measure_time
        def test_function():
            time.sleep(0.1)
            return "result"

        # Call the function and verify the result
        result = test_function()
        assert result == "result"

    def test_measure_time_with_args(self):
        # Define a test function with arguments
        @measure_time
        def test_function(a, b):
            time.sleep(0.1)
            return a + b

        # Call the function with arguments
        result = test_function(1, 2)
        assert result == 3

    def test_measure_time_with_kwargs(self):
        # Define a test function with keyword arguments
        @measure_time
        def test_function(a, b=2):
            time.sleep(0.1)
            return a + b

        # Call the function with keyword arguments
        result = test_function(1, b=3)
        assert result == 4

    def test_measure_time_with_query_result(self):
        # Define a test function that returns a QueryResult
        @measure_time
        def test_function():
            time.sleep(0.1)
            return QueryResult(data=["test"], affected_rows=1)

        # Call the function and verify the QueryResult has duration
        result = test_function()
        assert isinstance(result, QueryResult)
        assert result.data == ["test"]
        assert result.affected_rows == 1
        assert result.duration > 0
        assert result.duration >= 0.1  # Should be at least the sleep time

    def test_measure_time_without_query_result(self):
        # Define a test function that doesn't return a QueryResult
        @measure_time
        def test_function():
            time.sleep(0.1)
            return {"data": ["test"]}

        # Call the function and verify the result is unchanged
        result = test_function()
        assert isinstance(result, dict)
        assert result["data"] == ["test"]

    def test_measure_time_exception(self):
        # Define a test function that raises an exception
        @measure_time
        def test_function():
            time.sleep(0.1)
            raise ValueError("Test error")

        # Call the function and verify the exception is raised
        with pytest.raises(ValueError, match="Test error"):
            test_function()

    def test_measure_time_mock(self):
        # Use mocks to verify function behavior precisely

        # Create a mock for perf_counter
        mock_time = Mock()
        mock_time.side_effect = [0, 0.5]  # Start time, end time

        # Create a mock QueryResult
        mock_result = QueryResult()

        # Define a test function that returns the mock QueryResult
        @measure_time
        def test_function():
            return mock_result

        # Patch time.perf_counter with our mock
        with patch('time.perf_counter', mock_time):
            result = test_function()

        # Verify the mock was called twice
        assert mock_time.call_count == 2

        # Verify the duration was set correctly on the QueryResult
        assert result.duration == 0.5
