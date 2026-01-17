# GraphQL Integration

## DataLoader Pattern

GraphQL is prone to the N+1 problem. Using `DataLoader` in conjunction with this library's `in_` query can perfectly solve it.

```python
# Pseudo-code
async def user_loader(keys):
    users = User.query().where(User.c.id.in_(keys)).find_all()
    # Reorder to match keys
    return [users_dict.get(k) for k in keys]
```
