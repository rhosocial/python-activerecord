# src/rhosocial/activerecord/backend/impl/sqlite/mixins/function.py
"""
SQLite-specific Function implementation.

This module provides the SQLiteFunctionMixin class.
"""

from typing import Dict, Tuple


class SQLiteFunctionMixin:
    """SQLite function version support detection."""

    _SQLITE_FUNCTION_VERSIONS = {
        # The JSON1 functions have existed since SQLite 3.9.0 behind a
        # compile-time option, and only became core in 3.38.0 -- so a hard
        # version floor cannot express their availability: CI runs a 3.35.0
        # server where json_extract executes fine, which is how the wrong
        # 3.38.0 floor recorded here was disproved once the render-time gate
        # started enforcing it. Availability on an old build depends on how
        # SQLite was compiled, not on the version number, so these carry no
        # floor and the query surface answers "no constraint recorded".
        "json_extract": (None, None),
        "json_extract_text": (None, None),
        "json_build_object": (None, (0, 0, 0)),
        "json_array_elements": (None, (0, 0, 0)),
        "json_objectagg": (None, (0, 0, 0)),
        "json_arrayagg": (None, (0, 0, 0)),
        "json": (None, None),
        "json_array": (None, None),
        "json_object": (None, None),
        "json_type": (None, None),
        "json_valid": (None, None),
        "json_quote": (None, None),
        "json_remove": (None, None),
        "json_set": (None, None),
        "json_insert": (None, None),
        "json_replace": (None, None),
        "json_patch": (None, None),
        "json_array_length": (None, None),
        "json_array_unpack": (None, None),
        "json_object_pack": (None, None),
        "json_object_retrieve": (None, None),
        "json_object_length": (None, None),
        "json_object_keys": (None, None),
        "json_tree": (None, None),
        "json_each": (None, None),
        "json_array_insert": ((3, 53, 0), None),
        "jsonb_array_insert": ((3, 53, 0), None),
        "substr": (None, None),
        "instr": (None, None),
        "printf": (None, None),
        "unicode": (None, None),
        "hex": (None, None),
        "unhex": ((3, 45, 0), None),
        "soundex": (None, None),
        "group_concat": (None, None),
        "trim_sqlite": (None, None),
        "ltrim": (None, None),
        "rtrim": (None, None),
        "date_func": (None, None),
        "time_func": (None, None),
        "datetime_func": (None, None),
        "julianday": (None, None),
        "strftime_func": (None, None),
        "random_func": (None, None),
        "abs_sql": (None, None),
        "sign": ((3, 21, 0), None),
        "total": (None, None),
        "round_": (None, None),
        "pow": ((3, 35, 0), None),
        "power": ((3, 35, 0), None),
        "sqrt": ((3, 35, 0), None),
        "mod": ((3, 35, 0), None),
        "ceil": ((3, 35, 0), None),
        "floor": ((3, 35, 0), None),
        "trunc": ((3, 35, 0), None),
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        "zeroblob": (None, None),
        "randomblob": (None, None),
        "typeof": (None, None),
        "quote": (None, None),
        "last_insert_rowid": (None, None),
        "changes": (None, None),
        "iif": ((3, 32, 0), None),
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping."""
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.sqlite import functions as sqlite_functions

        expression_constructors = {
            "xmlagg", "xmlattributes", "xmlcomment", "xmlconcat", "xmlelement",
            "xmlexists", "xmlforest", "xmlparse", "xmlpi", "xmlquery",
            "xmlroot", "xmlserialize", "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
                result[func_name] = self._is_sqlite_function_supported(func_name)

        sqlite_funcs = getattr(sqlite_functions, "__all__", [])
        for func_name in sqlite_funcs:
            result[func_name] = self._is_sqlite_function_supported(func_name)

        return result

    def _is_sqlite_function_supported(self, func_name: str) -> bool:
        """Check if a SQLite-specific function is supported based on version."""
        version_range = self._SQLITE_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True

    #: The min column of ``_SQLITE_FUNCTION_VERSIONS``: the earliest SQLite
    #: that knows each gated function. One table, read two ways --
    #: ``supports_functions`` asks it, ``check_function_version`` enforces it,
    #: so a floor recorded here cannot be reported and ignored at once. A
    #: recorded *ceiling* is not a floor: it says the spelling does not exist
    #: on SQLite at all (``json_build_object`` and the other PostgreSQL names
    #: the table keeps for the query surface), which is a different question
    #: from being too old, and it stays with the query surface.
    #:
    #: Declared as data rather than as a ``function_version_floor`` override
    #: because ``SQLDialectBase`` precedes every mixin in the MRO: a method
    #: overriding the base here would be shadowed by it.
    function_version_floors = {
        func_name: floor
        for func_name, (floor, _ceiling) in _SQLITE_FUNCTION_VERSIONS.items()
        if floor is not None
    }

    # ------------------------------------------------------------------
    # Spellings SQLite writes differently, and the two operations it has to
    # emulate (measured 2026-10-09; see the operation-groups matrix).
    # ------------------------------------------------------------------

    def _pad_copies(self, count, pad):
        """``REPLACE(HEX(ZEROBLOB(count)), '00', pad)`` -- the pad, repeated.

        ``HEX(ZEROBLOB(n))`` is the hex text of *n* zero bytes, so it holds
        *n* two-character ``00`` pairs; replacing each pair with the pad leaves
        *n* copies of it. Used by both pad emulations.
        """
        from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

        return FunctionCall(
            self,
            "REPLACE",
            FunctionCall(self, "HEX", FunctionCall(self, "ZEROBLOB", count)),
            Literal(self, "00"),
            pad,
        )

    def format_repeat_expression(self, expr) -> Tuple[str, tuple]:
        """Emulate ``REPEAT``, which SQLite does not have.

        Each ``00`` pair in ``HEX(ZEROBLOB(count))`` is one copy slot, so
        replacing them with the string repeats it exactly *count* times --
        verified against REPEAT on PostgreSQL, MySQL, MariaDB and ClickHouse
        for 0, 1, 3 and a multi-character input. A negative count never
        reaches here: the factory settles it as the empty string first.
        """
        from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

        call = FunctionCall(
            self,
            "REPLACE",
            FunctionCall(self, "HEX", FunctionCall(self, "ZEROBLOB", expr.count)),
            Literal(self, "00"),
            expr.expr,
            alias=expr.alias,
        )
        return call.to_sql()

    def format_lpad_expression(self, expr) -> Tuple[str, tuple]:
        """Emulate ``LPAD``, which SQLite does not have.

        Two branches, because SQLite alone answers "already long enough" and
        "too short" with the same ``SUBSTR``: when the string is at least
        *length* long the result is its first *length* characters (truncation),
        and otherwise the padding is appended on the left and the last
        *length* characters are taken -- the padding is exactly *length* copies
        long, so the tail it contributes is the whole left-hand side.
        """
        from rhosocial.activerecord.backend.expression.advanced_functions import (
            CaseExpression,
        )
        from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal
        from rhosocial.activerecord.backend.expression.operators import (
            BinaryExpression,
            UnaryExpression,
        )
        from rhosocial.activerecord.backend.expression.predicates import (
            ComparisonPredicate,
        )

        length_call = FunctionCall(self, "LENGTH", expr.expr)
        truncate_branch = FunctionCall(
            self, "SUBSTR", expr.expr, Literal(self, 1), expr.length
        )
        padded = BinaryExpression(self, "||", self._pad_copies(expr.length, expr.pad), expr.expr)
        pad_branch = FunctionCall(
            self, "SUBSTR", padded, UnaryExpression(self, "-", expr.length)
        )
        case = CaseExpression(
            self,
            cases=[(ComparisonPredicate(self, "<=", expr.length, length_call), truncate_branch)],
            else_result=pad_branch,
            alias=expr.alias,
        )
        return case.to_sql()

    def format_rpad_expression(self, expr) -> Tuple[str, tuple]:
        """Emulate ``RPAD``, which SQLite does not have.

        One branch is enough: the padding is appended on the right and the
        first *length* characters are taken, which pads when short and
        truncates when long.
        """
        from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal
        from rhosocial.activerecord.backend.expression.operators import BinaryExpression

        padded = BinaryExpression(self, "||", expr.expr, self._pad_copies(expr.length, expr.pad))
        call = FunctionCall(
            self, "SUBSTR", padded, Literal(self, 1), expr.length, alias=expr.alias
        )
        return call.to_sql()

    #: Names SQLite spells differently. Each is a spelling difference and not a
    #: semantic one -- measured 2026-10-09 across the ten backends -- so it is
    #: made here rather than at the call site.
    _SQLITE_FUNCTION_NAMES = {
        "ASCII": "UNICODE",
        "STRPOS": "INSTR",
    }

    def format_function_call(self, expr) -> Tuple[str, tuple]:
        """Format a function call, renaming the ones SQLite spells otherwise.

        Renames are the first column; ``POSITION``, ``LEFT``, ``RIGHT`` and the
        two-argument ``LOG`` are argument-order differences and are rebuilt
        from the same operands. Everything else delegates to the shared
        formatter untouched.

        The one subtlety is ``RIGHT``: ``SUBSTR(x, LENGTH(x) - n + 1, n)``
        reads from the end when *n* exceeds the length -- it returns the tail
        instead of the whole string -- so the start is clamped with
        ``MAX(..., 1)``. Verified against MySQL, MariaDB, ClickHouse and
        BigQuery for n = 0, 1, len-1, len, len+1.
        """
        import copy

        from rhosocial.activerecord.backend.dialect.mixins.function import (
            FunctionCallMixin,
        )
        from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal
        from rhosocial.activerecord.backend.expression.operators import BinaryExpression

        name = expr.func_name.upper()
        translated = None
        if name in self._SQLITE_FUNCTION_NAMES and len(expr.args) >= 1:
            translated = copy.copy(expr)
            translated.func_name = self._SQLITE_FUNCTION_NAMES[name]
        elif name == "TRUNCATE" and len(expr.args) == 2:
            # SQLite's TRUNC takes one argument, so a precision cannot be
            # passed through: the value is scaled, truncated toward zero and
            # scaled back, which is exact for negatives too (truncation is
            # symmetric, unlike rounding).
            scale = FunctionCall(self, "POW", Literal(self, 10), expr.args[1])
            scaled = BinaryExpression(self, "*", expr.args[0], scale)
            return BinaryExpression(
                self, "/", FunctionCall(self, "TRUNC", scaled), scale
            ).to_sql()
        elif name == "TRUNCATE" and len(expr.args) == 1:
            translated = copy.copy(expr)
            translated.func_name = "TRUNC"
        elif name == "POSITION" and len(expr.args) == 2:
            # SQLite's INSTR takes the haystack first; the core POSITION spells
            # the needle first, which is the standard IN form.
            translated = copy.copy(expr)
            translated.func_name = "INSTR"
            translated.args = [expr.args[1], expr.args[0]]
        elif name == "LEFT" and len(expr.args) == 2:
            translated = copy.copy(expr)
            translated.func_name = "SUBSTR"
            translated.args = [expr.args[0], Literal(self, 1), expr.args[1]]
        elif name == "RIGHT" and len(expr.args) == 2:
            length_call = FunctionCall(self, "LENGTH", expr.args[0])
            start = BinaryExpression(
                self,
                "+",
                BinaryExpression(self, "-", length_call, expr.args[1]),
                Literal(self, 1),
            )
            translated = copy.copy(expr)
            translated.func_name = "SUBSTR"
            translated.args = [
                expr.args[0],
                FunctionCall(self, "MAX", start, Literal(self, 1)),
                expr.args[1],
            ]
        elif name == "LOG" and len(expr.args) == 2:
            translated = copy.copy(expr)
            translated.args = [expr.args[1], expr.args[0]]
        if translated is not None:
            return FunctionCallMixin.format_function_call(self, translated)
        return FunctionCallMixin.format_function_call(self, expr)

