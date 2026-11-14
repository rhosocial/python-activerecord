# tests/rhosocial/activerecord_test/feature/backend/sqlite/cli/test_cli_info.py
"""The ``info`` command's group tables describe what the command can render.

``PROTOCOL_FAMILY_GROUPS`` is the only statement of which protocols the family
overview prints and how they are grouped, and ``DIALECT_SPECIFIC_GROUPS`` marks
which of those groups are SQLite's own rather than the shared protocol families.
Neither is read anywhere else in the source, so the tables are worth exactly
what these assertions say about them:

* a group marked dialect-specific must be a group the family table actually
  carries, because ``_display_info_rich`` iterates the family table and consults
  the marker for each group it prints -- a marked name the table does not have
  never prints, so its label would be unearned rather than wrong;
* every protocol a group names must be one whose support the command can
  measure, because a class with no ``supports_*`` method is reported as zero of
  zero and rendered at 0%, which reads as "this backend does not support it"
  for a question nothing was ever asked.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.cli.info import (
    DIALECT_SPECIFIC_GROUPS,
    PROTOCOL_FAMILY_GROUPS,
    _get_protocol_support_methods,
)

pytestmark = [pytest.mark.feature]


def test_the_dialect_specific_groups_are_groups_the_family_table_carries():
    """A marked name the family table does not carry never prints at all."""
    unmarked = set(DIALECT_SPECIFIC_GROUPS) - set(PROTOCOL_FAMILY_GROUPS)
    assert not unmarked, (
        f"marked dialect-specific but not a group the info command prints: "
        f"{sorted(unmarked)}"
    )


@pytest.mark.parametrize("group", sorted(PROTOCOL_FAMILY_GROUPS))
def test_a_family_group_names_protocols_the_info_command_can_measure(group):
    """Every protocol in a group offers a support method to report on."""
    protocols = PROTOCOL_FAMILY_GROUPS[group]
    assert protocols, f"{group} is an empty group and prints an empty panel"
    for protocol in protocols:
        assert _get_protocol_support_methods(protocol), (
            f"{group}: {protocol.__name__} offers no supports_* method, so the "
            f"info command can report nothing about it"
        )
