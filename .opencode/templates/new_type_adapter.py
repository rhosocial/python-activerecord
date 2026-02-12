# src/rhosocial/activerecord/backend/impl/BACKEND_NAME/type_adapter.py
"""
BACKEND_NAME type adapter implementation.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional
from ...base.type_adapter import TypeAdapter


class BACKEND_NAMETYPEAdapter(TypeAdapter):
    """
    BACKEND_NAME type adapter.
    
    Converts between Python types and BACKEND_NAME database types.
    """
    
    def __init__(self):
        """Initialize type adapter."""
        self._adapters = {}
        self._register_default_adapters()
    
    def _register_default_adapters(self) -> None:
        """Register default type adapters."""
        # Python -> Database type mappings
        self.register(str, self._to_string)
        self.register(int, self._to_integer)
        self.register(float, self._to_float)
        self.register(bool, self._to_boolean)
        self.register(datetime, self._to_datetime)
        self.register(date, self._to_date)
        self.register(time, self._to_time)
        self.register(Decimal, self._to_decimal)
    
    # Python -> Database converters
    def _to_string(self, value: str) -> str:
        """Convert string to database format."""
        return value
    
    def _to_integer(self, value: int) -> int:
        """Convert integer to database format."""
        return value
    
    def _to_float(self, value: float) -> float:
        """Convert float to database format."""
        return value
    
    def _to_boolean(self, value: bool) -> Any:
        """Convert boolean to database format."""
        return value
    
    def _to_datetime(self, value: datetime) -> Any:
        """Convert datetime to database format."""
        return value
    
    def _to_date(self, value: date) -> Any:
        """Convert date to database format."""
        return value
    
    def _to_time(self, value: time) -> Any:
        """Convert time to database format."""
        return value
    
    def _to_decimal(self, value: Decimal) -> Any:
        """Convert Decimal to database format."""
        return str(value)
    
    def register(self, python_type: type, adapter: callable) -> None:
        """Register a type adapter."""
        self._adapters[python_type] = adapter
    
    def adapt(self, value: Any) -> Any:
        """Adapt a Python value to database format."""
        if value is None:
            return None
        
        adapter = self._adapters.get(type(value))
        if adapter:
            return adapter(value)
        
        return value
