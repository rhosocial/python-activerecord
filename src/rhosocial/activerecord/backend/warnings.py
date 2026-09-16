# src/rhosocial/activerecord/backend/warnings.py
"""
Custom warning classes for the backend module.
"""

import warnings


class IdentifierQuotingWarning(UserWarning):
    """Warning issued when an unquoted identifier is a reserved word.

    This warning is emitted when a user explicitly sets ``need_quote=False``
    for an identifier that is a reserved word in the target SQL dialect.
    The unquoted identifier may cause SQL syntax errors at runtime.
    """
    pass
