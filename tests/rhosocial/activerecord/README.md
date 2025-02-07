### Directory structure:

```
tests/
├── conftest.py  # 全局夹具导入
├── fixtures/    # 所有夹具
│   ├── __init__.py
│   ├── storage.py
│   ├── basic/        # 基础模型相关夹具
│   │   ├── __init__.py
│   │   ├── models.py   # 不同字段类型的基础模型
│   │   └── schema      # 存放对应 models.py 中模型的数据表模式。目前仅列出 sqlite。
│   ├── community/    # 社区相关夹具
│   │   ├── __init__.py
│   │   ├── models.py   # 社区基础模型定义
│   │   ├── queries.py  # 预定义查询
│   │   └── setup.py    # 表结构和初始数据
│   ├── mixins/       # 混入功能夹具
│   │   ├── __init__.py
│   │   ├── models.py   # 使用各种混入的模型
│   │   └── setup.py    # 相关表结构
│   └── events.py     # 事件相关夹具
├── basic/           # 基础功能测试
│   ├── __init__.py
│   ├── test_crud.py         # 基本CRUD操作测试
│   ├── test_validation.py   # 数据验证测试
│   └── test_fields.py       # 字段类型和处理测试
├── events/          # 事件系统测试
│   ├── __init__.py
│   ├── test_lifecycle.py    # 生命周期事件测试
│   └── test_handlers.py     # 事件处理器测试
├── query/           # 查询相关测试
│   ├── __init__.py
│   ├── test_basic.py        # 基本查询功能测试
│   ├── test_conditions.py   # 查询条件测试
│   └── test_joins.py        # 关联查询测试
├── community/       # 社区功能测试
│   ├── __init__.py
│   ├── test_users.py        # 用户相关功能测试
│   ├── test_articles.py     # 文章相关功能测试
│   ├── test_comments.py     # 评论相关功能测试
│   ├── test_friendships.py  # 好友关系测试
│   └── test_queries.py      # 预定义查询测试
├── mixins/          # 混入功能测试  
│   ├── __init__.py
│   ├── test_timestamps.py   # 时间戳混入测试
│   ├── test_soft_delete.py  # 软删除混入测试
│   └── test_optimistic_lock.py  # 乐观锁混入测试
└── storage/         # 存储后端测试
    ├── __init__.py
    ├── test_backend.py      # 后端基本功能测试
    └── test_transactions.py  # 事务功能测试
```