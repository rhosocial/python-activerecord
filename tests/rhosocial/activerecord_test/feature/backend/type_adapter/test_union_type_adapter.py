# tests/rhosocial/activerecord_test/feature/backend/type_adapter/test_union_type_adapter.py
import pytest
from typing import Optional, Union, Type, Dict, Any
from datetime import datetime

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.errors import IntegrityError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.base.fields import UseAdapter


# 1a. Define a custom adapter for testing
class YesOrNoBooleanAdapter(BaseSQLTypeAdapter):
    """Converts Python's True/False to 'yes'/'no' strings."""
    def _do_to_database(self, value: bool, target_type: Type, options: Optional[Dict[str, Any]] = None) -> str:
        return "yes" if value else "no"

    def _do_from_database(self, value: str, target_type: Type, options: Optional[Dict[str, Any]] = None) -> bool:
        return value == "yes"


# 1b. Define the ActiveRecord model for testing
class TypeAdapterTest(ActiveRecord):
    __table_name__ = 'type_adapter_tests'
    __primary_key__ = 'id'

    id: Optional[int] = None
    name: str
    # Fields for testing implicit Optional[T] handling
    optional_name: Optional[str] = None
    optional_age: Optional[int] = None
    last_login: Optional[datetime] = None
    is_premium: Optional[bool] = None
    # Field for testing unsupported Union
    unsupported_union: Union[str, int] = 0
    # Fields for testing explicit adapter annotation
    custom_bool: Annotated[bool, UseAdapter(YesOrNoBooleanAdapter(), str)] = None
    optional_custom_bool: Annotated[Optional[bool], UseAdapter(YesOrNoBooleanAdapter(), str)] = None


# 2. Define the corresponding schema
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS type_adapter_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    optional_name TEXT,
    optional_age INTEGER,
    last_login TEXT,
    is_premium INTEGER,
    unsupported_union TEXT,
    custom_bool TEXT,
    optional_custom_bool TEXT
);
"""


# 3. Create a setup/teardown fixture
@pytest.fixture
def test_table(db):
    """Fixture to create and drop the test table."""
    # Configure the model with the backend for this test session
    TypeAdapterTest.configure(db.config, type(db))
    db.execute(TABLE_SCHEMA)
    yield
    db.execute("DROP TABLE type_adapter_tests")


from rhosocial.activerecord.base.field_adapter_mixin import AdapterAnnotationHandler


# 4. Write the test cases
class TestUnionTypeAdapter:
    def test_optional_string_conversion(self, db, test_table):
        """Tests that Optional[str] is handled correctly."""
        # Test with a value
        rec1 = TypeAdapterTest(name="test_with_str", optional_name="optional_value", custom_bool=False)
        rec1.save()
        found_rec1 = TypeAdapterTest.find_one(rec1.id)
        assert isinstance(found_rec1.optional_name, str)
        assert found_rec1.optional_name == "optional_value"

        # Test with None
        rec2 = TypeAdapterTest(name="test_with_none", optional_name=None, custom_bool=False)
        rec2.save()
        found_rec2 = TypeAdapterTest.find_one(rec2.id)
        assert found_rec2.optional_name is None

    def test_optional_int_conversion(self, db, test_table):
        """Tests that Optional[int] is handled correctly."""
        # Test with a value
        rec1 = TypeAdapterTest(name="test_with_int", optional_age=30, custom_bool=False)
        rec1.save()
        found_rec1 = TypeAdapterTest.find_one(rec1.id)
        assert isinstance(found_rec1.optional_age, int)
        assert found_rec1.optional_age == 30

        # Test with None
        rec2 = TypeAdapterTest(name="test_with_none_age", optional_age=None, custom_bool=False)
        rec2.save()
        found_rec2 = TypeAdapterTest.find_one(rec2.id)
        assert found_rec2.optional_age is None

    def test_optional_datetime_conversion(self, db, test_table):
        """Tests that Optional[datetime] is handled correctly by its adapter."""
        now = datetime.now().replace(microsecond=0)
        # Test with a value
        rec1 = TypeAdapterTest(name="test_with_datetime", last_login=now, custom_bool=False)
        rec1.save()
        found_rec1 = TypeAdapterTest.find_one(rec1.id)
        assert isinstance(found_rec1.last_login, datetime)
        assert found_rec1.last_login == now

        # Test with None
        rec2 = TypeAdapterTest(name="test_with_none_datetime", last_login=None, custom_bool=False)
        rec2.save()
        found_rec2 = TypeAdapterTest.find_one(rec2.id)
        assert found_rec2.last_login is None

    def test_optional_bool_conversion(self, db, test_table):
        """Tests that Optional[bool] is handled correctly by its adapter."""
        # Test with a value
        rec1 = TypeAdapterTest(name="test_with_bool_true", is_premium=True, custom_bool=False)
        rec1.save()
        found_rec1 = TypeAdapterTest.find_one(rec1.id)
        assert found_rec1.is_premium is True

        rec2 = TypeAdapterTest(name="test_with_bool_false", is_premium=False, custom_bool=False)
        rec2.save()
        found_rec2 = TypeAdapterTest.find_one(rec2.id)
        assert found_rec2.is_premium is False

        # Test with None
        rec3 = TypeAdapterTest(name="test_with_none_bool", is_premium=None, custom_bool=False)
        rec3.save()
        found_rec3 = TypeAdapterTest.find_one(rec3.id)
        assert found_rec3.is_premium is None
        
    def test_non_optional_field_no_regression(self, db, test_table):
        """Tests that a simple non-optional field is not affected."""
        rec = TypeAdapterTest(name="simple_string", custom_bool=False)
        rec.save()
        found_rec = TypeAdapterTest.find_one(rec.id)
        assert isinstance(found_rec.name, str)
        assert found_rec.name == "simple_string"

    def test_unsupported_union_is_handled_gracefully(self, db, test_table):
        """
        Tests that a Union of multiple non-None types is handled gracefully.
        """
        # Save a string value to a field that expects Union[str, int].
        # The `to_database` part will work fine as it will use the string adapter.
        db.execute(
            "INSERT INTO type_adapter_tests (id, name, unsupported_union, custom_bool) VALUES (?, ?, ?, ?)",
            (1, "test_unsupported_union", "some_string", "no")
        )
        
        # When converting from the database, the type adapter logic for Optional[T]
        # will be skipped for Union[str, int]. Pydantic is then able to correctly
        # coerce the string value from the DB into the Union type.
        # Therefore, no error should be raised.
        found_rec = TypeAdapterTest.find_one(1)

        assert found_rec is not None
        assert found_rec.unsupported_union == "some_string"
        assert isinstance(found_rec.unsupported_union, str)

    def test_db_null_with_non_optional_field_raises_error(self, db, test_table):
        """
        Tests that inserting a NULL into a NOT NULL column raises an IntegrityError.
        """
        # Manually trying to insert a record with NULL for the non-optional 'name' field
        # should violate the table's NOT NULL constraint.
        with pytest.raises(IntegrityError) as exc_info:
            db.execute("INSERT INTO type_adapter_tests (id, name) VALUES (?, ?)", (1, None))
        
        assert "NOT NULL constraint failed" in str(exc_info.value)

    def test_annotated_custom_adapter(self, db, test_table):
        """Tests that a field-specific adapter assigned via Annotation works correctly."""
        # Test True value
        rec_true = TypeAdapterTest(name="custom_true", custom_bool=True)
        rec_true.save()
        
        # Verify raw data in DB is 'yes'
        raw_true = db.fetch_one("SELECT custom_bool FROM type_adapter_tests WHERE id = ?", (rec_true.id,))
        assert raw_true["custom_bool"] == "yes"

        # Verify that reading it back converts it to True
        found_true = TypeAdapterTest.find_one(rec_true.id)
        assert found_true.custom_bool is True

        # Test False value
        rec_false = TypeAdapterTest(name="custom_false", custom_bool=False)
        rec_false.save()

        # Verify raw data in DB is 'no'
        raw_false = db.fetch_one("SELECT custom_bool FROM type_adapter_tests WHERE id = ?", (rec_false.id,))
        assert raw_false["custom_bool"] == "no"
        
        # Verify that reading it back converts it to False
        found_false = TypeAdapterTest.find_one(rec_false.id)
        assert found_false.custom_bool is False

    def test_optional_annotated_custom_adapter(self, db, test_table):
        """Tests an Optional field that also has a custom annotated adapter."""
        # Test with True
        rec_true = TypeAdapterTest(name="opt_custom_true", custom_bool=False, optional_custom_bool=True)
        rec_true.save()
        found_true = TypeAdapterTest.find_one(rec_true.id)
        assert found_true.optional_custom_bool is True
        raw_true = db.fetch_one("SELECT optional_custom_bool FROM type_adapter_tests WHERE id = ?", (rec_true.id,))
        assert raw_true["optional_custom_bool"] == "yes"
        
        # Test with False
        rec_false = TypeAdapterTest(name="opt_custom_false", custom_bool=False, optional_custom_bool=False)
        rec_false.save()
        found_false = TypeAdapterTest.find_one(rec_false.id)
        assert found_false.optional_custom_bool is False
        raw_false = db.fetch_one("SELECT optional_custom_bool FROM type_adapter_tests WHERE id = ?", (rec_false.id,))
        assert raw_false["optional_custom_bool"] == "no"

        # Test with None
        rec_none = TypeAdapterTest(name="opt_custom_none", custom_bool=False, optional_custom_bool=None)
        rec_none.save()
        found_none = TypeAdapterTest.find_one(rec_none.id)
        assert found_none.optional_custom_bool is None
        raw_none = db.fetch_one("SELECT optional_custom_bool FROM type_adapter_tests WHERE id = ?", (rec_none.id,))
        assert raw_none["optional_custom_bool"] is None
