# src/rhosocial/activerecord/tests/providers/ddl_verify.py
"""
DDL 表达式 vs 现有 schema 文件验证工具

过渡期使用：编译 DDL 表达式并与现有的 .sql 文件对比，
暴露 dialect 实现缺口。
"""

import re
import os
from pathlib import Path
from typing import Callable, Optional, Tuple


def normalize_sql_for_comparison(sql: str, dialect_name: str = "sqlite") -> str:
    """归一化 SQL 供比较

    处理：移除注释、折叠空白、移除引号、剥离方言特定包装器
    """
    # 移除注释
    sql = re.sub(r'--.*?\n', '\n', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # 统一空白
    sql = re.sub(r'\s+', ' ', sql).strip().rstrip(';')

    # 去引号（所有方言的标识符引号）
    sql = sql.replace('"', '').replace('`', '')

    # 规范化括号周围的空白：(col → (col, col) → col)
    sql = re.sub(r'\(\s+', '(', sql)
    sql = re.sub(r'\s+\)', ')', sql)

    # 方言特定剥离
    if dialect_name == "mysql":
        sql = re.sub(r'\s+ENGINE=\S+', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+DEFAULT\s+CHARSET=\S+', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+COLLATE=\S+', '', sql, flags=re.IGNORECASE)

    # SQLite 布尔等价：DEFAULT FALSE/TRUE ↔ DEFAULT 0/1
    if dialect_name == "sqlite":
        sql = sql.replace(' DEFAULT FALSE', ' DEFAULT 0')
        sql = sql.replace(' DEFAULT TRUE', ' DEFAULT 1')

    # 统一关键词大写
    keywords = {
        'create', 'table', 'primary', 'key', 'not', 'null', 'default',
        'auto_increment', 'auto increment', 'unique', 'references', 'if',
        'exists', 'integer', 'text', 'real', 'blob', 'boolean', 'tinyint',
        'int', 'varchar', 'double', 'decimal', 'serial', 'timestamp',
        'bigint', 'smallint', 'char', 'date', 'time', 'with', 'time zone',
        'engine', 'charset', 'collate', 'innodb', 'utf8mb4', 'unicode_ci',
        'datetime',
    }
    result = []
    for t in sql.split():
        if t.lower() in keywords:
            result.append(t.upper())
        else:
            result.append(t)

    return ' '.join(result)


def schemas_equivalent(
    actual: str,
    expected: str,
    dialect_name: str = "sqlite",
    actual_params: Optional[Tuple] = None,
) -> bool:
    """判断两个 DDL 是否语义等价（归一化后字符串比较）

    Args:
        actual: DDL 表达式输出的 SQL
        expected: .sql 文件内容
        dialect_name: 方言名称
        actual_params: 表达式输出的参数元组，用于替换 DEFAULT ? 占位符
    """
    if actual_params:
        actual = _substitute_params(actual, actual_params)
    a = normalize_sql_for_comparison(actual, dialect_name)
    e = normalize_sql_for_comparison(expected, dialect_name)
    return a == e


def _substitute_params(sql: str, params: Tuple) -> str:
    """将 SQL 中的 ? 占位符替换为实际参数值"""
    import re
    result = []
    param_idx = 0
    for part in re.split(r'(\?)', sql):
        if part == '?' and param_idx < len(params):
            val = params[param_idx]
            param_idx += 1
            if isinstance(val, str):
                result.append(f"'{val}'")
            elif isinstance(val, bool):
                result.append('1' if val else '0')
            elif val is None:
                result.append('NULL')
            else:
                result.append(str(val))
        else:
            result.append(part)
    return ''.join(result)


def load_schema_file(path: Path) -> str:
    """加载现有的 .sql schema 文件"""
    return path.read_text(encoding="utf-8")


def verify_table(
    expr_fn: Callable,
    dialect,
    schema_path: Path,
    table_name: str,
    dialect_name: str = "sqlite",
) -> dict:
    """验证一个表的 DDL 表达式输出是否与 schema 文件匹配

    Returns:
        dict with keys: table_name, matches (bool), expected, actual, dialect
    """
    expected_sql = load_schema_file(schema_path)
    expr = expr_fn(dialect, table_name)
    actual_sql, actual_params = expr.to_sql()

    matches = schemas_equivalent(actual_sql, expected_sql, dialect_name, actual_params)

    return {
        "table": table_name,
        "dialect": dialect_name,
        "matches": matches,
        "expected": expected_sql.strip(),
        "actual": actual_sql,
        "actual_params": actual_params,
        "expected_norm": normalize_sql_for_comparison(expected_sql, dialect_name),
        "actual_norm": normalize_sql_for_comparison(
            _substitute_params(actual_sql, actual_params) if actual_params else actual_sql,
            dialect_name,
        ),
    }
