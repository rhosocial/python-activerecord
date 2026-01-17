# FastAPI Integration

Since `ActiveRecord` models are essentially `Pydantic` models, they can be seamlessly used as FastAPI `response_model` or request bodies.

## Dependency Injection

Use `Depends` to manage database sessions or transactions (if a UnitOfWork is implemented).

```python
@app.post("/users/", response_model=User)
def create_user(user: User):
    user.save()
    return user
```

## Async Support

Although the core of this library is synchronous, you can adapt `async def` routes by using `run_in_executor` or using the `sqlite_async` backend (if implemented).
