# src/rhosocial/activerecord/backend/impl/{{backend_name}}/config.py
"""
{{BackendName}} connection configuration.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class {{BackendName}}ConnectionConfig:
    """
    {{backend_name}} database connection configuration.
    
    Attributes:
        host: Database server host
        port: Database server port
        database: Database name
        username: Authentication username
        password: Authentication password
        charset: Character encoding (default: utf8mb4)
        timeout: Connection timeout in seconds
        pool_size: Connection pool size
        
    Example:
        >>> config = {{BackendName}}ConnectionConfig(
        ...     host="localhost",
        ...     port=5432,
        ...     database="mydb",
        ...     username="user",
        ...     password="secret"
        ... )
    """
    
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    charset: str = "utf8mb4"
    timeout: int = 30
    pool_size: int = 5
    
    def to_connection_string(self) -> str:
        """
        Generate connection string.
        
        Returns:
            Database connection string
        """
        return f"{{driver}}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
