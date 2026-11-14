# tests/rhosocial/activerecord_test/feature/backend/sqlite/cli/test_cli_status.py
"""The ``status`` subcommand's type names are the ones its handler answers.

``STATUS_TYPES`` is the single statement of which status kinds the command
accepts, and it is read once -- as the argument's ``choices``. That makes the
list the whole contract, in both directions:

* a name the table lists and argparse refuses is a name nobody can ask for, so
  the table would be advertising something the command does not do;
* a name the table lists that the status introspector cannot answer is a command
  that accepts an argument and then does nothing.

The networked status kinds are deliberately absent, and that is the other half
of the contract: SQLite has no server, so ``connections`` and ``users`` -- which
every other backend's list carries -- are not offered here at all.
"""

import argparse

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.cli.status import (
    STATUS_TYPES,
    create_parser,
)

pytestmark = [pytest.mark.feature]

#: What each accepted type asks the status introspector for. Written out here
#: rather than read from ``handle``, because a name the command accepts and no
#: branch answers should fail this test rather than do nothing silently.
_ANSWERED_BY = {
    "all": "get_overview",
    "config": "list_configuration",
    "performance": "list_configuration",
    "storage": "get_storage_info",
    "databases": "list_databases",
}


def _status_parser():
    """The ``status`` subcommand's parser, built the way the CLI builds it."""
    parser = argparse.ArgumentParser(prog="activerecord")
    subparsers = parser.add_subparsers()
    create_parser(subparsers)
    return parser


def _status_introspector():
    """A memory-backed status introspector; SQLite answers from the library."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    return backend.introspector.status


@pytest.mark.parametrize("status_type", STATUS_TYPES)
def test_every_type_the_table_names_is_one_the_parser_accepts(status_type):
    """A name argparse refuses is a name the command advertises but cannot take."""
    parsed = _status_parser().parse_args(["status", status_type])
    assert parsed.type == status_type


def test_a_type_the_table_does_not_name_is_refused():
    """``tablespaces`` is a real status kind -- on a backend that has them.

    SQLite does not, so the argument must be refused rather than accepted and
    ignored.
    """
    with pytest.raises(SystemExit):
        _status_parser().parse_args(["status", "tablespaces"])


def test_the_types_the_table_names_are_all_questions_the_introspector_answers():
    """The accepted names and the answerable questions are the same set."""
    introspector = _status_introspector()
    assert set(STATUS_TYPES) == set(_ANSWERED_BY), (
        f"the status subcommand accepts {sorted(STATUS_TYPES)} and this test "
        f"expects {sorted(_ANSWERED_BY)}"
    )
    for status_type, method_name in _ANSWERED_BY.items():
        method = getattr(introspector, method_name, None)
        assert callable(method), (
            f"{status_type}: the status introspector has no {method_name} to "
            f"answer it with"
        )


def test_the_networked_status_kinds_stay_unoffered():
    """SQLite is a library, so the kinds that need a server are not accepted.

    The other backends' lists carry ``connections`` and ``users``. Offering them
    here would accept an argument this backend can only answer with an empty
    list.
    """
    assert "connections" not in STATUS_TYPES
    assert "users" not in STATUS_TYPES
