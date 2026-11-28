# src/rhosocial/activerecord/backend/expression/functions/__init__.py
"""Standalone factory functions for creating SQL expression objects.

Usage Rules:
- For COUNT(*), pass "*" as a string: count(dialect, "*")
- For column references (e.g., COUNT(column), SUM(column)), pass Column objects:
  count(dialect, Column(dialect, "column_name"))
- For literal values (e.g., COUNT(?), SUM(?)), pass literal values as strings:
  count(dialect, "literal_value")
- For scalar functions (e.g., lower, upper), string arguments are treated as literal values by default
- For functions that operate on columns, wrap column names in Column objects"""

__all__ = [
    'AggregateFunction',
    'CountFunction',
    'SumFunction',
    'AvgFunction',
    'MinFunction',
    'MaxFunction',
    'count',
    'sum_',
    'avg',
    'min_',
    'max_',
    'UpperFunction',
    'LowerFunction',
    'CharLengthFunction',
    'concat',
    'coalesce',
    'length',
    'substring',
    'trim',
    'replace',
    'upper',
    'lower',
    'initcap',
    'left',
    'right',
    'lpad',
    'rpad',
    'reverse',
    'strpos',
    'concat_op',
    'chr_',
    'ascii',
    'octet_length',
    'bit_length',
    'position',
    'overlay',
    'translate',
    'repeat',
    'space',
    'abs_',
    'round_',
    'ceil',
    'floor',
    'sqrt',
    'power',
    'exp',
    'log',
    'sin',
    'cos',
    'tan',
    'mod',
    'sign',
    'truncate',
    'now',
    'current_date',
    'current_time',
    'year',
    'month',
    'day',
    'hour',
    'minute',
    'second',
    'date_part',
    'date_trunc',
    'interval',
    'date_add',
    'date_sub',
    'date_diff',
    'seconds_between',
    'current_timestamp',
    'localtimestamp',
    'extract',
    'case',
    'nullif',
    'greatest',
    'least',
    'row_number',
    'rank',
    'dense_rank',
    'lag',
    'lead',
    'first_value',
    'last_value',
    'nth_value',
    'json_extract',
    'json_extract_text',
    'json_build_object',
    'json_array_elements',
    'json_objectagg',
    'json_arrayagg',
    'array_agg',
    'unnest',
    'array_length',
    'cast',
    'to_char',
    'to_number',
    'to_date',
    'grouping_sets',
    'rollup',
    'cube',
    'current_user',
    'session_user',
    'system_user',
    'passing_clause',
    'xmlagg',
    'xmlattributes',
    'xmlcomment',
    'xmlconcat',
    'xmlelement',
    'xmlexists',
    'xmlforest',
    'xmlparse',
    'xmlpi',
    'xmlquery',
    'xmlroot',
    'xmlserialize',
    'xmltable',
]

import importlib

_MODULES = ('advanced_functions', 'aggregate', 'array', 'cast_expression', 'collation', 'conditional', 'datetime', 'function_call', 'grouping', 'json', 'math', 'string', 'system', 'type_conversion', 'uuid', 'window', 'xml')


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value  # cache so vars()/inspect see the name
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
