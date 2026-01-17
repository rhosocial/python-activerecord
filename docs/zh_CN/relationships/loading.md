# 加载策略 (Loading Strategies)

## N+1 查询问题

当你遍历一个列表并访问其关联关系时，可能会触发大量的数据库查询。

```python
users = User.find_all()  # 1次查询
for user in users:
    print(user.profile().bio)  # N次查询！
```

这就是著名的 N+1 问题。

## 预加载 (Eager Loading)

使用 `with_()` 方法可以在主查询中一并加载关联数据。

```python
# 告诉 ORM 我们需要同时加载 profile
users = User.query().with_('profile').find_all()

for user in users:
    # 这里不再触发数据库查询，直接从缓存读取
    print(user.profile().bio)
```

## 延迟加载 (Lazy Loading)

默认情况下，关系是延迟加载的。只有当你调用关系方法（如 `user.profile()`）时，才会执行 SQL。这对于不需要访问所有关联数据的场景更高效。

## 批量加载 (Batch Loading)

即使没有使用 `with_`，某些高级加载器也支持在访问第一个元素的关联时，自动批量加载列表中所有其他元素的关联（本库暂未默认启用此特性，主要依赖 `with_`）。
