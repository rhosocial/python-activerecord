---
name: Bug Report
about: Report a bug in rhosocial ActiveRecord
title: '[BUG] '
labels: 'bug'
assignees: ''
---

## Before Submitting

Please ensure this bug is related to the core ActiveRecord functionality that is NOT specific to any particular database backend. If the issue occurs only in a specific backend (e.g., MySQL, PostgreSQL, etc.), please submit the bug report to that backend's repository instead.

## Description

A clear and concise description of the bug.

## Environment

- **rhosocial ActiveRecord Version**: [e.g. 1.0.0.dev13]
- **Python Version**: [e.g. 3.13]
- **Database Backend**: [e.g. SQLite, MySQL, PostgreSQL, Oracle, SQL Server]
- **Database Version**: [e.g. MySQL 8.0, PostgreSQL 15.0]
- **OS**: [e.g. Linux, macOS, Windows]

## Steps to Reproduce

1.
2.
3.

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

What actually happened instead of the expected behavior.

## Database Query

If applicable, provide the generated SQL query that causes the issue:

```sql
-- Your problematic SQL query here
```

## Model Definition

If the issue is related to a specific model, please share your model definition:

```python
# Example model definition
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: EmailStr
```

## Error Details

If you're getting an error, include the full error message and stack trace:

```
Paste the full error message here
```

## Additional Context

Any other context about the problem here.