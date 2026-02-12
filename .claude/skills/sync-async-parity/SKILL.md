---
name: sync-async-parity
description: Enforce strict sync/async API parity including naming conventions, docstrings, and field ordering
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: beginner
---

## What I do

Ensure strict parity between synchronous and asynchronous APIs:
- Class naming conventions (Async prefix)
- Method naming rules (identical names)
- Docstring requirements ("asynchronously")
- Field ordering consistency
- Testing parity rules

## When to use me

Use this skill when:
- Implementing new sync/async API pairs
- Reviewing code for parity violations
- Creating tests for both sync and async versions
- Understanding parity requirements

## Five Core Rules

### 1. Class Names
Add `Async` prefix to async versions:
```python
BaseActiveRecord → AsyncBaseActiveRecord
ActiveQuery → AsyncActiveQuery
StorageBackend → AsyncStorageBackend
```

### 2. Method Names (CRITICAL)
**Must be IDENTICAL** - no `_async` suffix:
```python
# CORRECT
def save(self): ...  # Sync
async def save(self): ...  # Async

# WRONG
def save(self): ...  # Sync
async def save_async(self): ...  # Async - DON'T DO THIS
```

### 3. Docstrings
Async version notes "asynchronously" in first sentence:
```python
def save(self):
    """Save the record to database."""
    
async def save(self):
    """Save the record to database asynchronously."""
```

### 4. Field Order
Declaration order must match exactly between sync and async.

### 5. Testing Parity
- Fixtures: `order_fixtures` → `async_order_fixtures`
- Test classes: `TestQuery` → `TestAsyncQuery`
- Test methods: identical names
- Schema files: shared

## Verification Checklist
- [ ] Class has Async prefix
- [ ] Method names identical
- [ ] Docstring mentions "asynchronously"
- [ ] Field order matches
- [ ] Tests follow parity rules
