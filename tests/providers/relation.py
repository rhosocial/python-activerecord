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


class RelationProvider:
    """
    Concrete implementation of the IRelationProvider interface for SQLite.
    """
    
    def __init__(self):
        # Initialize with default SQLite backend - will be configured based on scenario
        self.backend = None
    
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
        # Get the backend class and config for the requested scenario
        backend_class, config = get_scenario(scenario_name)
        
        # Create a backend instance with the scenario configuration
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
        # Get the backend class and config for the requested scenario
        backend_class, config = get_scenario(scenario_name)
        
        # Create a backend instance with the scenario configuration
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
        # For in-memory database, cleanup is minimal
        # In a file-based scenario, we might need to delete the file
        if self.backend and hasattr(self.backend, '_connection'):
            self.backend.disconnect()