# Connection Configuration

## Basic Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| host | str | localhost | {database} server address |
| port | int | {port} | {database} port |
| database | str | - | Database name |
| username | str | - | Username |
| password | str | - | Password |

## Advanced Configuration Options

```python
from rhosocial.activerecord.backend.impl.{backend} import (
    {Backend}Backend,
    {Backend}ConnectionConfig,
)

config = {Backend}ConnectionConfig(
    # Basic configuration
    host='localhost',
    port={port},
    database='myapp',
    username='myuser',
    password='mypassword',

    # Connection options
    connect_timeout=10,
    read_timeout=30,
    write_timeout=30,
)

backend = {Backend}Backend(config)
backend.connect()
```

## Using YAML Configuration

```yaml
# scenarios.yaml
scenarios:
  production:
    host: db.example.com
    port: {port}
    database: myapp_prod
    username: app_user
    password: ${DB_PASSWORD}

  development:
    host: localhost
    port: {port}
    database: myapp_dev
    username: dev_user
    password: dev_password
```

💡 *AI Prompt:* "What connection parameters are most important for production deployments?"
