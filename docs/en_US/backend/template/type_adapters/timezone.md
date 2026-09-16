# Timezone Handling

## Overview

{database} handles timestamps and timezones differently from Python. This document explains how rhosocial-activerecord bridges the gap.

## Timestamp Types

<!-- Document backend-specific timestamp types. Examples:

### MySQL: DATETIME vs TIMESTAMP

| Type | Range | Timezone | Storage |
|------|-------|----------|---------|
| DATETIME | 1000-01-01 to 9999-12-31 | Stores as-is | 8 bytes |
| TIMESTAMP | 1970-01-01 to 2038-01-19 | Converts to UTC | 4 bytes |

### PostgreSQL: TIMESTAMP vs TIMESTAMPTZ

| Type | Timezone | Storage |
|------|----------|---------|
| TIMESTAMP | Stores as-is | 8 bytes |
| TIMESTAMPTZ | Converts to UTC | 8 bytes |

-->

## Python Handling

```python
from datetime import datetime, timezone

# Store UTC
now = datetime.now(timezone.utc)

# {database} stores in its timezone
# The adapter handles conversion automatically
```

## Best Practices

1. **Store UTC**: Always store timestamps in UTC. Convert to local time only at the presentation layer.
2. **Use timezone-aware datetime objects**: In Python, always use `datetime.now(timezone.utc)` instead of `datetime.now()`.
3. **Configure server timezone**: Ensure the {database} server timezone is set to UTC for consistent behavior.
4. **Future events**: Use timezone-aware timestamps for events that occur in the future (e.g., scheduled tasks).

## See Also

- [Type Mapping](mapping.md) — type conversion table
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "What is the difference between TIMESTAMP and TIMESTAMPTZ in {database}?"
