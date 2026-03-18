# 环境感知的 Fixture 选择系统

测试套件提供了一套环境感知的 fixture 选择机制，允许根据运行时 Python 版本自动选择最合适的模型类。这使得测试代码能够利用新版本 Python 的语言特性，同时保持向后兼容性。

## 概述

### 设计目标

1. **版本感知**：根据运行时 Python 版本选择最优的模型实现
2. **渐进增强**：高版本 Python 用户获得更好的类型提示和语言特性
3. **向后兼容**：低版本 Python 用户仍能正常运行测试
4. **透明集成**：后端开发者无需关心版本细节，自动获得最佳实现

### 版本特定特性

| Python 版本 | 特性 | 示例 |
|------------|------|------|
| 3.10+ | 联合类型语法 | `int \| None` 代替 `Optional[int]` |
| 3.11+ | Self 类型 | 链式方法的精确返回类型 |
| 3.12+ | @override 装饰器 | 显式标记方法覆写 |
| 3.12+ | 类型参数语法 | `class Model[T]:` 代替 `Generic[T]` |

## 架构

### Fixture 文件结构

每个功能模块的 fixtures 目录包含多个版本特定的模型文件：

```
testsuite/feature/query/fixtures/
├── models.py           # 基础版本 (Python 3.8+)
├── models_py310.py     # Python 3.10+ 特性
├── models_py311.py     # Python 3.11+ 特性
└── models_py312.py     # Python 3.12+ 特性
```

### 版本声明机制

每个版本特定的模型类通过 `__requires_python__` 属性声明其最低 Python 版本要求：

```python
# models_py312.py
from typing import ClassVar, override
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __requires_python__ = (3, 12)  # 声明最低版本

    id: int | None = None
    username: str

    @override
    def get_display_name(self) -> str:
        return self.username
```

### 选择器函数

测试套件提供 `select_fixture()` 函数用于选择最合适的模型类：

```python
from rhosocial.activerecord.testsuite.utils import select_fixture

# 选择最高兼容版本
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])
```

选择逻辑：
1. 按列表顺序检查每个候选类
2. 检查类的 `__requires_python__` 属性
3. 返回第一个满足当前 Python 版本的类
4. 若无匹配，返回列表中最后一个类（通常是基础版本）

## 后端集成

### Provider 实现模式

后端开发者应在模块级别使用 fixture 选择模式：

```python
# tests/providers/query.py
import sys
from rhosocial.activerecord.testsuite.utils import select_fixture

# 导入基础版本
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import (
    User as UserBase,
    Order as OrderBase,
)

# 条件导入高版本
UserPy310 = UserPy311 = UserPy312 = None
if sys.version_info >= (3, 10):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py310 import (
        User as UserPy310,
    )
if sys.version_info >= (3, 11):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py311 import (
        User as UserPy311,
    )
if sys.version_info >= (3, 12):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py312 import (
        User as UserPy312,
    )

# 模块级别选择最合适的模型类
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])
Order = select_fixture([OrderPy312, OrderPy311, OrderPy310, OrderBase])
```

### 辅助函数

为简化重复代码，可定义模块级别的辅助函数：

```python
def _select_model_class(base_class, *versioned_classes, name: str):
    """选择最高兼容版本的模型类"""
    candidates = [c for c in versioned_classes if c is not None]
    if not candidates:
        return base_class
    return select_fixture([*candidates, base_class])
```

## 已支持的功能模块

以下功能模块已支持环境感知的 fixture 选择：

| 模块 | 基础版本 | py310 | py311 | py312 |
|------|----------|-------|-------|-------|
| basic | ✅ | ✅ | ✅ | ✅ |
| events | ✅ | ✅ | ✅ | ✅ |
| mixins | ✅ | ✅ | ✅ | ✅ |
| query | ✅ | ✅ | ✅ | ✅ |
| relation | ✅ | ✅ | ✅ | ✅ |

## 最佳实践

### 1. 在模块级别选择模型

推荐在模块级别完成模型选择，而非在方法内部：

```python
# ✅ 推荐：模块级别选择
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])

class QueryProvider:
    def setup_user_fixtures(self):
        user = User(username="test")
        # ...

# ❌ 不推荐：方法内部导入
class QueryProvider:
    def setup_user_fixtures(self):
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User
        user = User(username="test")
```

### 2. 保持一致的导入顺序

始终按版本从高到低的顺序排列候选类：

```python
# ✅ 正确顺序：高版本优先
Model = select_fixture([ModelPy312, ModelPy311, ModelPy310, ModelBase])

# ❌ 错误顺序：低版本优先会导致无法使用新特性
Model = select_fixture([ModelBase, ModelPy310, ModelPy311, ModelPy312])
```

### 3. 处理可选依赖

某些版本特定特性可能依赖新的标准库模块：

```python
from typing import ClassVar

# Python 3.11+ 的 Self 类型
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
```
