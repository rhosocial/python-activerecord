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
    PERFORMANCE = "performance"  # Performance metrics
    CONNECTION = "connection"  # Connection information
    STORAGE = "storage"  # Storage information
    SECURITY = "security"  # Security related
    REPLICATION = "replication"  # Replication related


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

    A simplified version of IntrospectionDatabaseInfo focused on status display.
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
class ProcessInfo:
    """Current running process/query information.

    Attributes:
        id: Process/thread ID
        user: User running the query
        host: Client host
        database: Database being accessed
        command: Command type (Query, Sleep, etc.)
        time: Time in current state
        state: Current state
        info: Query text or info
        extra: Additional backend-specific information
    """

    id: int
    user: Optional[str] = None
    host: Optional[str] = None
    database: Optional[str] = None
    command: Optional[str] = None
    time: Optional[int] = None
    state: Optional[str] = None
    info: Optional[str] = None
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
        processes: List of current running processes
        extensions: List of installed extensions
        extra: Additional backend-specific information

    **Engine-level facts live in subclasses, not here.** The slots that used
    to sit on this class -- ``wal``, ``replication``, ``archive``,
    ``security`` on PostgreSQL's side, ``innodb``, ``binary_log``,
    ``slow_query``, ``mysql_replication`` on MySQL's -- named families only
    one engine answers, which asserted on every other backend that it had
    something it does not have. They moved to their engines: an overview that
    answers those families is a subclass of this one carrying its own typed
    fields (``PostgreSQLServerOverview(ServerOverview)``,
    ``MySQLServerOverview(ServerOverview)``), and ``get_overview()`` keeps
    its core signature because the subclass is a legal covariant return.
    ``to_dict()`` iterates the instance's fields rather than naming them, so
    the subclass's facts serialize without being re-declared here.

    Facts that only one engine has are named typed fields on that engine's
    subclass -- ClickHouse's storage engines, Oracle's tablespaces, SQL
    Server's filegroups -- not ``extra`` entries: ``extra`` holds spellings
    that map onto a core member (``.claude/rules/introspection.md`` §2, §5),
    not a second family's fields.
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
    processes: List[ProcessInfo] = field(default_factory=list)
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

        Field-driven on purpose: a backend's overview is a subclass of this
        one carrying its own engine-level facts as typed fields, and this
        method serializes whatever fields the instance actually has, so the
        subclass's facts serialize without being re-declared here
        (``.claude/rules/introspection.md`` §5).

        Returns:
            Dictionary representation of the server overview
        """
        from dataclasses import asdict, fields, is_dataclass

        result: Dict[str, Any] = {}
        for item_field in fields(self):
            value = getattr(self, item_field.name)
            if item_field.name in ("configuration", "performance"):
                result[item_field.name] = [
                    {**asdict(item), "category": item.category.value} for item in value
                ]
            elif isinstance(value, list):
                result[item_field.name] = [
                    (
                        asdict(member)
                        if is_dataclass(member) and not isinstance(member, type)
                        else member
                    )
                    for member in value
                ]
            elif is_dataclass(value) and not isinstance(value, type):
                result[item_field.name] = asdict(value)
            else:
                result[item_field.name] = value
        return result
