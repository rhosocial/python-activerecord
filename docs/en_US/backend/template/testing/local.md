# Local {database} Testing

## Overview

This section describes how to set up a local {database} testing environment using Docker.

## Running {database} with Docker

```bash
# Run {database} container
docker run -d \
  --name {backend}-test \
  -e {DB_ENV_USER}=test \
  -e {DB_ENV_PASSWORD}=test \
  -e {DB_ENV_DB}=test \
  -p {port}:{port} \
  {docker-image}:{version}
```

## Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  {backend}:
    image: {docker-image}:{version}
    environment:
      {DB_ENV_USER}: test
      {DB_ENV_PASSWORD}: test
      {DB_ENV_DB}: test
    ports:
      - "{port}:{port}"
    volumes:
      - {backend}_data:{data-path}

volumes:
  {backend}_data:
```

```bash
docker-compose up -d
```

## Running Tests

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT={port}
export DB_DATABASE=test
export DB_USER=test
export DB_PASSWORD=test

# Run tests (serially)
pytest tests/
```

> **Note**: Tests must be executed serially. The test suite uses fixed table names, and parallel execution will cause conflicts and failures.

```bash
# DO NOT use parallel execution
pytest -n auto          # ❌ WILL CAUSE FAILURES
pytest -n 4             # ❌ WILL CAUSE FAILURES

# Always run tests serially (default behavior)
pytest                  # ✅ Correct
```

💡 *AI Prompt:* "What is the difference between Docker and Docker Compose?"
