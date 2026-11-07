"""
CRUD Insert operations: basic insert, batch insert, etc.
"""

#: The registry metadata the CRUD example packages share.
#:
#: ``delete``, ``insert`` and ``update`` are the same family -- the three
#: write operations over the same tables -- so they declare the same category
#: and the same priority. Writing it out three times would be three copies of
#: one decision with nothing keeping them in step: renumber the CRUD priority
#: in two of them and the third silently keeps the old one. Per
#: ``.claude/rules/constants.md`` a value read from more than one place, where
#: the readings must agree, takes a module-level constant and a test that pins
#: it -- see
#: ``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
#:
#: The ddl, query, transaction and types packages deliberately keep their own
#: tables: they are different families with their own categories and
#: priorities, and sharing the mechanism is not sharing the value.
META = {
    "category": "crud",
    "priority": 10,
}
