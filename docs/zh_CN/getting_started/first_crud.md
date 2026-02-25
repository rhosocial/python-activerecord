# 你的第一个 CRUD 应用

在本教程中，我们将从零开始构建一个简单的 **Todo 应用**。你将学习如何使用 `rhosocial-activerecord` 创建、读取、更新和删除数据。

## 你将构建什么

一个命令行 Todo 应用，你可以：
- ✅ 添加新任务
- 📋 列出所有任务（支持过滤）
- ✏️ 标记任务为已完成
- 🗑️ 删除任务

## AI 快速开始

> 💡 **AI 提示词：** "我是一个 Python 开发者。请帮我使用 rhosocial-activerecord 和 SQLite 创建一个完整的 Todo CRUD 应用，包含：(1) 包含 id、title、description、completed、created_at 字段的模型定义，(2) 数据库配置，(3) 所有增删改查操作，(4) 一个简单的命令行界面。使用 Python 3.8+ 语法并包含正确的导入语句。"
>
> 复制上面的提示词发送给 AI 助手，几秒钟内即可获得可运行的 CRUD 应用！

## 前置知识

- 已安装 Python 3.8 或更高版本
- 基本的 Python 知识（函数、类）
- 一个文本编辑器或 IDE

## 第 1 步：项目设置

### 创建项目目录

```bash
mkdir my_first_crud
cd my_first_crud
python -m venv venv
```

### 激活虚拟环境

```bash
# 在 macOS/Linux 上：
source venv/bin/activate

# 在 Windows 上：
venv\Scripts\activate
```

### 安装依赖

```bash
pip install rhosocial-activerecord
```

> 💡 **AI 提示词：** "什么是虚拟环境，为什么要使用它？"

## 第 2 步：创建数据库 Schema

在编写 Python 代码之前，让我们先了解需要存储哪些数据：

**Todo 任务：**
- `id`：唯一标识符（自动生成）
- `title`：需要做什么
- `description`：更多详情（可选）
- `completed`：是否完成（True/False）
- `created_at`：任务创建时间

## 第 3 步：定义模型

创建一个名为 `todo.py` 的文件：

```python
# todo.py
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class Todo(ActiveRecord):
    """Todo 任务模型。"""
    
    # 必需：启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # 字段
    id: Optional[int] = None  # 由数据库自动生成
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = False
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'todos'


# 配置数据库
config = SQLiteConnectionConfig(database='todo.db')
Todo.configure(config, SQLiteBackend)

# 创建表（在生产环境中，应使用迁移）
Todo.__backend__.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

**逐行解释：**

```python
from typing import ClassVar, Optional
```
- `ClassVar`：告诉 Pydantic 这是类变量，不是模型字段
- `Optional`：表示该字段可以为 None

```python
from rhosocial.activerecord.base import FieldProxy
```
- `FieldProxy`：你必须自行导入并定义，以启用类型安全查询，如 `Todo.c.completed == True`

```python
class Todo(ActiveRecord):
```
- 你的模型继承自 `ActiveRecord`，获得数据库操作能力

```python
c: ClassVar[FieldProxy] = FieldProxy()
```
- **需要你自行定义**：字段代理不是内置的——每个模型都必须定义它才能进行类型安全查询
- 你可以给它取任何名字（`c`、`fields`、`col` 等），`c` 只是约定俗成
- 没有它，你无法进行类型安全查询！

```python
id: Optional[int] = None
```
- 主键，由 SQLite 自动生成
- `Optional` 因为保存前它是 None

```python
title: str = Field(..., min_length=1, max_length=200)
```
- Pydantic 验证：title 必须是 1-200 个字符
- `...` 表示"必需字段"

```python
completed: bool = False
```
- 布尔字段，默认值为 `False`

```python
Todo.configure(config, SQLiteBackend)
```
- 将模型连接到 SQLite 数据库

> 💡 **AI 提示词：** "解释 FieldProxy 的作用以及为什么需要它来进行类型安全查询。"

## 第 4 步：创建（添加任务）

添加以下代码到 `todo.py`：

```python
# 添加到 todo.py

def add_task(title: str, description: str = None) -> Todo:
    """添加新任务。"""
    task = Todo(
        title=title,
        description=description,
        completed=False
    )
    task.save()  # 这会插入到数据库
    print(f"✅ 添加任务：{task.title} (ID: {task.id})")
    return task


# 测试
if __name__ == "__main__":
    # 添加一些任务
    add_task("学习 rhosocial-activerecord", "完成教程")
    add_task("构建 Todo 应用", "创建一个可用的应用")
    add_task("复习代码", "理解每一行")
```

**运行：**
```bash
python todo.py
```

**输出：**
```
✅ 添加任务：学习 rhosocial-activerecord (ID: 1)
✅ 添加任务：构建 Todo 应用 (ID: 2)
✅ 添加任务：复习代码 (ID: 3)
```

**解释：**
```python
task = Todo(title=title, description=description)
```
- 创建新的 Todo 实例（尚未在数据库中）

```python
task.save()
```
- **INSERT** 操作：保存到数据库
- `task.id` 现在填充了自动生成的 ID

> 💡 **AI 提示词：** "创建实例和调用 save() 有什么区别？"

## 第 5 步：读取（列出任务）

添加这些函数到 `todo.py`：

```python
# 添加到 todo.py

def list_all_tasks():
    """列出所有任务。"""
    tasks = Todo.query().order_by((Todo.c.created_at, "DESC")).all()
    
    print("\n📋 所有任务：")
    print("-" * 60)
    for task in tasks:
        status = "✅" if task.completed else "⬜"
        print(f"{status} [{task.id}] {task.title}")
        if task.description:
            print(f"   {task.description}")
    print()


def list_pending_tasks():
    """只列出未完成的任务。"""
    tasks = Todo.query() \
        .where(Todo.c.completed == False) \
        .order_by((Todo.c.created_at, "ASC")) \
        .all()
    
    print("\n⏳ 待处理任务：")
    print("-" * 60)
    for task in tasks:
        print(f"⬜ [{task.id}] {task.title}")
    print()


def find_task_by_id(task_id: int) -> Optional[Todo]:
    """通过 ID 查找任务。"""
    return Todo.find(task_id)


# 更新 main 块
if __name__ == "__main__":
    # 注释掉 add_task 调用以避免重复
    # add_task("学习 rhosocial-activerecord")
    
    list_all_tasks()
    list_pending_tasks()
    
    # 查找特定任务
    task = find_task_by_id(1)
    if task:
        print(f"找到任务：{task.title}")
```

**解释：**

```python
Todo.query().order_by((Todo.c.created_at, "DESC")).all()
```
- `.query()` - 开始构建查询
- `.order_by((Todo.c.created_at, "DESC"))` - 按创建时间排序，最新的在前
- `.all()` - 执行查询并返回所有结果

```python
.where(Todo.c.completed == False)
```
- 过滤：只返回 completed 为 False 的任务
- `Todo.c.completed` 是类型安全的（IDE 会提示自动补全！）

```python
Todo.find(task_id)
```
- 通过主键获取的快捷方式
- 如果未找到返回 `None`

> 💡 **AI 提示词：** "展示在这个 Todo 应用中过滤和排序任务的不同方式。"

## 第 6 步：更新（完成任务）

添加更新函数：

```python
# 添加到 todo.py

def complete_task(task_id: int) -> bool:
    """标记任务为已完成。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    task.completed = True
    task.save()  # 这执行 UPDATE
    print(f"✅ 完成任务：{task.title}")
    return True


def update_task_title(task_id: int, new_title: str) -> bool:
    """更新任务标题。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    task.title = new_title
    task.save()
    print(f"✏️ 更新任务 {task_id}：{new_title}")
    return True


# 更新 main 块
if __name__ == "__main__":
    complete_task(1)  # 完成任务 ID 1
    update_task_title(2, "构建一个超棒的 Todo 应用")
    list_all_tasks()
```

**解释：**
```python
task.completed = True
task.save()
```
- 修改属性
- `.save()` 自动检测它是已有记录（有 `id`）
- 执行 **UPDATE** 而不是 INSERT

> 💡 **AI 提示词：** "rhosocial-activerecord 如何知道是 INSERT 还是 UPDATE？"

## 第 7 步：删除（移除任务）

添加删除函数：

```python
# 添加到 todo.py

def delete_task(task_id: int) -> bool:
    """删除任务。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    title = task.title  # 保存用于确认消息
    task.delete()  # 这从数据库中移除
    print(f"🗑️ 删除任务：{title}")
    return True


# 更新 main 块
if __name__ == "__main__":
    delete_task(3)  # 删除任务 ID 3
    list_all_tasks()
```

**解释：**
```python
task.delete()
```
- **DELETE** 操作
- 从数据库中删除行
- Python 对象仍然存在，但已"分离"

## 第 8 步：交互式 CLI（可选）

让我们让它可以交互。创建 `todo_cli.py`：

```python
# todo_cli.py
from todo import Todo, add_task, list_all_tasks, list_pending_tasks, complete_task, delete_task


def show_menu():
    print("\n" + "="*60)
    print("📝 Todo 应用")
    print("="*60)
    print("1. 添加任务")
    print("2. 列出所有任务")
    print("3. 列出待处理任务")
    print("4. 完成任务")
    print("5. 删除任务")
    print("6. 退出")
    print("="*60)


def main():
    while True:
        show_menu()
        choice = input("\n选择操作 (1-6)：").strip()
        
        if choice == "1":
            title = input("任务标题：")
            desc = input("描述（可选）：") or None
            add_task(title, desc)
            
        elif choice == "2":
            list_all_tasks()
            
        elif choice == "3":
            list_pending_tasks()
            
        elif choice == "4":
            task_id = input("要完成的任务 ID：")
            if task_id.isdigit():
                complete_task(int(task_id))
            else:
                print("❌ 请输入有效的数字")
                
        elif choice == "5":
            task_id = input("要删除的任务 ID：")
            if task_id.isdigit():
                delete_task(int(task_id))
            else:
                print("❌ 请输入有效的数字")
                
        elif choice == "6":
            print("👋 再见！")
            break
            
        else:
            print("❌ 无效选项，请选择 1-6。")


if __name__ == "__main__":
    main()
```

**运行：**
```bash
python todo_cli.py
```

## 完整代码

这是完整的 `todo.py`：

<details>
<summary>点击展开完整代码</summary>

```python
# todo.py - 完整 CRUD 示例
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class Todo(ActiveRecord):
    """Todo 任务模型。"""
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = False
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'todos'


# 配置数据库
config = SQLiteConnectionConfig(database='todo.db')
Todo.configure(config, SQLiteBackend)

# 创建表
Todo.__backend__.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")


# CRUD 操作
def add_task(title: str, description: str = None) -> Todo:
    """添加新任务。"""
    task = Todo(title=title, description=description, completed=False)
    task.save()
    print(f"✅ 添加任务：{task.title} (ID: {task.id})")
    return task


def list_all_tasks():
    """列出所有任务。"""
    tasks = Todo.query().order_by((Todo.c.created_at, "DESC")).all()
    
    print("\n📋 所有任务：")
    print("-" * 60)
    for task in tasks:
        status = "✅" if task.completed else "⬜"
        print(f"{status} [{task.id}] {task.title}")
        if task.description:
            print(f"   {task.description}")
    print()


def list_pending_tasks():
    """只列出未完成的任务。"""
    tasks = Todo.query() \
        .where(Todo.c.completed == False) \
        .order_by((Todo.c.created_at, "ASC")) \
        .all()
    
    print("\n⏳ 待处理任务：")
    print("-" * 60)
    for task in tasks:
        print(f"⬜ [{task.id}] {task.title}")
    print()


def find_task_by_id(task_id: int) -> Optional[Todo]:
    """通过 ID 查找任务。"""
    return Todo.find(task_id)


def complete_task(task_id: int) -> bool:
    """标记任务为已完成。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    task.completed = True
    task.save()
    print(f"✅ 完成任务：{task.title}")
    return True


def update_task_title(task_id: int, new_title: str) -> bool:
    """更新任务标题。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    task.title = new_title
    task.save()
    print(f"✏️ 更新任务 {task_id}：{new_title}")
    return True


def delete_task(task_id: int) -> bool:
    """删除任务。"""
    task = Todo.find(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 未找到")
        return False
    
    title = task.title
    task.delete()
    print(f"🗑️ 删除任务：{title}")
    return True


# 演示
if __name__ == "__main__":
    # 添加示例任务（运行一次，然后注释掉）
    # add_task("学习 rhosocial-activerecord", "完成教程")
    # add_task("构建 Todo 应用", "创建一个可用的应用")
    # add_task("复习代码", "理解每一行")
    
    # 演示所有操作
    list_all_tasks()
    list_pending_tasks()
```

</details>

## 你学到了什么

✅ **创建**：`Model(**data).save()` → INSERT  
✅ **读取**：`Model.query().where(...).all()` → SELECT  
✅ **更新**：修改属性，然后 `.save()` → UPDATE  
✅ **删除**：`.delete()` → DELETE  

## 下一步

- 尝试添加验证（例如，防止空标题）
- 添加截止日期到任务
- 实现批量操作（完成多个任务）
- 阅读 [查询](../querying/README.md) 了解更多高级功能

## 另请参阅

- [配置](configuration.md) — 数据库设置详情
- [查询](../querying/README.md) — 高级查询功能
- [常见错误](troubleshooting.md) — 如果遇到问题
