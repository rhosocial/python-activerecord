"""
Interface for model update behavior customization.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

class IUpdateBehavior(ABC):
    """Interface for defining model update behavior.

    Allows models to add custom conditions and expressions during updates.
    Useful for implementing features like optimistic locking.
    """
    @abstractmethod
    def get_update_conditions(self) -> List[Tuple[str, Optional[tuple]]]:
        """Get additional update conditions.

        Returns:
            List[Tuple[str, Optional[tuple]]]: List of (condition_sql, params) tuples

        Example:
            def get_update_conditions(self):
                return [
                    ('version = ?', (self.version,)),
                    ('updated_at = ?', (self.updated_at,))
                ]
        """
        pass

    @abstractmethod
    def get_update_expressions(self) -> Dict[str, Any]:
        """Get update field expressions.

        Returns:
            Dict[str, Any]: Mapping of field names to expressions

        Example:
            def get_update_expressions(self):
                return {
                    'version': self.version + 1,
                    'updated_at': 'CURRENT_TIMESTAMP'
                }
        """
        pass