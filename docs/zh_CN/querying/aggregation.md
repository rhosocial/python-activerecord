# 聚合统计 (Aggregation)

## 基础函数

支持标准的 SQL 聚合函数：`count`, `sum_`, `avg`, `min_`, `max_`。

```python
# 统计总用户数
total = User.query().count()

# 计算所有文章的总阅读量
total_views = Post.query().sum_(Post.c.views)
```

## 分组 (Group By)

统计每个用户的文章数量：

```python
from rhosocial.activerecord.backend.expression import functions

# SELECT user_id, COUNT(*) FROM posts GROUP BY user_id
results = Post.query() \
    .select(Post.c.user_id, functions.count('*')) \
    .group_by(Post.c.user_id) \
    .aggregate()
```

> **注意**: 分组查询通常返回字典或元组，而不是模型实例，除非结果能完整映射回模型。
