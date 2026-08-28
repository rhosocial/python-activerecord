# tests/providers/basic.py
"""
This file provides the concrete implementation of the `IBasicProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.

Its main responsibilities are:
1.  Reporting which test scenarios (database configurations) are available.
2.  Setting up the database environment for a given test. This includes:
    - Getting the correct database configuration for the scenario.
    - Configuring the ActiveRecord model with a database connection.
    - Dropping any old tables and creating the necessary table schema.
3.  Cleaning up any resources (like temporary database files) after a test runs.
"""

import os
import sys
import logging
from typing import Type, List, Tuple

from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.model import ActiveRecord

# Setup logging for fixture selection debugging
logger = logging.getLogger(__name__)

# Import the fixture selector utility
from rhosocial.activerecord.testsuite.utils import select_fixture  # noqa: E402

# Import base version models (Python 3.8+)
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (  # noqa: E402
    User as UserBase,
    TypeCase as TypeCaseBase,
    ValidatedFieldUser as ValidatedFieldUserBase,
    TypeTestModel as TypeTestModelBase,
    ValidatedUser as ValidatedUserBase,
    PydanticValidatedModel as PydanticValidatedModelBase,
    TypeAdapterTest as TypeAdapterTestBase,
    YesOrNoBooleanAdapter,
    MappedUser as MappedUserBase,
    MappedPost as MappedPostBase,
    MappedComment as MappedCommentBase,
    ColumnMappingModel as ColumnMappingModelBase,
    MixedAnnotationModel as MixedAnnotationModelBase,
)
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (  # noqa: E402
    BulkUser as BulkUserBase,
    AsyncBulkUser as AsyncBulkUserBase,
)

# Import async base models
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (  # noqa: E402
    AsyncUser as AsyncUserBase,
    AsyncTypeCase as AsyncTypeCaseBase,
    AsyncValidatedUser as AsyncValidatedUserBase,
    AsyncValidatedFieldUser as AsyncValidatedFieldUserBase,
    AsyncPydanticValidatedModel as AsyncPydanticValidatedModelBase,
    AsyncTypeTestModel as AsyncTypeTestModelBase,
    AsyncTypeAdapterTest as AsyncTypeAdapterTestBase,
    AsyncMappedUser as AsyncMappedUserBase,
    AsyncMappedPost as AsyncMappedPostBase,
    AsyncMappedComment as AsyncMappedCommentBase,
    AsyncColumnMappingModel as AsyncColumnMappingModelBase,
    AsyncMixedAnnotationModel as AsyncMixedAnnotationModelBase,
)

# Conditionally import Python 3.10+ models
User310 = TypeCase310 = ValidatedFieldUser310 = TypeTestModel310 = ValidatedUser310 = None
PydanticValidatedModel310 = TypeAdapterTest310 = MappedUser310 = MappedPost310 = MappedComment310 = None
ColumnMappingModel310 = MixedAnnotationModel310 = None
AsyncUser310 = AsyncTypeCase310 = AsyncValidatedFieldUser310 = AsyncTypeTestModel310 = None
AsyncValidatedUser310 = AsyncPydanticValidatedModel310 = AsyncTypeAdapterTest310 = AsyncMappedUser310 = (
    AsyncMappedPost310
) = None
AsyncMappedComment310 = AsyncColumnMappingModel310 = AsyncMixedAnnotationModel310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py310 import (
            User as User310,
            TypeCase as TypeCase310,
            ValidatedFieldUser as ValidatedFieldUser310,
            TypeTestModel as TypeTestModel310,
            ValidatedUser as ValidatedUser310,
            PydanticValidatedModel as PydanticValidatedModel310,
            TypeAdapterTest as TypeAdapterTest310,
            MappedUser as MappedUser310,
            MappedPost as MappedPost310,
            MappedComment as MappedComment310,
            ColumnMappingModel as ColumnMappingModel310,
            MixedAnnotationModel as MixedAnnotationModel310,
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py310 import (
            AsyncUser as AsyncUser310,
            AsyncTypeCase as AsyncTypeCase310,
            AsyncValidatedUser as AsyncValidatedUser310,
            AsyncValidatedFieldUser as AsyncValidatedFieldUser310,
            AsyncPydanticValidatedModel as AsyncPydanticValidatedModel310,
            AsyncTypeTestModel as AsyncTypeTestModel310,
            AsyncTypeAdapterTest as AsyncTypeAdapterTest310,
            AsyncMappedUser as AsyncMappedUser310,
            AsyncMappedPost as AsyncMappedPost310,
            AsyncMappedComment as AsyncMappedComment310,
            AsyncColumnMappingModel as AsyncColumnMappingModel310,
            AsyncMixedAnnotationModel as AsyncMixedAnnotationModel310,
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

# Conditionally import Python 3.11+ models
User311 = TypeCase311 = ValidatedFieldUser311 = TypeTestModel311 = ValidatedUser311 = None
PydanticValidatedModel311 = TypeAdapterTest311 = MappedUser311 = MappedPost311 = MappedComment311 = None
ColumnMappingModel311 = MixedAnnotationModel311 = None
AsyncUser311 = AsyncTypeCase311 = AsyncValidatedFieldUser311 = AsyncTypeTestModel311 = None
AsyncValidatedUser311 = AsyncPydanticValidatedModel311 = AsyncTypeAdapterTest311 = AsyncMappedUser311 = (
    AsyncMappedPost311
) = None
AsyncMappedComment311 = AsyncColumnMappingModel311 = AsyncMixedAnnotationModel311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py311 import (
            User as User311,
            TypeCase as TypeCase311,
            ValidatedFieldUser as ValidatedFieldUser311,
            TypeTestModel as TypeTestModel311,
            ValidatedUser as ValidatedUser311,
            PydanticValidatedModel as PydanticValidatedModel311,
            TypeAdapterTest as TypeAdapterTest311,
            MappedUser as MappedUser311,
            MappedPost as MappedPost311,
            MappedComment as MappedComment311,
            ColumnMappingModel as ColumnMappingModel311,
            MixedAnnotationModel as MixedAnnotationModel311,
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py311 import (
            AsyncUser as AsyncUser311,
            AsyncTypeCase as AsyncTypeCase311,
            AsyncValidatedUser as AsyncValidatedUser311,
            AsyncValidatedFieldUser as AsyncValidatedFieldUser311,
            AsyncPydanticValidatedModel as AsyncPydanticValidatedModel311,
            AsyncTypeTestModel as AsyncTypeTestModel311,
            AsyncTypeAdapterTest as AsyncTypeAdapterTest311,
            AsyncMappedUser as AsyncMappedUser311,
            AsyncMappedPost as AsyncMappedPost311,
            AsyncMappedComment as AsyncMappedComment311,
            AsyncColumnMappingModel as AsyncColumnMappingModel311,
            AsyncMixedAnnotationModel as AsyncMixedAnnotationModel311,
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

# Conditionally import Python 3.12+ models
User312 = TypeCase312 = ValidatedFieldUser312 = TypeTestModel312 = ValidatedUser312 = None
PydanticValidatedModel312 = TypeAdapterTest312 = MappedUser312 = MappedPost312 = MappedComment312 = None
ColumnMappingModel312 = MixedAnnotationModel312 = None
AsyncUser312 = AsyncTypeCase312 = AsyncValidatedFieldUser312 = AsyncTypeTestModel312 = None
AsyncValidatedUser312 = AsyncPydanticValidatedModel312 = AsyncTypeAdapterTest312 = AsyncMappedUser312 = (
    AsyncMappedPost312
) = None
AsyncMappedComment312 = AsyncColumnMappingModel312 = AsyncMixedAnnotationModel312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py312 import (
            User as User312,
            TypeCase as TypeCase312,
            ValidatedFieldUser as ValidatedFieldUser312,
            TypeTestModel as TypeTestModel312,
            ValidatedUser as ValidatedUser312,
            PydanticValidatedModel as PydanticValidatedModel312,
            TypeAdapterTest as TypeAdapterTest312,
            MappedUser as MappedUser312,
            MappedPost as MappedPost312,
            MappedComment as MappedComment312,
            ColumnMappingModel as ColumnMappingModel312,
            MixedAnnotationModel as MixedAnnotationModel312,
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py312 import (
            AsyncUser as AsyncUser312,
            AsyncTypeCase as AsyncTypeCase312,
            AsyncValidatedUser as AsyncValidatedUser312,
            AsyncValidatedFieldUser as AsyncValidatedFieldUser312,
            AsyncPydanticValidatedModel as AsyncPydanticValidatedModel312,
            AsyncTypeTestModel as AsyncTypeTestModel312,
            AsyncTypeAdapterTest as AsyncTypeAdapterTest312,
            AsyncMappedUser as AsyncMappedUser312,
            AsyncMappedPost as AsyncMappedPost312,
            AsyncMappedComment as AsyncMappedComment312,
            AsyncColumnMappingModel as AsyncColumnMappingModel312,
            AsyncMixedAnnotationModel as AsyncMixedAnnotationModel312,
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.12+ fixtures: {e}")


# Select appropriate fixture classes based on Python version
def _select_model_class(base_cls, py312_cls, py311_cls, py310_cls, model_name: str) -> Type:
    """Select the most appropriate model class for the current Python version."""
    candidates = [c for c in [py312_cls, py311_cls, py310_cls, base_cls] if c is not None]
    selected = select_fixture(*candidates)
    logger.info(f"Selected {model_name}: {selected.__name__} from {selected.__module__}")
    return selected


# Select sync models
User = _select_model_class(UserBase, User312, User311, User310, "User")
TypeCase = _select_model_class(TypeCaseBase, TypeCase312, TypeCase311, TypeCase310, "TypeCase")
ValidatedFieldUser = _select_model_class(
    ValidatedFieldUserBase, ValidatedFieldUser312, ValidatedFieldUser311, ValidatedFieldUser310, "ValidatedFieldUser"
)
TypeTestModel = _select_model_class(
    TypeTestModelBase, TypeTestModel312, TypeTestModel311, TypeTestModel310, "TypeTestModel"
)
ValidatedUser = _select_model_class(
    ValidatedUserBase, ValidatedUser312, ValidatedUser311, ValidatedUser310, "ValidatedUser"
)
PydanticValidatedModel = _select_model_class(
    PydanticValidatedModelBase,
    PydanticValidatedModel312,
    PydanticValidatedModel311,
    PydanticValidatedModel310,
    "PydanticValidatedModel",
)
TypeAdapterTest = _select_model_class(
    TypeAdapterTestBase, TypeAdapterTest312, TypeAdapterTest311, TypeAdapterTest310, "TypeAdapterTest"
)
MappedUser = _select_model_class(MappedUserBase, MappedUser312, MappedUser311, MappedUser310, "MappedUser")
MappedPost = _select_model_class(MappedPostBase, MappedPost312, MappedPost311, MappedPost310, "MappedPost")
MappedComment = _select_model_class(
    MappedCommentBase, MappedComment312, MappedComment311, MappedComment310, "MappedComment"
)
ColumnMappingModel = _select_model_class(
    ColumnMappingModelBase, ColumnMappingModel312, ColumnMappingModel311, ColumnMappingModel310, "ColumnMappingModel"
)
MixedAnnotationModel = _select_model_class(
    MixedAnnotationModelBase,
    MixedAnnotationModel312,
    MixedAnnotationModel311,
    MixedAnnotationModel310,
    "MixedAnnotationModel",
)

# Select async models
AsyncUser = _select_model_class(AsyncUserBase, AsyncUser312, AsyncUser311, AsyncUser310, "AsyncUser")
AsyncTypeCase = _select_model_class(
    AsyncTypeCaseBase, AsyncTypeCase312, AsyncTypeCase311, AsyncTypeCase310, "AsyncTypeCase"
)
AsyncValidatedFieldUser = _select_model_class(
    AsyncValidatedFieldUserBase,
    AsyncValidatedFieldUser312,
    AsyncValidatedFieldUser311,
    AsyncValidatedFieldUser310,
    "AsyncValidatedFieldUser",
)
AsyncTypeTestModel = _select_model_class(
    AsyncTypeTestModelBase, AsyncTypeTestModel312, AsyncTypeTestModel311, AsyncTypeTestModel310, "AsyncTypeTestModel"
)
AsyncValidatedUser = _select_model_class(
    AsyncValidatedUserBase, AsyncValidatedUser312, AsyncValidatedUser311, AsyncValidatedUser310, "AsyncValidatedUser"
)
AsyncPydanticValidatedModel = _select_model_class(
    AsyncPydanticValidatedModelBase,
    AsyncPydanticValidatedModel312,
    AsyncPydanticValidatedModel311,
    AsyncPydanticValidatedModel310,
    "AsyncPydanticValidatedModel",
)
AsyncTypeAdapterTest = _select_model_class(
    AsyncTypeAdapterTestBase,
    AsyncTypeAdapterTest312,
    AsyncTypeAdapterTest311,
    AsyncTypeAdapterTest310,
    "AsyncTypeAdapterTest",
)
AsyncMappedUser = _select_model_class(
    AsyncMappedUserBase, AsyncMappedUser312, AsyncMappedUser311, AsyncMappedUser310, "AsyncMappedUser"
)
AsyncMappedPost = _select_model_class(
    AsyncMappedPostBase, AsyncMappedPost312, AsyncMappedPost311, AsyncMappedPost310, "AsyncMappedPost"
)
AsyncMappedComment = _select_model_class(
    AsyncMappedCommentBase, AsyncMappedComment312, AsyncMappedComment311, AsyncMappedComment310, "AsyncMappedComment"
)
AsyncColumnMappingModel = _select_model_class(
    AsyncColumnMappingModelBase,
    AsyncColumnMappingModel312,
    AsyncColumnMappingModel311,
    AsyncColumnMappingModel310,
    "AsyncColumnMappingModel",
)
AsyncMixedAnnotationModel = _select_model_class(
    AsyncMixedAnnotationModelBase,
    AsyncMixedAnnotationModel312,
    AsyncMixedAnnotationModel311,
    AsyncMixedAnnotationModel310,
    "AsyncMixedAnnotationModel",
)

# BulkUser models (simple, no version-specific variants needed)
BulkUser = BulkUserBase
AsyncBulkUser = AsyncBulkUserBase

from rhosocial.activerecord.testsuite.feature.basic.interfaces import IBasicSyncProvider, IBasicAsyncProvider  # noqa: E402
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (  # noqa: E402
    OrderItem as OrderItemBase,
    Order as OrderBase,
    MappedOrderItem as MappedOrderItemBase,
    AsyncOrderItem as AsyncOrderItemBase,
    AsyncOrder as AsyncOrderBase,
    AsyncMappedOrderItem as AsyncMappedOrderItemBase,
    Product,
    ProductFormA,
    ProductWithProxy,
    ProductWithColumnAndAdapter,
    AsyncProduct,
    AsyncProductFormA,
    AsyncProductWithProxy,
    AsyncProductWithColumnAndAdapter,
)
from rhosocial.activerecord.testsuite.core.protocols import WorkerTestProtocol  # noqa: E402

# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario  # noqa: E402


class BasicProviderBase:
    """
    SQLite-specific shared helper base for basic feature test providers.
    Contains only non-I/O helper methods shared between sync and async providers.
    """

    def __init__(self):
        self._scenario_db_files = {}

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def get_yes_no_adapter(self) -> BaseSQLTypeAdapter:
        """Returns an instance of the YesOrNoBooleanAdapter."""
        return YesOrNoBooleanAdapter()

    def get_dialect(self, scenario_name: str = "default"):
        """Return a bare, fully-constructed SQLite dialect instance.

        Used by the ``feature/basic/ddl`` subtopic (expression/dialect
        contract). ``(3, 53, 0)`` is chosen so that plain ``DROP
        CONSTRAINT`` support is advertised; the three ``IF [NOT] EXISTS``
        modifiers remain unsupported and their ``supports_*`` switches stay
        ``False``.
        """
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        return SQLiteDialect(version=(3, 53, 0))

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        schema_dir = os.path.join(
            os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "basic", "schema"
        )
        schema_path = os.path.join(schema_dir, filename)

        with open(schema_path, "r", encoding="utf-8") as f:
            return f.read()


class BasicSyncProvider(BasicProviderBase, IBasicSyncProvider, WorkerTestProtocol):
    """
    Sync-only SQLite implementation for the basic features test group.
    Connects generic testsuite tests to the actual SQLite database.

    Also implements WorkerTestProtocol to enable WorkerPool tests.
    """

    def __init__(self):
        super().__init__()
        # Track active backend instances for proper cleanup.
        # IMPORTANT: SQLite connections hold file locks. If we attempt to delete
        # the database file before disconnecting, the file remains locked and
        # subsequent tests will hang indefinitely waiting for the lock to release.
        # This was discovered during WorkerPool tests where cleanup would hang
        # on Windows and some Linux configurations.
        # See: python-activerecord-mysql/docs/zh_CN/scenarios/parallel_workers.md
        # See: python-activerecord-postgres/docs/zh_CN/scenarios/parallel_workers.md
        self._active_backends = []

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        # 1. Get the backend class (SQLiteBackend) and connection config for the requested scenario.
        backend_class, original_config = get_scenario(scenario_name)

        # Check if this is a file-based scenario, and if so, generate a unique filename
        import os
        import tempfile
        import uuid

        config = original_config  # default to the original config

        if original_config.database != ":memory:":
            # For file-based scenarios, use a (possibly pooled) database file.
            from providers.pooling import resolve_database_file, should_keep_database

            unique_filename = resolve_database_file(scenario_name)

            # Store the actual database file used for this scenario in this test
            self._scenario_db_files[scenario_name] = unique_filename

            # Create a new config with the unique database path
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close and not should_keep_database(scenario_name),
                pragmas=original_config.pragmas,
            )

        # 2. Configure the generic model class with our specific backend and config.
        #    This is the key step that links the testsuite's model to our database.
        model_class.configure(config, backend_class)

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        try:
            drop_expr = DropTableExpression(
                dialect=model_class.__backend__.dialect,
                table=TableExpression(model_class.__backend__.dialect, table_name),
                if_exists=True,
            )
            model_class.__backend__.execute(
                *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        except Exception:
            pass

        from providers.fixtures.basic import TABLE_EXPRESSIONS

        if fn := TABLE_EXPRESSIONS.get(table_name):
            create_expr = fn(model_class.__backend__.dialect, table_name)
            model_class.__backend__.execute(
                *create_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        else:
            schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
            model_class.__backend__.execute(schema_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Track the backend for proper cleanup
        if model_class.__backend__ not in self._active_backends:
            self._active_backends.append(model_class.__backend__)

        return model_class

    # --- Sync setup methods ---

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `User` model tests."""
        return self._setup_model(User, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeCase` model tests."""
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeTestModel` model tests."""
        return self._setup_model(TypeTestModel, scenario_name, "type_tests")

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `ValidatedFieldUser` model tests."""
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `ValidatedUser` model tests."""
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    def setup_pydantic_validated_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `PydanticValidatedModel` model tests."""
        return self._setup_model(PydanticValidatedModel, scenario_name, "pydantic_validated_models")

    def setup_mapped_models(self, scenario_name: str):
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        user = self._setup_model(MappedUser, scenario_name, "users")
        post = self._setup_model(MappedPost, scenario_name, "posts")
        comment = self._setup_model(MappedComment, scenario_name, "comments")
        return user, post, comment

    def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for ColumnMappingModel and MixedAnnotationModel."""
        column_mapping_model = self._setup_model(ColumnMappingModel, scenario_name, "column_mapping_items")
        mixed_annotation_model = self._setup_model(MixedAnnotationModel, scenario_name, "mixed_annotation_items")
        return column_mapping_model, mixed_annotation_model

    def setup_type_adapter_model_and_schema(self) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeAdapterTest` model tests."""
        scenarios = self.get_test_scenarios()
        scenario_name = scenarios[0] if scenarios else "default"
        return self._setup_model(TypeAdapterTest, scenario_name, "type_adapter_tests")

    def setup_bulk_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `BulkUser` model tests."""
        return self._setup_model(BulkUser, scenario_name, "bulk_users")

    # --- Composite PK setup methods ---

    def setup_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the OrderItem model (composite PK) tests."""
        return self._setup_model(OrderItemBase, scenario_name, "order_items")

    def setup_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the Order model (single PK, used as reference)."""
        return self._setup_model(OrderBase, scenario_name, "orders")

    def setup_mapped_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the MappedOrderItem model (composite PK with column mapping)."""
        return self._setup_model(MappedOrderItemBase, scenario_name, "order_items")

    # --- Derived field setup methods ---

    def setup_product_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(Product, scenario_name, "product")

    def setup_product_form_a_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(ProductFormA, scenario_name, "product")

    def setup_product_with_proxy_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(ProductWithProxy, scenario_name, "product")

    def setup_product_with_column_and_adapter_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(ProductWithColumnAndAdapter, scenario_name, "product")

    def get_worker_connection_params(self, scenario_name: str, fixture_type: str = None) -> dict:
        """
        Return serializable connection parameters for Worker processes.

        This method provides all information needed to recreate the database
        connection in a Worker process, including the schema SQL for table creation.

        Args:
            scenario_name: The test scenario name
            fixture_type: Optional fixture type hint (e.g., 'user', 'async_user')
                         Used to determine if async backend is needed
        """
        if scenario_name in self._scenario_db_files:
            database_path = self._scenario_db_files[scenario_name]
        else:
            _, config = get_scenario(scenario_name)
            database_path = config.database

        is_async = fixture_type and fixture_type.startswith("async_")
        backend_class_name = "AsyncSQLiteBackend" if is_async else "SQLiteBackend"

        table_name = "users"
        if fixture_type:
            base_type = fixture_type.replace("async_", "")
            table_map = {
                "user": "users",
                "order": "orders",
                "order_item": "order_items",
            }
            table_name = table_map.get(base_type, "users")

        from providers.fixtures.basic import TABLE_EXPRESSIONS

        if fn := TABLE_EXPRESSIONS.get(table_name):
            from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
            dialect = SQLiteDialect()
            schema_sql, _ = fn(dialect, table_name).to_sql()
        else:
            schema_sql = self._load_sqlite_schema(f"{table_name}.sql")

        return {
            "backend_module": "rhosocial.activerecord.backend.impl.sqlite",
            "backend_class_name": backend_class_name,
            "config_class_module": "rhosocial.activerecord.backend.impl.sqlite.config",
            "config_class_name": "SQLiteConnectionConfig",
            "config_kwargs": {
                "database": database_path,
            },
            "schema_sql": schema_sql,
        }

    def get_worker_schema_sql(self, scenario_name: str, table_name: str) -> str:
        """
        Return the SQL statement to create a specific table.

        Args:
            scenario_name: The test scenario name (unused for SQLite as schema is fixed)
            table_name: Name of the table to create

        Returns:
            CREATE TABLE SQL statement
        """
        from providers.fixtures.basic import TABLE_EXPRESSIONS

        if fn := TABLE_EXPRESSIONS.get(table_name):
            from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
            dialect = SQLiteDialect()
            sql, _ = fn(dialect, table_name).to_sql()
            return sql
        return self._load_sqlite_schema(f"{table_name}.sql")

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. For file-based scenarios, this involves
        disconnecting backends and deleting the temporary database file.

        CRITICAL: Backend disconnection MUST happen before file deletion.
        SQLite maintains file locks on open connections. Attempting to delete
        a database file while connections are still open will:
        1. Fail silently on Unix (file remains until all handles closed)
        2. Hang indefinitely on Windows (exclusive lock prevents deletion)
        3. Cause subsequent tests to fail due to locked database files
        """
        for backend_instance in self._active_backends:
            try:
                backend_instance.disconnect()
            except Exception:
                pass
        self._active_backends.clear()

        if scenario_name in self._scenario_db_files:
            from providers.pooling import should_keep_database

            if not should_keep_database(scenario_name):
                db_file = self._scenario_db_files[scenario_name]
                if os.path.exists(db_file):
                    try:
                        os.remove(db_file)
                    except OSError:
                        pass
            del self._scenario_db_files[scenario_name]
        else:
            _, config = get_scenario(scenario_name)
            if config.delete_on_close and config.database != ":memory:" and os.path.exists(config.database):
                try:
                    os.remove(config.database)
                except OSError:
                    pass


class BasicAsyncProvider(BasicProviderBase, IBasicAsyncProvider):
    """
    Async-only SQLite implementation for the basic features test group.
    Connects generic testsuite async tests to the actual SQLite database.
    """

    def __init__(self):
        super().__init__()
        # Track active backend instances for proper cleanup.
        # IMPORTANT: SQLite connections hold file locks. If we attempt to delete
        # the database file before disconnecting, the file remains locked and
        # subsequent tests will hang indefinitely waiting for the lock to release.
        self._active_async_backends = []

    async def get_dialect(self, scenario_name: str = "default"):
        """Async mirror of ``BasicProviderBase.get_dialect``."""
        return super().get_dialect(scenario_name)

    async def _setup_async_model(
        self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str
    ) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given async model."""
        # 1. Get the async backend class (AsyncSQLiteBackend) and connection config for the requested scenario.
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        backend_class = AsyncSQLiteBackend
        _, original_config = get_scenario(scenario_name)

        # Check if this is a file-based scenario, and if so, generate a unique filename
        import os
        import tempfile
        import uuid

        config = original_config  # default to the original config

        if original_config.database != ":memory:":
            # For file-based scenarios, use a (possibly pooled) database file.
            from providers.pooling import resolve_database_file, should_keep_database

            unique_filename = resolve_database_file(scenario_name)

            # Store the actual database file used for this scenario in this test
            self._scenario_db_files[scenario_name] = unique_filename

            # Create a new config with the unique database path
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close and not should_keep_database(scenario_name),
                pragmas=original_config.pragmas,
            )

        # 2. Configure the generic async model class with our specific async backend and config.
        #    This is the key step that links the testsuite's async model to our database.
        await model_class.configure(config, backend_class)

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        try:
            drop_expr = DropTableExpression(
                dialect=model_class.__backend__.dialect,
                table=TableExpression(model_class.__backend__.dialect, table_name),
                if_exists=True,
            )
            await model_class.__backend__.execute(
                *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        except Exception:
            pass

        from providers.fixtures.basic import TABLE_EXPRESSIONS

        if fn := TABLE_EXPRESSIONS.get(table_name):
            create_expr = fn(model_class.__backend__.dialect, table_name)
            await model_class.__backend__.execute(
                *create_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        else:
            schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
            await model_class.__backend__.execute(schema_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        if model_class.__backend__ not in self._active_async_backends:
            self._active_async_backends.append(model_class.__backend__)

        return model_class

    # --- Async setup methods ---

    async def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncUser` model tests."""
        return await self._setup_async_model(AsyncUser, scenario_name, "users")

    async def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeCase` model tests."""
        return await self._setup_async_model(AsyncTypeCase, scenario_name, "type_cases")

    async def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeTestModel` model tests."""
        return await self._setup_async_model(AsyncTypeTestModel, scenario_name, "type_tests")

    async def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncValidatedFieldUser` model tests."""
        return await self._setup_async_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncValidatedUser` model tests."""
        return await self._setup_async_model(AsyncValidatedUser, scenario_name, "validated_users")

    async def setup_pydantic_validated_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncPydanticValidatedModel` model tests."""
        return await self._setup_async_model(AsyncPydanticValidatedModel, scenario_name, "pydantic_validated_models")

    async def setup_mapped_models(self, scenario_name: str):
        """Sets up the database for AsyncMappedUser, AsyncMappedPost, and AsyncMappedComment models."""
        user = await self._setup_async_model(AsyncMappedUser, scenario_name, "users")
        shared_backend = user.__backend__

        post_model_class = AsyncMappedPost
        post_model_class.__connection_config__ = user.__connection_config__
        post_model_class.__backend_class__ = user.__backend_class__
        post_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(post_model_class, scenario_name, "posts")

        comment_model_class = AsyncMappedComment
        comment_model_class.__connection_config__ = user.__connection_config__
        comment_model_class.__backend_class__ = user.__backend_class__
        comment_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(comment_model_class, scenario_name, "comments")

        return user, post_model_class, comment_model_class

    async def _initialize_async_model_schema(
        self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str
    ):
        """Initialize schema for a model that shares backend with another model."""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        drop_expr = DropTableExpression(
            dialect=model_class.__backend__.dialect,
            table=TableExpression(model_class.__backend__.dialect, table_name),
            if_exists=True,
        )
        await model_class.__backend__.execute(*drop_expr.to_sql(), options=options)

        from providers.fixtures.basic import TABLE_EXPRESSIONS

        if fn := TABLE_EXPRESSIONS.get(table_name):
            create_expr = fn(model_class.__backend__.dialect, table_name)
            await model_class.__backend__.execute(*create_expr.to_sql(), options=options)
        else:
            schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
            await model_class.__backend__.execute(schema_sql, options=options)

    async def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for AsyncColumnMappingModel and AsyncMixedAnnotationModel."""
        column_mapping_model = await self._setup_async_model(
            AsyncColumnMappingModel, scenario_name, "column_mapping_items"
        )
        shared_backend = column_mapping_model.__backend__

        mixed_annotation_model_class = AsyncMixedAnnotationModel
        mixed_annotation_model_class.__connection_config__ = column_mapping_model.__connection_config__
        mixed_annotation_model_class.__backend_class__ = column_mapping_model.__backend_class__
        mixed_annotation_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(mixed_annotation_model_class, scenario_name, "mixed_annotation_items")

        return column_mapping_model, mixed_annotation_model_class

    async def setup_type_adapter_model_and_schema(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeAdapterTest` model tests."""
        return await self._setup_async_model(AsyncTypeAdapterTest, scenario_name, "type_adapter_tests")

    async def setup_bulk_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncBulkUser` model tests."""
        return await self._setup_async_model(AsyncBulkUser, scenario_name, "bulk_users")

    # --- Composite PK async setup methods ---

    async def setup_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderItemBase, scenario_name, "order_items")

    async def setup_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderBase, scenario_name, "orders")

    async def setup_mapped_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncMappedOrderItemBase, scenario_name, "order_items")

    # --- Derived field async setup methods ---

    async def setup_product_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncProduct, scenario_name, "product")

    async def setup_product_form_a_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncProductFormA, scenario_name, "product")

    async def setup_product_with_proxy_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncProductWithProxy, scenario_name, "product")

    async def setup_product_with_column_and_adapter_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncProductWithColumnAndAdapter, scenario_name, "product")

    async def cleanup_after_test(self, scenario_name: str):
        """
        Performs async cleanup after a test. For file-based scenarios, this involves
        deleting the temporary database file.

        CRITICAL: Backend disconnection MUST happen before file deletion.
        See cleanup_after_test() for details on SQLite file locking behavior.
        """
        for backend_instance in self._active_async_backends:
            try:
                await backend_instance.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()

        if scenario_name in self._scenario_db_files:
            from providers.pooling import should_keep_database

            if not should_keep_database(scenario_name):
                db_file = self._scenario_db_files[scenario_name]
                if os.path.exists(db_file):
                    try:
                        os.remove(db_file)
                    except OSError:
                        pass
            del self._scenario_db_files[scenario_name]
        else:
            _, config = get_scenario(scenario_name)
            if config.delete_on_close and config.database != ":memory:" and os.path.exists(config.database):
                try:
                    os.remove(config.database)
                except OSError:
                    pass
