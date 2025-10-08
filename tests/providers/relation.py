"""
Relation Provider for SQLite Backend

This module contains the concrete implementation of the IRelationProvider interface
for the SQLite backend. It sets up models with proper relations and provides
the required functionality to run the testsuite's relation tests against SQLite.
"""
from typing import Type, List, Tuple
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from .scenarios import get_scenario


from rhosocial.activerecord.testsuite.feature.relation.interfaces import IRelationProvider

class RelationProvider(IRelationProvider):
    """
    Concrete implementation of the IRelationProvider interface for SQLite.
    """
    
    def __init__(self):
        # Initialize with default SQLite backend - will be configured based on scenario
        self.backend = None
        # Track the actual database file used for each scenario in the current test
        self._scenario_db_files = {}
    
    def get_test_scenarios(self) -> List[str]:
        """
        Return a list of scenario names that this backend supports for relation tests.
        """
        from .scenarios import get_enabled_scenarios
        return list(get_enabled_scenarios().keys())
    
    def setup_employee_department_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord]]:
        """
        Set up employee and department models with relations for testing.
        """
        # Get the original config for the requested scenario
        backend_class, original_config = get_scenario(scenario_name)
        
        # Check if this is a file-based scenario, and if so, generate a unique filename
        import os
        import tempfile
        import uuid
        
        if original_config.database != ":memory:":
            # For file-based scenarios, create a unique temporary file
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite"
            )
            
            # Store the actual database file used for this scenario in this test
            self._scenario_db_files[scenario_name] = unique_filename
            
            # Create a new config with the unique database path
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas
            )
        else:
            # For in-memory scenarios, use original config
            config = original_config
        
        # Create a backend instance with the (potentially modified) scenario configuration
        self.backend = backend_class(**config.__dict__)
        
        # Import models from the testsuite
        from rhosocial.activerecord.testsuite.feature.relation.fixtures.models import Employee, Department
        
        # Configure models with backend
        Employee.configure(self.backend)
        Department.configure(self.backend)
        
        # Create tables in database
        self.backend.execute_sql(Employee._create_table_sql())
        self.backend.execute_sql(Department._create_table_sql())
        
        # Return the configured models as a tuple
        return (Employee, Department)
    
    def setup_author_book_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """
        Set up author, book, chapter, and profile models with relations for testing.
        """
        # Get the original config for the requested scenario
        backend_class, original_config = get_scenario(scenario_name)
        
        # Check if this is a file-based scenario, and if so, generate a unique filename
        import os
        import tempfile
        import uuid
        
        if original_config.database != ":memory:":
            # For file-based scenarios, create a unique temporary file
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite"
            )
            
            # Note: Since this method might be called multiple times in one test,
            # we don't want to overwrite the scenario file if it's already set
            if scenario_name not in self._scenario_db_files:
                self._scenario_db_files[scenario_name] = unique_filename
            
            # Create a new config with the unique database path
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas
            )
        else:
            # For in-memory scenarios, use original config
            config = original_config
        
        # Create a backend instance with the (potentially modified) scenario configuration
        self.backend = backend_class(**config.__dict__)
        
        # Import models from the testsuite
        from rhosocial.activerecord.testsuite.feature.relation.fixtures.models import Author, Book, Chapter, Profile
        
        # Configure models with backend
        Author.configure(self.backend)
        Book.configure(self.backend)
        Chapter.configure(self.backend)
        Profile.configure(self.backend)
        
        # Create tables in database
        self.backend.execute_sql(Author._create_table_sql())
        self.backend.execute_sql(Book._create_table_sql())
        self.backend.execute_sql(Chapter._create_table_sql())
        self.backend.execute_sql(Profile._create_table_sql())
        
        # Return the configured models as a tuple
        return (Author, Book, Chapter, Profile)
    
    def cleanup_after_test(self, scenario_name: str):
        """
        Perform cleanup after relation tests.
        """
        # Use the dynamically generated database file if available, otherwise use the original config
        if scenario_name in self._scenario_db_files:
            import os
            db_file = self._scenario_db_files[scenario_name]
            if os.path.exists(db_file):
                try:
                    # Attempt to remove the temp db file.
                    os.remove(db_file)
                    # Remove from tracking dict
                    del self._scenario_db_files[scenario_name]
                except OSError:
                    # Ignore errors if the file is already gone or locked, etc.
                    pass
        
        # For in-memory database, cleanup is minimal
        # In a file-based scenario, we might need to delete the file
        if self.backend and hasattr(self.backend, '_connection'):
            self.backend.disconnect()