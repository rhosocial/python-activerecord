#!/usr/bin/env python3
"""
演示脚本:生成订单处理工作流的静态图和实例图。

运行方式:
    cd docs/examples/chapter_12_named_procedure
    PYTHONPATH=../../../src:. python3 diagram_demo.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# 导入工作流类
from order_workflow import OrderProcessingProcedure

# Try to import SQLite modules
try:
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.named_query import (
        ProcedureRunner, TransactionMode,
    )
    from rhosocial.activerecord.backend.named_query.resolver import resolve_named_query
    HAS_SQLITE = True
except ImportError as e:
    HAS_SQLITE = False
    print(f"[Warning] Cannot import SQLite module: {e}")
    print("Will only demonstrate static diagram features")


def setup_mock_backend():
    """创建模拟后端,用于演示实例图。"""
    if not HAS_SQLITE:
        return None

    # 创建内存数据库
    backend = SQLiteBackend(database=":memory:")
    conn = backend.connection

    # 创建表
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            status TEXT,
            amount REAL
        )
    """)
    conn.execute("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            available INTEGER,
            reserved INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            type TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            status TEXT,
            transaction_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE order_records (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            user_id INTEGER,
            amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 插入测试数据
    conn.execute("INSERT INTO orders (id, user_id, status, amount) VALUES (1, 100, 'pending', 99.99)")
    conn.execute("INSERT INTO inventory (id, order_id, available, reserved) VALUES (1, 1, 10, 0)")
    conn.execute("INSERT INTO payments (id, order_id, status, transaction_id) VALUES (1, 1, 'success', 'TXN123')")
    conn.commit()

    return backend


def create_mock_execute(backend):
    """创建模拟的 execute_query 回调。"""
    def execute_query(sql, params, stmt_type):
        class MockResult:
            def __init__(self, data, affected_rows):
                self.data = data
                self.affected_rows = affected_rows

        conn = backend.connection
        try:
            cursor = conn.execute(sql, params)
            if sql.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, row)) for row in rows] if columns else []
                return MockResult(data, len(data))
            else:
                conn.commit()
                return MockResult([], cursor.rowcount)
        except Exception as e:
            conn.rollback()
            return MockResult([], 0)

    return execute_query


def main():
    print("=" * 60)
    print("Order Processing Workflow - Static Diagram Demo")
    print("=" * 60)
    print()

    # Set default parameters
    OrderProcessingProcedure.order_id = 1
    OrderProcessingProcedure.user_id = 100
    OrderProcessingProcedure.amount = 99.99

    # Static flowchart
    print("【Flowchart Static Diagram】")
    print("-" * 40)
    flowchart = OrderProcessingProcedure.static_diagram("flowchart")
    print(flowchart)
    print()

    # Static sequence diagram
    print("【Sequence Static Diagram】")
    print("-" * 40)
    sequence = OrderProcessingProcedure.static_diagram("sequence")
    print(sequence)
    print()

    # Instance diagram (if SQLite is available)
    if HAS_SQLITE:
        print("=" * 60)
        print("Order Processing Workflow - Instance Diagram Demo")
        print("=" * 60)
        print()

        backend = setup_mock_backend()
        dialect = backend.dialect
        execute_query = create_mock_execute(backend)

        # Use ProcedureRunner to execute the procedure
        runner = ProcedureRunner(
            "order_workflow.OrderProcessingProcedure"
        )

        # Use the imported class directly
        runner._procedure_class = OrderProcessingProcedure
        runner._params_info = OrderProcessingProcedure.get_parameters()

        result = runner.run(
            dialect,
            user_params={
                "order_id": 1,
                "user_id": 100,
                "amount": 99.99,
            },
            transaction_mode=TransactionMode.AUTO,
            backend=backend,
            execute_query=execute_query,
        )

        print(f"Execution result: success={result.success}, aborted={result.aborted}")
        if result.aborted:
            print(f"Abort reason: {result.abort_reason}")
        print()

        # Instance flowchart
        print("【Flowchart Instance Diagram】")
        print("-" * 40)
        instance_flowchart = result.diagram("flowchart", procedure_name="OrderProcessingProcedure")
        print(instance_flowchart)
        print()

        # Instance sequence diagram
        print("【Sequence Instance Diagram】")
        print("-" * 40)
        instance_sequence = result.diagram("sequence", procedure_name="OrderProcessingProcedure")
        print(instance_sequence)
        print()

        print("=" * 60)
        print("Notes:")
        print("- Instance diagram shows execution status (green=success, red=failure)")
        print("- Shows execution time for each step (milliseconds)")
        print("- Unexecuted steps shown in gray")
        print("- END node shows total steps and total time")
        print("=" * 60)
    else:
        print("=" * 60)
        print("Note: Install sqlite to demonstrate instance diagrams")
        print("pip install aiosqlite  # for async support")
        print("=" * 60)

    print()
    print("=" * 60)
    print("General Notes:")
    print("- Static diagrams are generated via dry-run, no DB connection needed")
    print("- Conditional branches execute during dry-run (because bindings have data)")
    print("- Parallel nodes use Mermaid & syntax (flowchart) or par/and blocks (sequence)")
    print("=" * 60)


if __name__ == "__main__":
    main()