# 集合操作与 CTE

`set` 与 `cte` 执行已有的 `SetOperationQuery` / `CTEQuery`，有两种用法：

1. **简单两侧**（`set union`、`union-all`、`intersect`、`except`）用 CLI 参数构造两个模型查询；
2. **组合查询**（`set run`、`cte run`）执行返回查询对象的工厂函数，覆盖 CTE、多臂组合和自定义谓词。

## 简单集合操作

```bash
rhosocial-activerecord set union \
  --left-model app.models:User --right-model app.models:Admin \
  --left-where "status=active" --right-where "status=active" -o json
```

- `--left-model` / `--right-model` 必填，且必须同为同步或同为异步。
- `--left-where` / `--right-where` 与 `dql list` 一样只支持等值 `field=value`；
  `--order-by`、`--select` 同时作用于两侧。
- `--limit`、`--offset`、`--page/--page-size` 会分别应用到两侧。**不会自动注入默认分页**。
- `union-all` 映射到 `UNION ALL`；`intersect` / `except` 需要后端支持。

行以字典返回，因为集合操作不绑定单一模型类；输出格式规则与普通查询行一致。

## 组合查询

```python
# app/queries.py
from app.models import Admin, User

def active_users_union():
    return User.query().where(User.c.status == "active").union(
        Admin.query().where(Admin.c.status == "active")
    )
```

```bash
rhosocial-activerecord set run --model app.models:User \
  --query app.queries:active_users_union -o json
```

- `set run` / `cte run` 的 `--model` 可选：工厂需要模型被配置时传，工厂自己配置连接时省略。
- 工厂函数无参数调用，必须返回 `SetOperationQuery`（`set run`）或 `CTEQuery`（`cte run`）；
  传入普通 `ActiveQuery` 会被拒绝，并在消息中说明期望类型。
- 这些命令调用 `aggregate()`。`SetOperationQuery` 与 `CTEQuery` 的行是字典，
  不支持 `all()` 或 `limit()`。
- `set run` / `cte run` 不额外加分页；需要限制行数时写进查询本身。

## CTE

```python
# app/queries.py
from rhosocial.activerecord.query import CTEQuery
from app.models import User

def older_users():
    cte = CTEQuery(User.backend())
    cte.with_cte("older_users", User.query().where(User.c.age >= 30))
    return cte.from_cte("older_users")
```

```bash
rhosocial-activerecord cte run --model app.models:User \
  --query app.queries:older_users -o json
```

递归 CTE 和方言差异都通过框架 API 在 Python 里构造，CLI 只执行结果对象。

## 后端支持

`intersect` / `except` 和递归 CTE 依赖数据库能力。方言不支持时后端抛出错误，CLI 以退出码 1
报告。CLI 没有能力开关：应在应用层用框架的 dialect 协议判断。

## 让 AI 使用这些命令

- 超出两个简单臂的组合，优先用 `set run` / `cte run`：工厂就是普通 Python，避免引号问题。
- 工厂内部调用 `Model.backend()` 时传 `--model`；只有工厂自己配置连接时才省略。
- 集合操作行是字典、没有模型元数据，`--fields` 必须是行里真实存在的键。
- 空结果时传 `--fields`，否则无法推断输出列。
- 查询类型不符（例如把 `ActiveQuery` 传给 `set run`）会以退出码 1 结束并说明期望类型；
  修正工厂，不要重复执行同一命令。
