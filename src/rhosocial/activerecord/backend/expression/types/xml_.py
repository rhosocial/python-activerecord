# src/rhosocial/activerecord/backend/expression/types/xml_.py
"""XML — an XML document."""

from __future__ import annotations

from ._base import DataType


class XmlType(DataType):
    """XML — an XML document (SQL:2003 ``xml`` type).

    A *semantic* type: the value means "an XML document" on every backend that
    has one, while the storage is each backend's own choice. Backends that can
    render it implement ``format_data_type_xml``; the rest declare a substitute
    through ``suggested_data_types()`` — for most of them ``TextType``, which
    is not a compromise but an accurate description of what they store.

    Not to be confused with :class:`~...types.json_.JsonType`. Both are
    semi-structured, but the operations differ (XPath plus schema validation
    against JSON path plus none), the standards differ (SQL/XML against
    SQL/JSON), and the backends that have one do not reliably have the other.

    Deliberately **not** a subclass of :class:`~...types.string.TextType`,
    even though several backends store XML as text: SQL Server's ``xml`` is
    stored "as large binary objects (BLOBs)" and Oracle's ``XMLType`` is an
    Oracle-supplied type whose storage model — ``CLOB``, binary XML, or
    object-relational — is chosen per column, so "it is text" is false where it
    matters most. See :class:`~...types.uuid_.UUIDType` for the same argument
    applied to UUID.

    Carries no parameters: an associated XML Schema is a column or domain
    attribute, not part of the type's identity.

    Storage by backend, for reference when reading a DDL diff:

    ==============  ==========================
    Backend         Storage
    ==============  ==========================
    PostgreSQL      ``XML`` — native; it checks input for well-formedness,
                     but it "does not validate input values against a
                     document type declaration (DTD)" and there is "no
                     built-in support for validating against other XML schema
                     languages such as XML Schema"
    Oracle          ``XMLType`` — an Oracle-supplied type: "you can choose to
                     store the XML data in a ``CLOB`` column, as binary XML
                     (stored internally as a ``BLOB``), or object
                     relationally", and "queries and DML on ``XMLType``
                     columns operate the same regardless of the storage
                     mechanism"
    SQL Server      ``xml`` — "stored in xml type columns as large binary
                     objects (BLOBs)"; what that representation preserves is
                     the XML InfoSet
    MySQL           ``TEXT`` — no XML type; the chapter's list of categories
                     is numeric, date and time, string, spatial and JSON
    MariaDB         **native ``XMLTYPE``, available from 12.3** — "basic XML
                     storage capabilities only, without validation", capped at
                     4GB like ``LONGBLOB``, and "length cannot be specified".
                     The dialect renders ``XMLTYPE`` from 12.3 (the first GA of
                     that series was 12.3.2) and substitutes ``TEXT`` below it.
                     Note the bare word ``XML`` is not MariaDB's keyword on any
                     version
    SQLite          ``TEXT`` — no native type; XML gets TEXT affinity
    Snowflake       ``OBJECT`` (via ``suggested_data_types``) — ``PARSE_XML()``
                     returns ``OBJECT``, which is Snowflake's name for a
                     ``VARIANT``; there is no XML type
    BigQuery        ``STRING`` — no XML type; its type list is closed and
                     documented, and ``STRING`` is the only character type
                     in it
    ClickHouse      ``String`` — the manual enumerates ClickHouse's data types
                     exhaustively and XML is not among them; nothing is
                     rendered, the declared substitute is the byte-string type
    Firebird        ``BLOB SUB_TYPE TEXT`` — Firebird's ``TEXT`` is an alias
                     for BLOB subtype 1, "a specialized subtype used to store
                     plain text data that is too large to fit into a string
                     type", not a ``VARCHAR``-sized string type
    ==============  ==========================

    This is a *documentation* table, not a contract: a backend whose entry is
    missing has not implemented the type. Every row was taken from that
    backend's own documentation, and a row that is wrong here is a defect here
    — not a licence for the backend to differ.

    Vendor documentation, checked row by row:

    * PostgreSQL — https://www.postgresql.org/docs/current/datatype-xml.html
    * Oracle — XML Types section:
      https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Data-Types.html
    * SQL Server —
      https://learn.microsoft.com/en-us/sql/t-sql/xml/xml-transact-sql
      https://learn.microsoft.com/en-us/sql/relational-databases/xml/xml-indexes-sql-server
    * MySQL — https://dev.mysql.com/doc/refman/8.4/en/data-types.html
    * MariaDB —
      https://mariadb.com/docs/server/reference/data-types/string-data-types/xmltype
    * SQLite — https://www.sqlite.org/datatype3.html
    * Snowflake — the type list, which has no XML entry, and the function that
      defines what XML is stored as:
      https://docs.snowflake.com/en/sql-reference/intro-summary-data-types
      https://docs.snowflake.com/en/sql-reference/functions/parse_xml
    * BigQuery —
      https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types
    * ClickHouse — https://clickhouse.com/docs/en/sql-reference/data-types
    * Firebird —
      https://www.firebirdsql.org/file/documentation/chunk/en/refdocs/fblangref50/fblangref50-datatypes-bnrytypes.html

    Kept separate from :class:`~...types.custom.CustomType`, which is what
    ``parse_type()`` yields for a name the framework does not recognise:
    ``XmlType`` is a modelled concept, ``CustomType`` is honest ignorance.
    """

    name = "xml"

    def __init__(self, dialect=None):
        super().__init__(dialect)
