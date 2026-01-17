# GraphQL 集成

## DataLoader 模式

GraphQL 极易产生 N+1 问题。使用 `DataLoader` 配合本库的 `in_` 查询可以完美解决。

```python
# 伪代码
async def user_loader(keys):
    users = User.query().where(User.c.id.in_(keys)).find_all()
    # 重组顺序以匹配 keys
    return [users_dict.get(k) for k in keys]
```
