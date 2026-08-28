#!/usr/bin/env python3
"""PyPy 兼容性实验脚本 — 不修改源代码，仅通过独立脚本验证假设。"""
# 实验路径：/mnt/i/GitHubRepositories/rhosocial/python-activerecord/experiments/pypy_compat_experiment.py

import sys
import sqlite3
from decimal import Decimal

# 假设 1：PyPy 下 Decimal 序列化与 CPython 差异
print("=" * 60)
print("假设 1：Decimal + Pydantic 在 PyPy 下的序列化行为")
print("=" * 60)

try:
    import pydantic
    print(f"pydantic 版本: {pydantic.__version__}")
    print(f"sys.implementation: {sys.implementation.name}")

    class M(pydantic.BaseModel):
        balance: Decimal

    m = M(balance=Decimal("1500.00"))
    print(f"实例化成功: balance={m.balance}, type={type(m.balance)}")

    # 尝试序列化
    try:
        serialized = m.model_dump()
        print(f"model_dump() 结果: {serialized}")
        print(f"序列化类型: {type(serialized.get('balance'))}")
    except Exception as e:
        print(f"model_dump() 失败: {type(e).__name__}: {e}")

    # 尝试 JSON 模式序列化
    try:
        json_str = m.model_dump_json()
        print(f"model_dump_json() 成功: {json_str[:200]}...")
    except Exception as e:
        print(f"model_dump_json() 失败: {type(e).__name__}: {e}")

except Exception as e:
    print(f"Pydantic 导入/测试失败: {type(e).__name__}: {e}")


# 假设 2：PyPy sqlite3（基于 apsw）的 RETURNING + 游标状态差异
print()
print("=" * 60)
print("假设 2：sqlite3 RETURNING 语句后的游标状态与事务提交")
print("=" * 60)

# 在 CPython 下使用内置 sqlite3 测试；在 PyPy 下同样使用 sqlite3 模块（由 apsw 提供）
# 测试核心：执行 INSERT ... RETURNING 后，游标是否仍处于 "SQL statements in progress" 状态

try:
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()

    # 执行带 RETURNING 的 INSERT
    cursor.execute('INSERT INTO users (name) VALUES (?) RETURNING id, name', ("alice",))
    row = cursor.fetchone()
    print(f"RETURNING 结果: {row}")

    # 检查游标状态：是否还有未读取的数据？
    # 在 CPython 下，RETURNING 语句的游标通常在 fetchone() 后仍可关闭
    # 在 PyPy 下，可能游标没有被完全消费，导致后续 COMMIT 失败
    try:
        extra = cursor.fetchall()
        print(f"fetchall() 额外结果数: {len(extra)}")
    except Exception as e:
        print(f"fetchall() 异常（可能正常）: {e}")

    # 关键实验：在游标未显式关闭时直接 COMMIT
    # 在 CPython 下通常可以成功；在 PyPy 下可能失败
    print(f"游标关闭前连接状态: in_transaction={conn.in_transaction}")

    # 不显式关闭游标，直接提交
    try:
        conn.commit()
        print("直接 COMMIT 成功（游标未关闭）")
    except sqlite3.OperationalError as e:
        print(f"直接 COMMIT 失败（游标未关闭）: {e}")
        # 关闭游标后再试
        cursor.close()
        conn.commit()
        print("关闭游标后 COMMIT 成功")

    # 测试使用 RETURNING 时游标是否被完全消费
    cursor2 = conn.cursor()
    cursor2.execute('INSERT INTO users (name) VALUES (?) RETURNING id, name', ("bob",))
    print(f"第二次 RETURNING 结果: {cursor2.fetchone()}")
    # 检查是否还有剩余行
    remaining = cursor2.fetchall()
    print(f"第二次 fetchall() 剩余行数: {len(remaining)}")
    cursor2.close()

    conn.close()
    print("sqlite3 实验完成（无异常）")

except Exception as e:
    print(f"sqlite3 实验异常: {type(e).__name__}: {e}")


# 假设 3：PyPy 下 sqlite3 模块实现差异（_sqlite3 vs apsw）
print()
print("=" * 60)
print("假设 3：sqlite3 模块实现来源与 load_extension 差异")
print("=" * 60)

try:
    import sqlite3
    # 检查 sqlite3 是否来自内置模块
    print(f"sqlite3 模块文件: {sqlite3.__file__ if hasattr(sqlite3, '__file__') else 'built-in'}")

    conn = sqlite3.connect(":memory:")
    # 测试 load_extension 可用性（PyPy 的 apsw 可能不支持）
    try:
        conn.enable_load_extension(True)
        # load_extension 需要实际扩展文件，这里只测试启用状态
        print("enable_load_extension(True) 成功")
    except Exception as e:
        print(f"enable_load_extension(True) 失败: {type(e).__name__}: {e}")

    conn.close()
except Exception as e:
    print(f"sqlite3 模块差异测试失败: {type(e).__name__}: {e}")


# 假设 4：Decimal 在 SQL 参数绑定时的类型差异
print()
print("=" * 60)
print("假设 4：Decimal 参数绑定在 PyPy sqlite3 中的表现")
print("=" * 60)

try:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE items (price NUMERIC)")
    conn.execute("INSERT INTO items (price) VALUES (?)", (Decimal("10.00"),))
    cursor = conn.execute("SELECT price FROM items")
    row = cursor.fetchone()
    print(f"插入 Decimal('10.00') 后读取: {row}, 类型: {type(row[0]) if row else None}")
    conn.close()
except Exception as e:
    print(f"Decimal 绑定实验失败: {type(e).__name__}: {e}")


# 总结
print()
print("=" * 60)
print("实验脚本执行完毕（无源代码修改）")
print(f"运行环境: {sys.version}")
print("=" * 60)
