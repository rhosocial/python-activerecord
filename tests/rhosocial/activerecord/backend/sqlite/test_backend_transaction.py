import os
import tempfile

import pytest

from src.rhosocial.activerecord.backend.errors import (
    IntegrityError
)
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from src.rhosocial.activerecord.backend.impl.sqlite.transaction import SQLiteTransactionManager
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


class TestSQLiteBackendTransaction:
    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库文件路径"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # 清理
        if os.path.exists(path):
            os.unlink(path)
        # 清理相关的 WAL 和 SHM 文件
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    @pytest.fixture
    def config(self, temp_db_path):
        """创建数据库配置"""
        return ConnectionConfig(database=temp_db_path)

    @pytest.fixture
    def backend(self, config):
        """创建 SQLite 后端"""
        backend = SQLiteBackend(connection_config=config)
        # 确保表存在
        backend.connect()
        backend.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
        return backend

    def test_transaction_property(self, backend):
        """测试事务管理器属性"""
        assert backend._transaction_manager is None

        # 访问属性应该创建事务管理器
        assert isinstance(backend.transaction_manager, SQLiteTransactionManager)
        assert backend._transaction_manager is not None

        # 再次访问应该返回相同实例
        assert backend.transaction_manager is backend._transaction_manager

    def test_begin_transaction(self, backend):
        """测试开始事务"""
        backend.begin_transaction()
        assert backend.in_transaction is True
        assert backend.transaction_manager.is_active is True

    def test_commit_transaction(self, backend):
        """测试提交事务"""
        backend.begin_transaction()

        # 插入数据
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'test commit')")

        # 提交事务
        backend.commit_transaction()
        assert backend.in_transaction is False

        # 验证数据已提交
        result = backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert result is not None
        assert result['id'] == 1
        assert result['value'] == 'test commit'

    def test_rollback_transaction(self, backend):
        """测试回滚事务"""
        backend.begin_transaction()

        # 插入数据
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'test rollback')")

        # 回滚事务
        backend.rollback_transaction()
        assert backend.in_transaction is False

        # 验证数据已回滚
        result = backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert result is None

    def test_transaction_context_manager(self, backend):
        """测试事务上下文管理器"""
        # 使用 with 语句进行事务管理
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (3, 'context manager')")

        # 验证事务已提交
        assert backend.in_transaction is False
        result = backend.fetch_one("SELECT * FROM test WHERE id = 3")
        assert result is not None
        assert result['id'] == 3
        assert result['value'] == 'context manager'

    def test_transaction_context_manager_exception(self, backend):
        """测试事务上下文管理器异常处理"""
        try:
            with backend.transaction():
                backend.execute("INSERT INTO test (id, value) VALUES (4, 'context exception')")
                raise ValueError("Test exception")
        except ValueError:
            pass

        # 验证事务已回滚
        assert backend.in_transaction is False
        result = backend.fetch_one("SELECT * FROM test WHERE id = 4")
        assert result is None

    def test_nested_transactions(self, backend):
        """测试嵌套事务"""
        # 开始外层事务
        backend.begin_transaction()

        # 插入数据
        backend.execute("INSERT INTO test (id, value) VALUES (5, 'outer')")

        # 开始内层事务
        backend.begin_transaction()

        # 插入更多数据
        backend.execute("INSERT INTO test (id, value) VALUES (6, 'inner')")

        # 回滚内层事务
        backend.rollback_transaction()

        # 验证内层事务回滚
        result = backend.fetch_one("SELECT * FROM test WHERE id = 6")
        assert result is None

        # 验证外层事务数据仍然存在
        result = backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result['value'] == 'outer'

        # 提交外层事务
        backend.commit_transaction()

        # 验证外层事务提交成功
        result = backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result['value'] == 'outer'

    def test_mixed_nested_transactions(self, backend):
        """测试混合嵌套事务（包含上下文管理器）"""
        # 开始外层事务
        backend.begin_transaction()

        # 插入数据
        backend.execute("INSERT INTO test (id, value) VALUES (7, 'outer mixed')")

        # 使用上下文管理器开始内层事务
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (8, 'inner mixed')")

        # 验证内层事务提交成功
        result = backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8) ORDER BY id")
        assert len(result) == 2
        assert result[0]['value'] == 'outer mixed'
        assert result[1]['value'] == 'inner mixed'

        # 回滚外层事务
        backend.rollback_transaction()

        # 验证所有数据都被回滚
        result = backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8)")
        assert len(result) == 0

    def test_auto_transaction_on_insert(self, backend):
        """测试插入操作的自动事务处理"""
        # 使用 insert 方法
        result = backend.insert("test", {"id": 9, "value": "auto insert"})

        # 验证插入成功
        assert result.affected_rows == 1
        assert result.last_insert_id == 9

        # 验证数据存在
        row = backend.fetch_one("SELECT * FROM test WHERE id = 9")
        assert row is not None
        assert row['value'] == 'auto insert'

    def test_auto_transaction_on_update(self, backend):
        """测试更新操作的自动事务处理"""
        # 先插入数据
        backend.insert("test", {"id": 10, "value": "before update"})

        # 使用 update 方法
        result = backend.update("test", {"value": "after update"}, "id = ?", (10,))

        # 验证更新成功
        assert result.affected_rows == 1

        # 验证数据已更新
        row = backend.fetch_one("SELECT * FROM test WHERE id = 10")
        assert row is not None
        assert row['value'] == 'after update'

    def test_auto_transaction_on_delete(self, backend):
        """测试删除操作的自动事务处理"""
        # 先插入数据
        backend.insert("test", {"id": 11, "value": "to be deleted"})

        # 验证数据已插入
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is not None

        # 使用 delete 方法
        result = backend.delete("test", "id = ?", (11,))

        # 验证删除成功
        assert result.affected_rows == 1

        # 验证数据已删除
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is None

    def test_transaction_with_integrity_error(self, backend):
        """测试事务中的完整性错误"""
        # 先插入数据
        backend.insert("test", {"id": 12, "value": "unique"})

        # 开始事务
        backend.begin_transaction()

        # 插入一些数据
        backend.execute("INSERT INTO test (id, value) VALUES (13, 'before error')")

        # 尝试插入重复数据，应该失败
        with pytest.raises(IntegrityError):
            backend.execute("INSERT INTO test (id, value) VALUES (12, 'duplicate')")

        # 回滚事务
        backend.rollback_transaction()

        # 验证事务内的所有操作都被回滚
        row = backend.fetch_one("SELECT * FROM test WHERE id = 13")
        assert row is None

    def test_connection_context_manager(self, backend):
        """测试连接上下文管理器"""
        # 使用 with 语句进行连接管理
        with backend as conn:
            # 在上下文中使用连接
            conn.execute("INSERT INTO test (id, value) VALUES (14, 'connection context')")

        # 验证操作成功
        row = backend.fetch_one("SELECT * FROM test WHERE id = 14")
        assert row is not None
        assert row['value'] == 'connection context'

    def test_disconnect_during_transaction(self, backend):
        """测试事务期间断开连接"""
        # 开始事务
        backend.begin_transaction()

        # 插入数据
        backend.execute("INSERT INTO test (id, value) VALUES (15, 'disconnect test')")

        # 断开连接
        backend.disconnect()

        # 验证事务状态被重置
        assert backend._transaction_manager is None
        assert backend._connection is None
        assert backend.in_transaction is False

        # 重新连接并验证数据被回滚
        backend.connect()
        row = backend.fetch_one("SELECT * FROM test WHERE id = 15")
        assert row is None

    def test_delete_on_close(self, temp_db_path):
        """测试关闭时删除数据库文件"""
        # 创建带有 delete_on_close 的后端
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config, delete_on_close=True)

        # 连接并创建表
        backend.connect()
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'temp data')")

        # 验证文件存在
        assert os.path.exists(temp_db_path)

        # 断开连接，应该删除文件
        backend.disconnect()

        # 验证文件已删除
        assert not os.path.exists(temp_db_path)
        assert not os.path.exists(temp_db_path + "-wal")
        assert not os.path.exists(temp_db_path + "-shm")