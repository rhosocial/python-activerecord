# 运行模式 (Strict vs Raw)

## 严格模式 (默认)

默认情况下，所有查询结果都会经过 Pydantic 的验证与实例化。这保证了数据绝对符合模型定义，但会带来 CPU 开销。

```python
# 返回 User 实例列表，经过完整验证
users = User.find_all()
```

## 原始/聚合模式 (Raw Mode)

当你需要处理海量数据（如导出报表、ETL）且确信数据库数据有效时，可以使用 `.aggregate()` 模式（或 `find_all(raw=True)`，视具体 API 而定），直接返回 Python 字典或元组。

```python
# 绕过 Pydantic，直接返回字典列表
# 速度提升通常在 5x - 10x
users_data = User.query().aggregate()
```

**适用场景**:
*   只读列表展示
*   大数据导出
*   中间层数据处理
