# 缓存机制 (Caching)

本库包含多级缓存优化：

1.  **元数据缓存**: 字段映射、列名信息只解析一次。
2.  **关系缓存**: `user.posts()` 第一次调用后会缓存结果，除非显式刷新或过期。

## 清除关系缓存

```python
# 强制重新查询数据库
user.clear_relation_cache('posts')
# 或者
user.posts.clear_cache()
```

## 批量加载缓存

在使用 `batch_load` 或 `with_` 时，ORM 会智能地填充这些缓存，避免后续访问触发查询。
