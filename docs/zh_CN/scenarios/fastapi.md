# FastAPI 集成

由于 `ActiveRecord` 模型本质上就是 `Pydantic` 模型，它们可以无缝地用作 FastAPI 的 `response_model` 或请求体。

## 依赖注入

使用 `Depends` 来管理数据库会话或事务（如果实现了 UnitOfWork）。

```python
@app.post("/users/", response_model=User)
def create_user(user: User):
    user.save()
    return user
```

## 异步支持

虽然本库核心是同步的，但可以通过 `run_in_executor` 或使用 `sqlite_async` 后端（如果已实现）来适配 `async def` 路由。
