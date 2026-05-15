# Knowledge Base Instructions - RhoSocial ActiveRecord

## Overview

This document provides comprehensive instructions for understanding and working with the **rhosocial-activerecord** ecosystem. The project implements a modern, Pythonic ActiveRecord pattern with type safety and rich features.

**Key Differentiator**: This is a standalone ActiveRecord implementation built from scratch with **only Pydantic as a dependency** - no reliance on existing ORMs like SQLAlchemy or Django ORM. All database interaction logic is implemented directly through a clean backend abstraction layer.

## Quick Reference

- **Primary Project**: rhosocial-activerecord (core implementation)
- **Extension Projects**: rhosocial-activerecord-mysql, rhosocial-activerecord-postgres, etc.
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

### Module Hierarchy

