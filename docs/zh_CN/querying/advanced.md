# 高级查询 (Advanced Features)

## 连接 (Joins)

显式连接其他表。

```python
# 查找所有发表过文章的用户
users = User.query() \
    .join(Post, on=(User.c.id == Post.c.user_id)) \
    .group_by(User.c.id) \
    .all()
```

## CTE (公用表表达式)

对于复杂查询，CTE 可以让逻辑更清晰。

```python
from rhosocial.activerecord.query import CTEQuery

# 定义 CTE：找出最近活跃的用户
recent_users_cte = User.query().where(User.c.last_login > '2023-01-01')

# 使用 CTE
query = CTEQuery(User.backend()) \
    .with_cte('recent_users', recent_users_cte) \
    .query(
        User.query().join('recent_users', on='users.id = recent_users.id')
    )

results = query.aggregate()
```

## 窗口函数 (Window Functions)

需要后端支持（SQLite 3.25+）。

```python
from rhosocial.activerecord.backend.expression.window import Window, Rank

# 对每个类别的文章按浏览量排名
window = Window.partition_by(Post.c.category_id).order_by((Post.c.views, "DESC"))
rank_col = Rank().over(window).as_('rank')

results = Post.query().select(Post.c.title, rank_col).aggregate()
```
