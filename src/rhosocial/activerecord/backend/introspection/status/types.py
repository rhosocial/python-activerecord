# src/rhosocial/activerecord/backend/introspection/status/types.py
"""
Server status data structures for introspection.

This module defines dataclasses for representing database server status
information in a database-agnostic way, enabling unified status reporting
across different database backends.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class StatusCategory(Enum):
    """Categories for grouping server status items."""

    CONFIGURATION = "configuration"  # Configuration parameters
    PERFORMANCE = "performance"      # Performance metrics
    CONNECTION = "connection"        # Connection information
    STORAGE = "storage"              # Storage information
    SECURITY = "security"            # Security related
    REPLICATION = "replication"      # Replication related


@dataclass
class StatusItem:
    """A single server status item (configuration parameter or metric).

    Attributes:
        name: Parameter name
        value: Current value
        category: Category for grouping
        description: Human-readable description
        unit: Unit of measurement (e.g., "bytes", "seconds", "connections")
        is_readonly: Whether this parameter is read-only
        is_dynamic: Whether this parameter can be changed at runtime
        default_value: Default value for this parameter
        extra: Additional backend-specific information
    """

    name: str
    value: Any
    category: StatusCategory = StatusCategory.CONFIGURATION
    description: Optional[str] = None
    unit: Optional[str] = None
    is_readonly: bool = False
    is_dynamic: bool = True
    default_value: Optional[Any] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseBriefInfo:
    """Brief database/schema information for status overview.

    A simplified version of DatabaseInfo focused on status display.
    """

    name: str
    schema: Optional[str] = None
    owner: Optional[str] = None
    encoding: Optional[str] = None
    size_bytes: Optional[int] = None
    table_count: Optional[int] = None
    view_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInfo:
    """User/role information for status overview.

    Attributes:
        name: User/role name
        host: Host restriction (MySQL style)
        roles: Assigned roles
        is_superuser: Whether this user has superuser privileges
        extra: Additional backend-specific information
    """

    name: str
    host: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    is_superuser: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionInfo:
    """Connection-related status information.

    Attributes:
        active_count: Number of active connections
        max_connections: Maximum allowed connections
        idle_count: Number of idle connections
        extra: Additional backend-specific information
    """

    active_count: Optional[int] = None
    max_connections: Optional[int] = None
    idle_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageInfo:
    """Storage-related status information.

    Attributes:
        total_size_bytes: Total database size in bytes
        data_size_bytes: Size of data files
        index_size_bytes: Size of index files
        log_size_bytes: Size of log files
        free_space_bytes: Free space available
        extra: Additional backend-specific information
    """

    total_size_bytes: Optional[int] = None
    data_size_bytes: Optional[int] = None
    index_size_bytes: Optional[int] = None
    log_size_bytes: Optional[int] = None
    free_space_bytes: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionInfo:
    """Current session/connection information.

    Attributes:
        user: Current session user name
        database: Current database name
        schema: Current schema name (PostgreSQL style)
        host: Client host address
        ssl_enabled: Whether SSL/TLS is enabled for this connection
        ssl_version: SSL/TLS version if enabled
        ssl_cipher: SSL cipher suite if enabled
        password_used: Whether password was used for authentication
        extra: Additional backend-specific information
    """

    user: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None
    host: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    ssl_version: Optional[str] = None
    ssl_cipher: Optional[str] = None
    password_used: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WALInfo:
    """Write-Ahead Logging information.

    Attributes:
        wal_level: WAL level (minimal, replica, logical)
        wal_size_bytes: Current WAL size in bytes
        wal_files: Number of WAL files
        checkpoint_count: Number of checkpoints
        checkpoint_time: Time of last checkpoint
        wal_write_rate: WAL write rate in bytes/second
        wal_segments: Current number of WAL segments
        extra: Additional backend-specific information
    """

    wal_level: Optional[str] = None
    wal_size_bytes: Optional[int] = None
    wal_files: Optional[int] = None
    checkpoint_count: Optional[int] = None
    checkpoint_time: Optional[str] = None
    wal_write_rate: Optional[float] = None
    wal_segments: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationInfo:
    """Replication status information.

    Attributes:
        is_primary: Whether this server is a primary/master
        is_standby: Whether this server is a standby/replica
        replication_slots: Number of replication slots
        active_replications: Number of active replication connections
        lag_bytes: Replication lag in bytes (for standby)
        streaming: Whether streaming replication is active
        extra: Additional backend-specific information
    """

    is_primary: Optional[bool] = None
    is_standby: Optional[bool] = None
    replication_slots: Optional[int] = None
    active_replications: Optional[int] = None
    lag_bytes: Optional[int] = None
    streaming: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchiveInfo:
    """Archive status information.

    Attributes:
        archive_mode: Archive mode (on, off, always)
        archive_command: Archive command
        archive_timeout: Archive timeout in seconds
        archived_count: Number of archived WAL files
        failed_count: Number of failed archive attempts
        last_archived: Time of last archive
        last_failed: Time of last failed archive
        extra: Additional backend-specific information
    """

    archive_mode: Optional[str] = None
    archive_command: Optional[str] = None
    archive_timeout: Optional[int] = None
    archived_count: Optional[int] = None
    failed_count: Optional[int] = None
    last_archived: Optional[str] = None
    last_failed: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityInfo:
    """Security-related status information.

    Attributes:
        ssl_enabled: Whether SSL is enabled
        ssl_cert_file: SSL certificate file path
        ssl_key_file: SSL key file path
        ssl_ca_file: SSL CA file path
        password_encryption: Password encryption method
        auth_method: Authentication method
        krb_enabled: Whether Kerberos is enabled
        row_security: Row-level security status
        extra: Additional backend-specific information
    """

    ssl_enabled: Optional[bool] = None
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    ssl_ca_file: Optional[str] = None
    password_encryption: Optional[str] = None
    auth_method: Optional[str] = None
    krb_enabled: Optional[bool] = None
    row_security: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtensionInfo:
    """Installed extension information.

    Attributes:
        name: Extension name
        version: Extension version
        schema: Schema where extension is installed
        description: Extension description
        extra: Additional backend-specific information
    """

    name: str
    version: Optional[str] = None
    schema: Optional[str] = None
    description: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerOverview:
    """Complete server status overview.

    This is the top-level data structure returned by status introspectors,
    containing all status information organized by category.

    Attributes:
        server_version: Server version string
        server_vendor: Server vendor name (e.g., "SQLite", "MySQL", "PostgreSQL")
        server_name: Server name/identifier
        session: Current session/connection information
        configuration: List of configuration parameters
        performance: List of performance metrics
        connections: Connection information
        storage: Storage information
        databases: List of databases/schemas
        users: List of users/roles
        wal: WAL information (PostgreSQL specific)
        replication: Replication information (PostgreSQL specific)
        archive: Archive information (PostgreSQL specific)
        security: Security information
        extensions: List of installed extensions (PostgreSQL specific)
        extra: Additional backend-specific information
    """

    server_version: str
    server_vendor: str
    server_name: Optional[str] = None
    session: Optional[SessionInfo] = None
    configuration: List[StatusItem] = field(default_factory=list)
    performance: List[StatusItem] = field(default_factory=list)
    connections: ConnectionInfo = field(default_factory=ConnectionInfo)
    storage: StorageInfo = field(default_factory=StorageInfo)
    databases: List[DatabaseBriefInfo] = field(default_factory=list)
    users: List[UserInfo] = field(default_factory=list)
    wal: Optional[WALInfo] = None
    replication: Optional[ReplicationInfo] = None
    archive: Optional[ArchiveInfo] = None
    security: Optional[SecurityInfo] = None
    extensions: List[ExtensionInfo] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def get_items_by_category(self, category: StatusCategory) -> List[StatusItem]:
        """Get all status items in a specific category.

        Args:
            category: The category to filter by

        Returns:
            List of StatusItem objects in the specified category
        """
        all_items = self.configuration + self.performance
        return [item for item in all_items if item.category == category]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation of the server overview
        """
        from dataclasses import asdict
        return {
            "server_version": self.server_version,
            "server_vendor": self.server_vendor,
            "server_name": self.server_name,
            "session": asdict(self.session) if self.session else None,
            "configuration": [
                {**asdict(item), "category": item.category.value}
                for item in self.configuration
            ],
            "performance": [
                {**asdict(item), "category": item.category.value}
                for item in self.performance
            ],
            "connections": asdict(self.connections),
            "storage": asdict(self.storage),
            "databases": [asdict(db) for db in self.databases],
            "users": [asdict(user) for user in self.users],
            "wal": asdict(self.wal) if self.wal else None,
            "replication": asdict(self.replication) if self.replication else None,
            "archive": asdict(self.archive) if self.archive else None,
            "security": asdict(self.security) if self.security else None,
            "extensions": [asdict(ext) for ext in self.extensions],
            "extra": self.extra,
        }
