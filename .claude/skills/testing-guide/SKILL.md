---
name: testing-guide
description: Testing patterns for rhosocial-activerecord including Provider pattern, sync/async parity, and test structure
license: MIT
compatibility: opencode
metadata:
  category: testing
  level: intermediate
---

## What I do

Provide testing best practices for the project:
- Environment setup (PYTHONPATH configuration)
- Provider pattern for backend-agnostic tests
- Sync/async test parity rules
- Protocol-based test skipping
- Fixture naming conventions

## When to use me

Use this skill when:
- Writing new tests
- Setting up test fixtures
- Ensuring sync/async parity
- Debugging test failures
- Understanding test architecture

## Required Setup

```bash
export PYTHONPATH=src  # Required!
pytest tests/ -v
```

## Testing Parity Rules

### Fixture Names
```python
# Sync
@pytest.fixture
def order_fixtures(backend_provider): ...

# Async - add 'async_' prefix
@pytest.fixture
def async_order_fixtures(backend_provider): ...
```

### Test Class Names
```python
class TestQuery: ...  # Sync
class TestAsyncQuery: ...  # Async (add Async prefix)
```

### Test Method Names
**MUST be identical**:
```python
def test_basic_query(self, fixtures): ...  # Sync

@pytest.mark.asyncio
async def test_basic_query(self, async_fixtures): ...  # Async
```

## Schema Sharing
Sync and async tests share the same SQL files - no duplication needed.

## Common Mistakes
- Forgetting PYTHONPATH
- Wrong fixture naming (order_fixtures_async vs async_order_fixtures)
- Different method names between sync/async
- Missing @pytest.mark.asyncio decorator
