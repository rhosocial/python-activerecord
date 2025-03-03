"""Python ActiveRecord implementation using Pydantic"""

"""
Main entry point for ActiveRecord functionality.

Provides a unified ActiveRecord implementation that combines:
- Basic CRUD operations
- Relational model support
- Query building
- Aggregate queries
- Field type support
"""

__version__ = "1.0.0.dev5"

# ### **Version Format**
# The version string MUST follow the [PEP 440](https://packaging.python.org/en/latest/specifications/version-specifiers/) standard.
# The full format is:
# `[EPOCH!]RELEASE[-PRE][.postPOST][.devDEV][+LOCAL]`
#
# #### **Components**
# 1. **Epoch (Optional)**
#    - Format: `[N!]` (e.g., `2!1.0.0`).
#    - Purpose: Resets version numbering for major compatibility breaks. Defaults to `0!` if omitted.
#
# 2. **Release Segments**
#    - Format: `N(.N)*` (e.g., `1`, `1.2`, `1.2.3`).
#    - Rules:
#      - At least one numeric segment.
#      - Major version increments (e.g., `1.0.0` → `2.0.0`) indicate **incompatible API changes** (recommended ≤1/year).
#
# 3. **Pre-release (Optional)**
#    - Format: `[-._]{a|alpha|b|beta|rc|pre|preview}[N]`
#      - Short aliases: `a` = alpha, `b` = beta, `rc` = release candidate.
#    - Examples:
#      - `1.0a1` (Alpha release 1)
#      - `1.0-beta.2` (Beta release 2)
#      - `1.0.0-rc.3` (Release candidate 3)
#
# 4. **Post-release (Optional)**
#    - Format: `.postN` (e.g., `1.0.0.post1`).
#    - Purpose: Denotes bug fixes without altering the main release.
#
# 5. **Dev-release (Optional)**
#    - Format: `.devN` (e.g., `1.0.0.dev2`).
#    - Purpose: Marks in-development versions (e.g., `1.0.0-dev` → `1.0.0.dev0` under PEP 440).
#
# 6. **Local Version (Optional)**
#    - Format: `+[alphanum][._-alphanum]*` (e.g., `+local`, `+test.2023`).
#    - Purpose: Identifies unofficial builds (ignored in version comparisons).
#
# ---
#
# ### **Examples**
# ```python
# __version__ = "1.0.0"                # Final release
# __version__ = "2!1.0.0a1"            # Epoch + Alpha
# __version__ = "1.0.0-beta.2.post3"   # Beta with post-release
# __version__ = "1.0.0.dev4+local.1"   # Dev version + local build
# ```
#
# ---
#
# ### **Key Changes from Original Format**
# - **Deprecated:** Standalone `-dev` → Use `.devN` (PEP 440 compliance).
# - **Added:** Support for epoch (`N!`), post-release (`.postN`), and local versions (`+...`).
# - **Extended Pre-release:** Added short aliases (`a`, `b`, `rc`) and flexible separators (`-`, `.`, `_`).
#
# This format ensures compatibility with Python packaging tools (e.g., `pip`, `setuptools`)
# while maintaining backward compatibility with your original semantic versioning rules.


from .base import BaseActiveRecord, QueryMixin
from .relation import RelationManagementMixin


class ActiveRecord(
    RelationManagementMixin,
    # FieldMixin,  # import when needed
    QueryMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features.

    Inherits functionality from:

    - BaseActiveRecord: Core CRUD operations
    - RelationalModelMixin: Relationship handling
    - QueryMixin: Query builder
    """
    ...


__all__ = [
    'ActiveRecord',
]