# Test Configuration

## Overview

This section describes how to configure the testing environment for the {backend} backend.

For general testing strategies (DummyBackend, SQLite integration), see the [Core Backend Testing Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/backend_testing.md).

## End-to-End Testing with {database} Backend

For complete {database} behavior testing, configure the {database} backend with a real database:

```python
import os
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend, {Backend}ConnectionConfig
from typing import ClassVar


class User(ActiveRecord):
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Read configuration from environment variables
config = {Backend}ConnectionConfig(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', {port})),
    database=os.environ.get('DB_DATABASE', 'test'),
    username=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
)
User.configure(config, {Backend}Backend)
```

## Test Fixtures

```python
import pytest


@pytest.fixture
def backend_config():
    return {Backend}ConnectionConfig(
        host='localhost',
        port={port},
        database='test',
        username='root',
        password='password',
    )


@pytest.fixture
def backend(backend_config):
    backend = {Backend}Backend(connection_config=backend_config)
    backend.connect()
    yield backend
    backend.disconnect()
```

## See Also

- [Core Backend Testing Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/backend_testing.md) — three-tier testing strategy
