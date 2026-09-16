# Connection Management

## Overview

Both `{Backend}Backend` (synchronous) and `Async{Backend}Backend` (asynchronous) maintain a **single persistent connection** per backend instance. The `pool_*` configuration fields inherited from `ConnectionPoolMixin` are recognised by the config class but may not be consumed by the backend — check the backend-specific details below.

## Current Behaviour

### Synchronous Backend

`{Backend}Backend.connect()` opens a persistent connection to the {database} server. The connection remains open until `disconnect()` is called.

```python
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend, {Backend}ConnectionConfig

config = {Backend}ConnectionConfig(
    host="localhost",
    port={port},
    database="myapp",
    username="app",
    password="secret",
)
backend = {Backend}Backend(config)
backend.connect()     # opens one persistent connection
```

### Asynchronous Backend

`Async{Backend}Backend.connect()` opens a persistent async connection. The API is identical to the synchronous version, with `await` prefixes.

```python
import asyncio
from rhosocial.activerecord.backend.impl.{backend} import Async{Backend}Backend, {Backend}ConnectionConfig

config = {Backend}ConnectionConfig(
    host="localhost",
    port={port},
    database="myapp",
    username="app",
    password="secret",
)

async def main():
    backend = Async{Backend}Backend(config)
    await backend.connect()
    # ... use the backend ...
    await backend.disconnect()

asyncio.run(main())
```

## Connection Lifecycle Guidelines

### One Backend Per Process

Configure your models once at application startup (not inside request handlers). Each call to `Model.configure(config, backend_class)` creates a new backend instance and a new underlying connection.

```python
# application startup (e.g., FastAPI lifespan)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from rhosocial.activerecord.backend.impl.{backend} import Async{Backend}Backend, {Backend}ConnectionConfig
from myapp.models import User, Order

_config = {Backend}ConnectionConfig(
    host="db.prod.internal",
    port={port},
    database="myapp",
    username="app",
    password="secret",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    User.configure(_config, Async{Backend}Backend)
    Order.configure(_config, Async{Backend}Backend)
    await User.backend().connect()
    await Order.backend().connect()
    yield
    await User.backend().disconnect()
    await Order.backend().disconnect()

app = FastAPI(lifespan=lifespan)
```

### Do NOT Configure Inside Request Handlers

```python
# ❌ Anti-pattern — creates a new connection on every request
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    User.configure(_config, Async{Backend}Backend)
    await User.backend().connect()
    user = await User.find_one(user_id)
    await User.backend().disconnect()
    return user

# ✅ Correct — connection already open from lifespan
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return await User.find(user_id)
```

## Connection Timeout Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connect_timeout` | `int` | `10` | Seconds before a connection attempt is abandoned |
| `read_timeout` | `int` | `30` | Seconds before a read operation times out |
| `write_timeout` | `int` | `30` | Seconds before a write operation times out |

## See Also

- [Connection Configuration](configuration.md) — full list of configuration options
- [Troubleshooting: Connection Issues](../troubleshooting/connection.md) — diagnosing connection errors
- [Core: Connection Management](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/connection)
