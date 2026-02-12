# Knowledge Base Instructions - RhoSocial ActiveRecord

## Overview

This document provides comprehensive instructions for understanding and working with the **rhosocial-activerecord** ecosystem. The project implements a modern, Pythonic ActiveRecord pattern with type safety and rich features.

**Key Differentiator**: This is a standalone ActiveRecord implementation built from scratch with **only Pydantic as a dependency** - no reliance on existing ORMs like SQLAlchemy or Django ORM. All database interaction logic is implemented directly through a clean backend abstraction layer.

## Quick Reference

- **Primary Project**: rhosocial-activerecord (core implementation)
- **Extension Projects**: rhosocial-activerecord-mysql, rhosocial-activerecord-postgresql, etc.
- **Test Suite Package**: rhosocial-activerecord-testsuite (planned - standardized testing contracts)
- **Documentation**: `docs/` directory with en_US and zh_CN versions
- **Python Version**: 3.8+ required
- **Core Dependency**: Pydantic 2.x only (no ORM dependencies)
- **Testing Framework**: pytest with extensive fixtures

## Instruction Documents

This knowledge base is organized into the following specialized instruction documents:

### 📝 [CODE_STYLE.md](./.claude/code_style.md)
Coding standards, conventions, and style guidelines for the project.

### 🏗️ [ARCHITECTURE.md](./.claude/architecture.md)
System architecture, design patterns, and module organization.

### 🔖 [VERSION_CONTROL.md](./.claude/version_control.md)
Version management, branching strategy, and release procedures.

### 🧪 [TESTING.md](./.claude/testing.md)
Testing strategy with planned testsuite package separation, current test structure, and future migration path.

### 🔌 [BACKEND_DEVELOPMENT.md](./.claude/backend_development.md)
Guidelines for developing new database backend implementations.

## Project Identification

### File Path Comments

Every source file begins with a comment indicating its relative path:

```python
# Python files
# src/rhosocial/activerecord/backend/base.py

# SQL files
-- tests/rhosocial/activerecord_test/query/fixtures/schema/sqlite/users.sql

# YAML files
# .github/workflows/test.yml
```

### Module Hierarchy

```
rhosocial.activerecord/
├── base/               # Core ActiveRecord functionality
├── field/              # Field types and behaviors
├── query/              # Query building and execution
├── relation/           # Relationship management
├── interface/          # Public API interfaces
└── backend/            # Database backend abstraction
    └── impl/           # Concrete implementations
        ├── sqlite/     # Built-in SQLite support
        ├── mysql/      # Separate package
        └── postgresql/ # Separate package
```

## Key Principles

### 1. Standalone Implementation
The project is a **pure Python ActiveRecord implementation** with no ORM dependencies:
- Built from scratch with only Pydantic for data validation
- No dependency on SQLAlchemy, Django ORM, or other existing ORMs
- Direct database driver interaction through backend abstraction

### 2. Namespace Package Architecture
The project uses Python namespace packages to allow distributed backend implementations:
- Core package: `rhosocial-activerecord`
- Backend packages: `rhosocial-activerecord-{backend}`
- Test suite package: `rhosocial-activerecord-testsuite` (planned)
- Extensions seamlessly integrate via `pkgutil.extend_path`

### 3. Protocol-Based Design
Heavy use of Python protocols and abstract base classes:
- Interfaces defined in `interface/` package
- Backend protocol in `backend/base.py`
- Type converters use protocol pattern

### 4. Separation of Concerns
- Core logic separated from database specifics
- Test definitions will be separated from backend implementations (planned)
- Each backend handles its own dialect and type conversion
- Mixins provide composable functionality

### 5. Type Safety
- Pydantic models for data validation
- Extensive type hints throughout
- Runtime type checking where appropriate

## Common Tasks

### Adding a New Feature

1. **Design Interface First**
   - Define abstract interface in `interface/` package
   - Use Protocol or ABC as appropriate

2. **Implement in Base**
   - Add implementation to appropriate base class
   - Ensure backward compatibility

3. **Add Tests to Testsuite**
   - Define test contracts in testsuite package
   - Write comprehensive test cases
   - Use appropriate pytest markers

4. **Update Documentation**
   - Add docstrings following Google style
   - Update README if needed
   - Add examples to tests

### Debugging Guidelines

1. **Check Path Comments**: Verify file locations match path comments
2. **Review Test Fixtures**: Tests often show correct usage patterns
3. **Trace Through Mixins**: Follow MRO for method resolution
4. **Check Backend Configuration**: Ensure proper backend setup
5. **Verify Testsuite Compatibility**: Check testsuite version compatibility

### Working with Tests

```python
# Current test execution (tests in main repository)
pytest tests/

# Future testsuite execution (when available)
pytest --run-testsuite

# Running specific test categories (future)
pytest -m "feature"
pytest -m "realworld"
pytest -m "benchmark"

# Generate compatibility report (future)
pytest --compat-report=html
pytest --compat-report=console
```

## Critical Implementation Notes

### 1. Backend Loading
Backends are loaded dynamically at runtime:
```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
Model.configure(config, SQLiteBackend)
```

### 2. Field Tracking
- Fields prefixed with `_` are not tracked
- Use `__no_track_fields__` class variable for exclusions
- Original values stored in `_original_values`

### 3. Event System
Models support lifecycle events:
- `before_save`, `after_save`
- `before_delete`, `after_delete`
- `before_validation`, `after_validation`

### 4. Query Building
Queries use method chaining:
```python
User.where(age__gte=18).order_by("-created_at").limit(10)
```

### 5. Test Suite Integration
The separated testsuite package (planned) will define standardized test contracts:
- Feature tests validate individual functionality
- Real-world scenarios test complex interactions
- Performance benchmarks measure backend performance
- Currently tests remain in main repository, migration is planned

## Version Compatibility Matrix

| Component | Python | SQLite | MySQL | PostgreSQL | Testsuite* |
|-----------|--------|--------|-------|------------|-----------|
| Core | 3.8+ | 3.8.3+ | - | - | - |
| MySQL Backend | 3.8+ | - | 5.7+ | - | TBD |
| PostgreSQL Backend | 3.8+ | - | - | 11+ | TBD |

*Testsuite versions will be determined upon package release

## Error Handling

### Database Errors
- `DatabaseError`: Base exception for all database errors
- `RecordNotFound`: Record doesn't exist
- `ValidationError`: Data validation failed
- `TransactionError`: Transaction-related issues

### Connection Errors
- `ConnectionError`: Unable to connect to database
- `TimeoutError`: Operation timed out

## Performance Considerations

1. **Lightweight Core**: Minimal dependencies (only Pydantic) ensure fast startup and low memory footprint
2. **Batch Operations**: Use `insert_many()` for bulk inserts
3. **Query Optimization**: Use `select()` to limit fields
4. **Connection Pooling**: Configure in backend settings
5. **Caching**: Relations cached by default, use `clear_relation_cache()`
6. **Direct Driver Access**: No ORM overhead, direct communication with database drivers

## Security Best Practices

1. **SQL Injection**: Always use parameterized queries
2. **Validation**: Use Pydantic validators
3. **Sensitive Data**: Never log connection passwords
4. **Transactions**: Use proper isolation levels

## Documentation

### Documentation Structure

The project includes comprehensive documentation in the `docs/` directory:

```
docs/
├── en_US/          # English documentation (authoritative)
│   ├── index.md
│   ├── quickstart.md
│   ├── api/
│   └── guides/
└── zh_CN/          # Chinese documentation (authoritative)
    ├── index.md
    ├── quickstart.md
    ├── api/
    └── guides/
```

### Important Notes on Documentation

- **Reference Status**: Documentation serves as reference material but may lag behind actual implementation
- **Implementation Priority**: Some code features are not documented until implementation is finalized and stable
- **Authoritative Versions**: English (en_US) and Chinese (zh_CN) are the maintained versions
- **When in Doubt**: Actual code and tests take precedence over documentation
- **Update Frequency**: Documentation updates follow stable releases rather than development changes

## Getting Help

1. **Check Tests**: Most features have test examples in `tests/` directory
2. **Review Interfaces**: Interfaces define expected behavior
3. **Backend README**: Each backend has specific documentation
4. **Type Hints**: Follow type hints for correct usage
5. **Documentation**: Consult `docs/en_US` or `docs/zh_CN` (may lag behind implementation)
6. **Testsuite Documentation**: Review planned testsuite architecture for future compatibility

## Next Steps

Review the specialized instruction documents in order:
1. Start with [ARCHITECTURE.md](./.claude/architecture.md) for system overview
2. Review [CODE_STYLE.md](./.claude/code_style.md) for coding standards
3. Study [TESTING.md](./.claude/testing.md) for the new testsuite architecture
4. Consult [BACKEND_DEVELOPMENT.md](./.claude/backend_development.md) for backend work
5. Reference [VERSION_CONTROL.md](./.claude/version_control.md) for releases