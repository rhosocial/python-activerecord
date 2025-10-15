# 基本测试指南

使用 rhosocial ActiveRecord 进行单元测试目前专注于基本模型功能和简单操作。

## 概述

当前单元测试包括：

- 测试基本模型创建和验证
- 验证简单CRUD操作
- 基本查询执行验证

## 测试框架

rhosocial ActiveRecord 与标准Python测试框架配合使用：

- `unittest` - Python的内置测试框架
- `pytest` - 功能更丰富的测试框架

## 基本测试设置

使用ActiveRecord模型进行测试：

1. 配置测试数据库（通常使用内存中的SQLite）
2. 创建必要的数据库表
3. 测试基本模型操作

## 当前限制

- 无内置测试夹具或工厂
- 有限的关系测试支持
- 无事务测试框架
- 仅限基本错误处理验证

## 简单测试示例

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestUser(unittest.TestCase):
    def setUp(self):
        # 设置测试数据库
        pass

    def test_model_creation(self):
        user = User(name="测试用户", email="test@example.com")
        self.assertEqual(user.name, "测试用户")
        
    def test_save_operation(self):
        user = User(name="测试用户", email="test@example.com")
        result = user.save()
        # 验证保存操作完成
        self.assertTrue(result)
```

## 概述

有效的ActiveRecord应用程序单元测试包括：

- 测试模型验证和业务逻辑
- 验证关系行为
- 确保事务完整性
- 在适当时模拟数据库连接

## 测试框架

rhosocial ActiveRecord设计为与标准Python测试框架无缝协作，如：

- `unittest` - Python的内置测试框架
- `pytest` - 一个功能更丰富的测试框架，具有出色的fixture支持

## 测试数据库配置

测试ActiveRecord模型时，建议：

1. 使用单独的测试数据库配置
2. 在测试之间重置数据库状态
3. 使用事务隔离测试用例
4. 在适当时考虑使用内存SQLite以加快测试速度

## 目录

- [模型测试](model_testing.md) - 测试ActiveRecord模型的策略
- [关系测试](relationship_testing.md) - 测试模型关系的技术
- [事务测试](transaction_testing.md) - 测试数据库事务的方法

## 最佳实践

- 保持测试隔离和独立
- 使用fixtures或工厂创建测试数据
- 测试有效和无效的场景
- 在必要时模拟外部依赖
- 使用数据库事务加速测试并确保隔离