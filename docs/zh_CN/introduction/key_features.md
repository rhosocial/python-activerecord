# 核心特性之旅 (A Tour of Key Features)

不要被各种技术术语吓到。让我们通过一个实际的场景——构建一个简单的博客系统——来看看 `rhosocial-activerecord` 是如何帮助你更轻松地编写代码的。

## 1. 定义你的数据：所见即所得
一切从定义模型开始。在 `rhosocial-activerecord` 中，你的模型 **本质上就是** Pydantic 模型。这意味着你不需要学习一套新的验证规则，利用你熟悉的 Pydantic 知识即可。

```python
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from pydantic import Field

class User(ActiveRecord):
    # 直接使用 Pydantic 进行强大的数据验证
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(..., ge=18)

    # 启用字段代理，为后续的查询提供类型支持
    c: ClassVar[FieldProxy] = FieldProxy()

# 尝试创建一个非法用户
# user = User(username="al", email="not-an-email", age=10) 
# ^ 这会立即抛出 Pydantic ValidationError，甚至不需要连接数据库！
```

**这一步解决了什么？**
你不再需要担心“垃圾数据”进入数据库。验证发生在 Python 层面，而且是即时的。

## 2. 拒绝重复劳动：像搭积木一样组合功能
很快你会发现，不仅是 `User`，你的 `Post` (文章) 和 `Comment` (评论) 都需要唯一的 ID，都需要记录创建时间 (`created_at`) 和更新时间 (`updated_at`)。

难道要在每个类里重复写这些字段吗？不需要。我们推崇 **组合优于继承**。

```python
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin

# 通过继承 Mixin，一行代码获得通用能力
class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    title: str
    content: str
    
    c: ClassVar[FieldProxy] = FieldProxy()

# 现在 Post 自动拥有了：
# - id (UUID 类型，自动生成)
# - created_at (自动记录创建时间)
# - updated_at (自动更新修改时间)
```

**这一步解决了什么？**
你的模型代码保持干净、专注于业务逻辑，通用功能通过 Mixin 复用。

## 3. 像写代码一样写查询：告别拼写错误
数据有了，现在我们要查询它。在传统 ORM 中，你经常需要小心翼翼地拼写字符串字段名，一旦拼错，程序跑起来才会报错。

`rhosocial-activerecord` 提供了 `FieldProxy` 系统（即上面的 `c`），让你的查询代码像普通 Python 代码一样拥有智能提示。

```python
# ❌ 糟糕的写法（传统方式）
# 如果你把 'username' 拼成了 'usrname'，只有运行时才知道错了
# User.query().where("usrname == 'alice'")

# ✅ 我们的写法
# IDE 会自动补全 .username，如果拼错，IDE 会直接标红警告
users = User.query().where(User.c.username == "alice").all()
```

**这一步解决了什么？**
将运行时错误提前到了编写代码时，利用 IDE 的能力大幅减少低级 bug。

## 4. 既要安全，又要速度：灵活的数据访问
你的博客火了，现在你需要导出一百万条日志进行分析。
*   使用完整对象一个个处理太慢了，因为创建一百万个 Python 对象开销很大。
*   写原生 SQL 又容易出错且难以维护。

`rhosocial-activerecord` 允许你在同一个库中无缝切换：

```python
# 场景 A：处理用户注册（需要完整校验）
# 使用 ActiveRecord 对象，享受完整的 Pydantic 验证和生命周期钩子
user = User(username="bob", email="bob@example.com", age=20)
user.save()

# 场景 B：生成大数据报表（追求极致性能）
# 使用 aggregate()，直接获取字典列表，跳过对象创建和验证，速度媲美原生 SQL
# 这里我们依然使用 User.c.active 享受类型提示，但结果是原始数据
raw_data = User.query().where(User.c.age > 20).limit(100000).aggregate()
```

**这一步解决了什么？**
你不必因为性能问题而被迫放弃 ORM，也不必因为追求性能而牺牲关键业务的安全性。

## 5. 零负担测试：不需要数据库也能测试 SQL
最后，你要上线了。你写了一个复杂的查询逻辑，想写个单元测试验证它。
通常你需要：安装 Docker -> 启动 MySQL -> 创建表 -> 插入数据 -> 运行测试 -> 清理数据... 太麻烦了！

我们可以直接测试“生成的 SQL 是否正确”：

```python
# 直接查看生成的 SQL，无需连接任何数据库
sql, params = User.query().where(User.c.username == "alice").to_sql()

# 断言生成的 SQL 符合预期
assert "SELECT * FROM users WHERE username = ?" in sql
assert params == ("alice",)
```

**这一步解决了什么？**
你的单元测试可以飞快运行，不需要任何外部环境依赖。


## 同步异步对等：跨范式功能等价性 (Sync-Async Parity: Equivalent Functionality Across Paradigms)

`rhosocial-activerecord` 的一个基本设计原则是**同步异步对等**，这意味着同步和异步实现提供等效的功能和一致的 API。

### 同步和异步模型 (Synchronous and Asynchronous Models)

同步和异步模型共享相同的结构和 API：

```python
# 同步模型
class User(ActiveRecord):
    username: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# 异步模型  
class AsyncUser(AsyncActiveRecord):
    username: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

### 一致的查询接口 (Consistent Query Interface)

同步和异步查询提供相同的方法，具有相同的签名：

```python
# 同步查询
users = User.query().where(User.c.username == 'john').all()

# 异步查询 - 相同的 API，只需使用 await
async def get_users():
    users = await AsyncUser.query().where(AsyncUser.c.username == 'john').all()
    return users
```

这种对等性使开发人员能够在同步和异步上下文之间无缝过渡，而无需学习不同的 API 或牺牲功能。

