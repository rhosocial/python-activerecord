# src/rhosocial/activerecord/backend/expression/types/network.py
"""Network address types — IPv4/IPv6 address, network (CIDR), MAC address."""

from __future__ import annotations

from ._base import DataType


class InetType(DataType):
    """INET — IPv4 / IPv6 host address.

    A *semantic* type rendered per backend: PostgreSQL ``INET``, MySQL /
    MariaDB / SQL Server ``VARBINARY(16)`` (INET6_ATON-compatible storage),
    Oracle / Firebird / SQLite as text.
    """


class CidrType(DataType):
    """CIDR — IPv4 / IPv6 network block with prefix length.

    A *semantic* type rendered per backend: PostgreSQL ``CIDR``, other
    backends as text (no native CIDR).
    """


class MacAddrType(DataType):
    """MAC — media access control address (EUI-48).

    A *semantic* type rendered per backend: PostgreSQL ``MACADDR``, MySQL /
    MariaDB / SQL Server ``BINARY(6)``, Oracle ``RAW(6)``, Firebird / SQLite
    as text.
    """