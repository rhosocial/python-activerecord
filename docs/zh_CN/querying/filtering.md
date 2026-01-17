# 基础过滤 (Filtering & Sorting)

## 启动查询

每个模型都有一个 `query()` 方法（或者简写 `find()` / `find_all()`）。

```python
# 获取查询对象
q = User.query()
```

## 过滤 (Where)

支持链式调用。推荐使用 `Model.c.field` 进行类型安全的比较。

```python
# 查找所有活跃且年龄大于 18 的用户
users = User.query() \
    .where(User.c.is_active == True) \
    .where(User.c.age > 18) \
    .all()
```

也支持字典风格（隐式 AND）：

```python
users = User.find_all({'is_active': True, 'age': 20})
```

## 排序 (Order By)

```python
# 按创建时间倒序
posts = Post.query().order_by((Post.c.created_at, "DESC")).all()
```

## 分页 (Limit & Offset)

```python
# 获取第 2 页，每页 20 条
posts = Post.query().limit(20).offset(20).all()
```
