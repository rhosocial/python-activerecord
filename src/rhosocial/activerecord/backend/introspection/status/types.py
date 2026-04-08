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
class InnoDBInfo:
    """InnoDB storage engine information (MySQL specific).

    Attributes:
        buffer_pool_size: Buffer pool size in bytes
        buffer_pool_instances: Number of buffer pool instances
        buffer_pool_pages_total: Total pages in buffer pool
        buffer_pool_pages_data: Data pages in buffer pool
        buffer_pool_pages_dirty: Dirty pages in buffer pool
        buffer_pool_pages_free: Free pages in buffer pool
        buffer_pool_read_requests: Number of read requests
        buffer_pool_reads: Number of reads from disk
        buffer_pool_wait_free: Number of times had to wait for free page
        log_waits: Number of log waits
        log_write_requests: Number of log write requests
        log_writes: Number of log writes
        os_file_reads: Number of OS file reads
        os_file_writes: Number of OS file writes
        os_fsyncs: Number of OS fsyncs
        row_lock_current_waits: Current row lock waits
        row_lock_time: Total row lock time in ms
        row_lock_time_avg: Average row lock time in ms
        row_lock_waits: Number of row lock waits
        rows_read: Rows read
        rows_inserted: Rows inserted
        rows_updated: Rows updated
        rows_deleted: Rows deleted
        data_reads: Data reads
        data_writes: Data writes
        data_read: Data read in bytes
        data_written: Data written in bytes
        extra: Additional backend-specific information
    """

    buffer_pool_size: Optional[int] = None
    buffer_pool_instances: Optional[int] = None
    buffer_pool_pages_total: Optional[int] = None
    buffer_pool_pages_data: Optional[int] = None
    buffer_pool_pages_dirty: Optional[int] = None
    buffer_pool_pages_free: Optional[int] = None
    buffer_pool_read_requests: Optional[int] = None
    buffer_pool_reads: Optional[int] = None
    buffer_pool_wait_free: Optional[int] = None
    log_waits: Optional[int] = None
    log_write_requests: Optional[int] = None
    log_writes: Optional[int] = None
    os_file_reads: Optional[int] = None
    os_file_writes: Optional[int] = None
    os_fsyncs: Optional[int] = None
    row_lock_current_waits: Optional[int] = None
    row_lock_time: Optional[int] = None
    row_lock_time_avg: Optional[float] = None
    row_lock_waits: Optional[int] = None
    rows_read: Optional[int] = None
    rows_inserted: Optional[int] = None
    rows_updated: Optional[int] = None
    rows_deleted: Optional[int] = None
    data_reads: Optional[int] = None
    data_writes: Optional[int] = None
    data_read: Optional[int] = None
    data_written: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BinaryLogInfo:
    """Binary log information (MySQL specific).

    Attributes:
        log_enabled: Whether binary logging is enabled
        log_format: Binary log format (ROW, STATEMENT, MIXED)
        log_files: List of binary log files
        current_log_file: Current binary log file name
        current_log_position: Current position in binary log
        log_size_bytes: Total size of binary logs
        gtid_mode: GTID mode (ON, OFF, ON_PERMISSIVE, OFF_PERMISSIVE)
        gtid_executed: Executed GTID set
        gtid_purged: Purged GTID set
        binlog_rows_query_log_events: Whether rows query log events are enabled
        binlog_checksum: Checksum algorithm used
        extra: Additional backend-specific information
    """

    log_enabled: Optional[bool] = None
    log_format: Optional[str] = None
    log_files: List[str] = field(default_factory=list)
    current_log_file: Optional[str] = None
    current_log_position: Optional[int] = None
    log_size_bytes: Optional[int] = None
    gtid_mode: Optional[str] = None
    gtid_executed: Optional[str] = None
    gtid_purged: Optional[str] = None
    binlog_rows_query_log_events: Optional[bool] = None
    binlog_checksum: Optional[str] = None
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
class SlowQueryInfo:
    """Slow query log configuration information (MySQL specific).

    Attributes:
        slow_query_log: Whether slow query log is enabled
        slow_query_log_file: Slow query log file path
        long_query_time: Threshold for slow queries in seconds
        log_queries_not_using_indexes: Whether to log queries not using indexes
        log_slow_admin_statements: Whether to log slow admin statements
        log_slow_slave_statements: Whether to log slow slave statements
        min_examined_row_limit: Minimum rows examined to be logged
        slow_queries_count: Number of slow queries recorded
        extra: Additional backend-specific information
    """

    slow_query_log: Optional[bool] = None
    slow_query_log_file: Optional[str] = None
    long_query_time: Optional[float] = None
    log_queries_not_using_indexes: Optional[bool] = None
    log_slow_admin_statements: Optional[bool] = None
    log_slow_slave_statements: Optional[bool] = None
    min_examined_row_limit: Optional[int] = None
    slow_queries_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationSlaveInfo:
    """MySQL slave replication status information.

    Attributes:
        master_host: Master host
        master_port: Master port
        master_user: Master user
        slave_io_running: Whether IO thread is running
        slave_sql_running: Whether SQL thread is running
        seconds_behind_master: Seconds behind master
        master_log_file: Current master log file
        read_master_log_pos: Position read from master log
        relay_master_log_file: Relay master log file
        slave_io_state: IO thread state
        last_io_errno: Last IO error number
        last_io_error: Last IO error message
        last_sql_errno: Last SQL error number
        last_sql_error: Last SQL error message
        relay_log_file: Current relay log file
        relay_log_pos: Position in relay log
        exec_master_log_pos: Executed position in master log
        extra: Additional backend-specific information
    """

    master_host: Optional[str] = None
    master_port: Optional[int] = None
    master_user: Optional[str] = None
    slave_io_running: Optional[str] = None
    slave_sql_running: Optional[str] = None
    seconds_behind_master: Optional[int] = None
    master_log_file: Optional[str] = None
    read_master_log_pos: Optional[int] = None
    relay_master_log_file: Optional[str] = None
    slave_io_state: Optional[str] = None
    last_io_errno: Optional[int] = None
    last_io_error: Optional[str] = None
    last_sql_errno: Optional[int] = None
    last_sql_error: Optional[str] = None
    relay_log_file: Optional[str] = None
    relay_log_pos: Optional[int] = None
    exec_master_log_pos: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationMasterInfo:
    """MySQL master replication status information.

    Attributes:
        binary_log_file: Current binary log file
        binary_log_position: Current binary log position
        binlog_do_db: Databases to replicate
        binlog_ignore_db: Databases to ignore
        gtid_executed: Executed GTID set
        gtid_purged: Purged GTID set
        extra: Additional backend-specific information
    """

    binary_log_file: Optional[str] = None
    binary_log_position: Optional[int] = None
    binlog_do_db: List[str] = field(default_factory=list)
    binlog_ignore_db: List[str] = field(default_factory=list)
    gtid_executed: Optional[str] = None
    gtid_purged: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MySQLReplicationInfo:
    """MySQL replication status information (combines master and slave info).

    Attributes:
        is_master: Whether this server is a master
        is_slave: Whether this server is a slave
        server_id: Server ID
        master_info: Master replication info (if this is a master)
        slave_info: Slave replication info (if this is a slave)
        extra: Additional backend-specific information
    """

    is_master: Optional[bool] = None
    is_slave: Optional[bool] = None
    server_id: Optional[int] = None
    master_info: Optional[ReplicationMasterInfo] = None
    slave_info: Optional[ReplicationSlaveInfo] = None
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
        innodb: InnoDB storage engine information (MySQL specific)
        binary_log: Binary log information (MySQL specific)
        processes: List of current running processes (MySQL specific)
        slow_query: Slow query log configuration (MySQL specific)
        mysql_replication: MySQL replication status (MySQL specific)
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
    innodb: Optional[InnoDBInfo] = None
    binary_log: Optional[BinaryLogInfo] = None
    processes: List[ProcessInfo] = field(default_factory=list)
    slow_query: Optional[SlowQueryInfo] = None
    mysql_replication: Optional[MySQLReplicationInfo] = None
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
            "innodb": asdict(self.innodb) if self.innodb else None,
            "binary_log": asdict(self.binary_log) if self.binary_log else None,
            "processes": [asdict(proc) for proc in self.processes],
            "slow_query": asdict(self.slow_query) if self.slow_query else None,
            "mysql_replication": asdict(self.mysql_replication) if self.mysql_replication else None,
            "extra": self.extra,
        }
