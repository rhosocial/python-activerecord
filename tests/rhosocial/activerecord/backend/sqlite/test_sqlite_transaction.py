import logging
import sqlite3
from unittest.mock import MagicMock, patch, call

import pytest

from src.rhosocial.activerecord.backend.errors import TransactionError
from src.rhosocial.activerecord.backend.impl.sqlite.transaction import SQLiteTransactionManager
from src.rhosocial.activerecord.backend.transaction import IsolationLevel


class TestSQLiteTransactionManager:
    @pytest.fixture
    def connection(self):
        """创建内存 SQLite 连接"""
        conn = sqlite3.connect(":memory:")
        # 设置自动提交，与实际实现保持一致
        conn.isolation_level = None
        # 创建测试表
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        return conn

    @pytest.fixture
    def logger(self):
        """创建测试用日志器"""
        logger = logging.getLogger("test_transaction")
        logger.setLevel(logging.DEBUG)
        return logger

    @pytest.fixture
    def transaction_manager(self, connection, logger):
        """创建事务管理器"""
        return SQLiteTransactionManager(connection, logger)

    def test_init(self, connection, logger):
        """测试初始化事务管理器"""
        manager = SQLiteTransactionManager(connection, logger)
        assert manager._connection == connection
        assert manager._connection.isolation_level is None
        assert manager.is_active is False
        assert manager._savepoint_count == 0
        assert manager._logger == logger
        assert manager._transaction_level == 0
        assert manager._isolation_level == IsolationLevel.SERIALIZABLE

    def test_init_without_logger(self, connection):
        """测试不提供日志器的初始化"""
        manager = SQLiteTransactionManager(connection)
        assert manager._logger is not None
        assert isinstance(manager._logger, logging.Logger)
        assert manager._logger.name == 'transaction'

    def test_logger_property(self, transaction_manager, logger):
        """测试日志器属性"""
        assert transaction_manager.logger == logger

        # 测试设置新的日志器
        new_logger = logging.getLogger("new_logger")
        transaction_manager.logger = new_logger
        assert transaction_manager.logger == new_logger

        # 测试设置为None时使用默认日志器
        transaction_manager.logger = None
        assert transaction_manager.logger is not None
        assert transaction_manager.logger.name == 'transaction'

        # 测试设置非日志器值
        with pytest.raises(ValueError):
            transaction_manager.logger = "not a logger"

    def test_log_method(self, transaction_manager):
        """测试日志记录方法"""
        with patch.object(transaction_manager._logger, 'log') as mock_log:
            transaction_manager.log(logging.INFO, "Test message")
            mock_log.assert_called_once_with(logging.INFO, "Test message")

            transaction_manager.log(logging.ERROR, "Error %s", "details", extra={'key': 'value'})
            mock_log.assert_called_with(logging.ERROR, "Error %s", "details", extra={'key': 'value'})

    def test_begin_transaction(self, transaction_manager):
        """测试开始事务"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            assert transaction_manager.is_active is True
            assert transaction_manager._transaction_level == 1

            # 验证日志记录
            assert mock_log.call_count >= 2
            mock_log.assert_any_call(logging.DEBUG, "Beginning transaction (level 0)")
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")

            # 验证事务真的开始了
            with pytest.raises(sqlite3.OperationalError):
                transaction_manager._connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

    def test_commit_transaction(self, transaction_manager):
        """测试提交事务"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            transaction_manager.commit()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Committing transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Committing outermost transaction")

            # 验证提交是否成功
            cursor = transaction_manager._connection.execute("SELECT * FROM test WHERE id = 1")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 1
            assert result[1] == 'test'

    def test_rollback_transaction(self, transaction_manager):
        """测试回滚事务"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            transaction_manager.rollback()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Rolling back outermost transaction")

            # 验证回滚是否成功
            cursor = transaction_manager._connection.execute("SELECT * FROM test WHERE id = 1")
            assert cursor.fetchone() is None

    def test_nested_transactions(self, transaction_manager):
        """测试嵌套事务（使用保存点）"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # 第一级事务
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

            # 验证第一级事务日志
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")
            mock_log.reset_mock()

            # 第二级事务（保存点）
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

            # 验证第二级事务日志
            mock_log.assert_any_call(logging.INFO, "Creating savepoint LEVEL1 for nested transaction")
            mock_log.reset_mock()

            # 回滚到第二级保存点
            transaction_manager.rollback()

            # 验证回滚日志
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 2)")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint LEVEL1 for nested transaction")

            # 验证第二级事务回滚，但第一级事务数据保留
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'level1'

            # 提交第一级事务
            transaction_manager.commit()

            # 验证最终结果
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'level1'

    def test_multiple_nested_levels(self, transaction_manager):
        """测试多层嵌套事务"""
        # 创建三层嵌套事务
        transaction_manager.begin()  # 第1层
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

        transaction_manager.begin()  # 第2层
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

        transaction_manager.begin()  # 第3层
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'level3')")

        # 检查事务级别
        assert transaction_manager._transaction_level == 3
        assert transaction_manager.is_active is True

        # 回滚第3层
        transaction_manager.rollback()

        # 回滚后应该只有1和2
        cursor = transaction_manager._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in cursor.fetchall()]
        assert ids == [1, 2]
        assert transaction_manager._transaction_level == 2

        # 提交第2层
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # 再提交第1层
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 0
        assert transaction_manager.is_active is False

        # 检查最终结果
        cursor = transaction_manager._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in cursor.fetchall()]
        assert ids == [1, 2]

    def test_isolation_level_serializable(self, connection, logger):
        """测试可序列化隔离级别"""
        with patch.object(logging.Logger, 'log') as mock_log:
            manager = SQLiteTransactionManager(connection, logger)
            manager.isolation_level = IsolationLevel.SERIALIZABLE

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.SERIALIZABLE")
            # mock_log.assert_any_call(logging.INFO, "Isolation level set to IsolationLevel.SERIALIZABLE")

            manager.begin()

            # 验证使用了正确的隔离级别语法
            # SQLite 的 SERIALIZABLE 对应 IMMEDIATE 关键字
            assert manager.is_active is True

            # 检查 read_uncommitted 设置为 0（SERIALIZABLE 默认）
            cursor = connection.execute("PRAGMA read_uncommitted")
            result = cursor.fetchone()
            assert result[0] == 0

            manager.commit()

    def test_isolation_level_read_uncommitted(self, connection, logger):
        """测试读未提交隔离级别"""
        manager = SQLiteTransactionManager(connection, logger)
        with patch.object(manager, 'log') as mock_log:
            manager.isolation_level = IsolationLevel.READ_UNCOMMITTED

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.READ_UNCOMMITTED")
            # mock_log.assert_any_call(logging.INFO, "Isolation level set to IsolationLevel.READ_UNCOMMITTED")

            manager.begin()

            # 验证使用了正确的隔离级别语法
            # SQLite 的 READ_UNCOMMITTED 对应 DEFERRED 关键字
            assert manager.is_active is True

            # 检查 read_uncommitted 设置为 1
            cursor = connection.execute("PRAGMA read_uncommitted")
            result = cursor.fetchone()
            assert result[0] == 1

            manager.commit()

    def test_unsupported_isolation_level(self, transaction_manager):
        """测试不支持的隔离级别"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # SQLite 不支持 READ_COMMITTED
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED

            assert "Unsupported isolation level" in str(exc_info.value)

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.READ_COMMITTED")
            mock_log.assert_any_call(logging.ERROR, "Unsupported isolation level: IsolationLevel.READ_COMMITTED")

    def test_set_isolation_level_during_transaction(self, transaction_manager):
        """测试在事务期间设置隔离级别"""
        # 开始事务
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            # 尝试更改隔离级别
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE

            assert "Cannot change isolation level during active transaction" in str(exc_info.value)

            # 验证日志记录
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.SERIALIZABLE")
            mock_log.assert_any_call(logging.ERROR, "Cannot change isolation level during active transaction")

        # 清理
        transaction_manager.rollback()

    def test_savepoint_operations(self, transaction_manager):
        """测试保存点操作"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # 开始主事务
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'base')")
            mock_log.reset_mock()

            # 创建保存点
            sp1 = transaction_manager.savepoint("sp1")
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')")

            # 验证保存点创建日志
            mock_log.assert_any_call(logging.DEBUG, "Creating savepoint (name: sp1)")
            mock_log.assert_any_call(logging.INFO, "Creating savepoint: sp1")
            mock_log.reset_mock()

            # 创建第二个保存点
            sp2 = transaction_manager.savepoint("sp2")
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'sp2')")

            # 验证保存点创建日志
            mock_log.assert_any_call(logging.DEBUG, "Creating savepoint (name: sp2)")
            mock_log.assert_any_call(logging.INFO, "Creating savepoint: sp2")
            mock_log.reset_mock()

            # 回滚到第一个保存点
            transaction_manager.rollback_to("sp1")

            # 验证回滚到保存点日志
            mock_log.assert_any_call(logging.DEBUG, "Rolling back to savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint: sp1")

            # 验证回滚到 sp1 保存点
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            mock_log.reset_mock()

            # 新增数据
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')")

            # 释放保存点 sp1
            transaction_manager.release("sp1")

            # 验证释放保存点日志
            mock_log.assert_any_call(logging.DEBUG, "Releasing savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Releasing savepoint: sp1")
            mock_log.reset_mock()

            # 提交主事务
            transaction_manager.commit()

            # 验证提交日志
            mock_log.assert_any_call(logging.DEBUG, "Committing transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Committing outermost transaction")

            # 验证最终结果
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            assert rows[1][0] == 4
            assert rows[1][1] == 'after-rollback'

    def test_auto_savepoint_name(self, transaction_manager):
        """测试自动生成保存点名称"""
        # 开始事务
        transaction_manager.begin()

        # 使用自动名称创建保存点
        sp1 = transaction_manager.savepoint()
        assert sp1 == "SP_1"
        assert transaction_manager._savepoint_count == 1

        sp2 = transaction_manager.savepoint()
        assert sp2 == "SP_2"
        assert transaction_manager._savepoint_count == 2

        # 回滚到第一个保存点
        transaction_manager.rollback_to(sp1)

        # 再次创建自动命名的保存点
        sp3 = transaction_manager.savepoint()
        assert sp3 == "SP_3"
        assert transaction_manager._savepoint_count == 3

        # 清理
        transaction_manager.rollback()

    def test_transaction_error_handling(self):
        """测试事务错误处理"""
        # 模拟连接执行异常
        bad_connection = MagicMock()
        bad_connection.execute.side_effect = sqlite3.Error("Mock error")

        manager = SQLiteTransactionManager(bad_connection)

        with patch.object(manager, 'log') as mock_log:
            # 测试 begin 失败
            with pytest.raises(TransactionError) as exc_info:
                manager.begin()

            assert "Failed to begin transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to begin transaction: Mock error")

            # 测试 commit 失败 (手动设置事务级别)
            manager._transaction_level = 1
            # 不再需要设置 _active 标志，因为 is_active 现在只依赖 _transaction_level

            with pytest.raises(TransactionError) as exc_info:
                manager.commit()

            assert "Failed to commit transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to commit transaction: Mock error")

            # 确保transaction_level在失败后恢复
            assert manager._transaction_level == 1

            # 测试 rollback 失败
            with pytest.raises(TransactionError) as exc_info:
                manager.rollback()

            assert "Failed to rollback transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to rollback transaction: Mock error")

            # 确保transaction_level在失败后恢复
            assert manager._transaction_level == 1

            # 测试 savepoint 失败
            with pytest.raises(TransactionError) as exc_info:
                manager.savepoint("sp1")

            assert "Failed to create savepoint" in str(exc_info.value)
            assert any("Failed to create savepoint" in args[1] for args, kwargs in mock_log.call_args_list
                       if args[0] == logging.ERROR)

            # 手动将保存点添加到活动列表中以测试后续操作
            manager._active_savepoints.append("sp1")

            # 测试 release 失败
            with pytest.raises(TransactionError) as exc_info:
                manager.release("sp1")

            assert "Failed to release savepoint" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to release savepoint sp1: Mock error")

            # 测试 rollback_to 失败
            with pytest.raises(TransactionError) as exc_info:
                manager.rollback_to("sp1")

            assert "Failed to rollback to savepoint" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to rollback to savepoint sp1: Mock error")

    def test_commit_without_active_transaction(self, transaction_manager):
        """测试在无活动事务时提交"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.commit()

            assert "No active transaction to commit" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to commit")

    def test_rollback_without_active_transaction(self, transaction_manager):
        """测试在无活动事务时回滚"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.rollback()

            assert "No active transaction to rollback" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to rollback")

    def test_savepoint_without_active_transaction(self, transaction_manager):
        """测试在无活动事务时创建保存点"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.savepoint("sp1")

            assert "Cannot create savepoint: no active transaction" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Cannot create savepoint: no active transaction")

    def test_release_invalid_savepoint(self, transaction_manager):
        """测试释放不存在的保存点"""
        # 开始事务
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.release("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # 清理
        transaction_manager.rollback()

    def test_rollback_to_invalid_savepoint(self, transaction_manager):
        """测试回滚到不存在的保存点"""
        # 开始事务
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.rollback_to("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # 清理
        transaction_manager.rollback()

    def test_supports_savepoint(self, transaction_manager):
        """测试是否支持保存点"""
        assert transaction_manager.supports_savepoint() is True

    @pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 6, 8), reason="SQLite 3.6.8+ required for savepoint")
    def test_multiple_savepoints(self, transaction_manager):
        """测试多个保存点"""
        # 开始事务
        transaction_manager.begin()

        ## 创建多个保存点
        savepoints = []
        for i in range(5):
            transaction_manager._connection.execute(f"INSERT INTO test (id, value) VALUES ({i + 1}, 'value{i + 1}')")
            sp_name = transaction_manager.savepoint(f"sp{i + 1}")
            savepoints.append(sp_name)

        # 验证所有数据已插入
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 5

        # 回滚到中间保存点
        transaction_manager.rollback_to("sp3")

        # 验证回滚后的数据
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 3

        # 回滚到第一个保存点
        transaction_manager.rollback_to("sp1")

        # 验证回滚后的数据
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 1

        # 提交事务
        transaction_manager.commit()

        # 验证最终数据
        cursor = transaction_manager._connection.execute("SELECT * FROM test")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'value1'

    def test_transaction_level_counter(self, transaction_manager):
        """测试事务嵌套级别计数器"""
        assert transaction_manager._transaction_level == 0

        # 第一级事务
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 1

        # 第二级事务
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 2

        # 第三级事务
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 3

        # 回滚一级
        transaction_manager.rollback()
        assert transaction_manager._transaction_level == 2

        # 提交一级
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # 最后提交
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 0

    def test_mixed_savepoint_transactions(self, transaction_manager):
        """测试混合使用保存点和嵌套事务"""
        # 开始主事务
        transaction_manager.begin()
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'main')")

        # 创建手动保存点
        sp1 = transaction_manager.savepoint("manual_sp")
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')")

        # 创建嵌套事务（内部使用保存点）
        transaction_manager.begin()
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'nested')")

        # 现在应该有3行数据
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 3

        # 回滚嵌套事务
        transaction_manager.rollback()

        # 应该剩下2行数据
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 2

        # 回滚到手动保存点
        transaction_manager.rollback_to(sp1)

        # 应该剩下1行数据
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 1

        # 提交主事务
        transaction_manager.commit()

        # 验证最终结果
        cursor = transaction_manager._connection.execute("SELECT * FROM test")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'main'