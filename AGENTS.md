# rhosocial-activerecord - AI Agent Instructions

This document provides comprehensive instructions for AI agents working on the **rhosocial-activerecord** project.

## Project Overview

**rhosocial-activerecord** is a pure Python ActiveRecord implementation built from scratch with **only Pydantic as a dependency** - no reliance on existing ORMs like SQLAlchemy or Django ORM.

### Key Characteristics
- Standalone ActiveRecord implementation (no ORM dependencies)
- Sync/Async dual API design with strict parity
- Expression-Dialect separation architecture
- Protocol-based design for feature detection
- Namespace package architecture for extensibility

## External Configuration Loading

CRITICAL: When you encounter references to files in `.opencode/` directory, use your Read tool to load them on a need-to-know basis. They're relevant to the SPECIFIC task at hand.

### Instructions:
- Do NOT preemptively load all references - use lazy loading based on actual need
- When loaded, treat content as mandatory instructions that override defaults
- Follow references recursively when needed

## Required Reading

Read the following files immediately as they're relevant to all workflows:

### Core Configuration (@.opencode/project.yml)
Contains project metadata, architecture principles, and validation rules.
- Python version requirements (3.8+)
- Core dependencies (Pydantic 2.x only)
- Mandatory rules (file headers, sync/async parity, line width)
- Forbidden rules (no ORM imports, no direct SQL concatenation)

### Context & Architecture (@.opencode/context.md)
Comprehensive project context including:
- Core architecture overview
- Expression-Dialect separation (most critical)
- Sync/Async parity rules
- Testing parity requirements
- Code modification checklist
- Common issue resolution
- Key file quick reference

## Workflow Commands

For development workflows, refer to:
- **Commands** (@.opencode/commands.yml): Available shortcuts like `/test`, `/lint`, `/new-feature`
- **Hints** (@.opencode/hints.yml): Smart suggestions triggered by keywords

## Pattern Recognition

For automatic file type recognition and associations:
- **Discovery** (@.opencode/discovery.yml): Patterns for backend implementations, expression components, test categories

## Code Templates

When creating new files, use templates from `.opencode/templates/`:
- `new_mixin.py` - Create new mixins
- `new_backend.py` - Create new database backends
- `new_field.py` - Create new field types
- `new_test.py` - Create new test cases

## Quick Reference

### Sync/Async Parity Rules (CRITICAL)
1. **Class names**: Add `Async` prefix for async versions
   - `BaseActiveRecord` → `AsyncBaseActiveRecord`
2. **Method names**: Remain IDENTICAL (no `_async` suffix)
   - `def save(self)` → `async def save(self)`
3. **Docstrings**: Async version notes "asynchronously" in first sentence
4. **Field order**: Declaration order must match
5. **Testing parity**: Fixtures, test classes, and schema sharing

### Mandatory Rules
- Every .py file must start with path comment: `# src/path/to/file.py`
- Line width must not exceed 100 characters
- Type annotations use Python 3.8+ compatible syntax
- Expression classes must never concatenate SQL strings directly

### Quick Commands
- `/test` - Run all tests (auto-sets PYTHONPATH=src)
- `/test-feature query` - Run query feature tests
- `/lint` - Run code linting
- `/new-feature` - Create new feature wizard

## Knowledge Base

For detailed architectural documentation, refer to `.claude/` directory:
- `.claude/architecture.md` - System architecture
- `.claude/code_style.md` - Coding standards
- `.claude/testing.md` - Testing architecture
- `.claude/version_control.md` - Version management
- `.claude/backend_development.md` - Backend development guide

## Getting Help

1. Check tests in `tests/` directory for usage examples
2. Review interfaces in `src/rhosocial/activerecord/interface/`
3. Follow type hints for correct usage
4. When in doubt, actual code and tests take precedence over documentation
