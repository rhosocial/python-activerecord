# tests/rhosocial/activerecord_test/feature/backend/common/test_typing.py
from rhosocial.activerecord.backend.typing import QueryResult


class TestQueryResult:
    def test_query_result_creation(self):
        # Test creating QueryResult with data
        result = QueryResult(
            data=[{"id": 1, "name": "Test"}],
            affected_rows=1,
            last_insert_id=1,
            duration=0.1
        )

        assert result.data == [{"id": 1, "name": "Test"}]
        assert result.affected_rows == 1
        assert result.last_insert_id == 1
        assert result.duration == 0.1

    def test_query_result_defaults(self):
        # Test QueryResult with default values
        result = QueryResult()

        assert result.data is None
        assert result.affected_rows == 0
        assert result.last_insert_id is None
        assert result.duration == 0.0
