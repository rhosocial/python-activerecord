# Experimental Features Guide

## 1. Overview

This document defines the rules, lifecycle, and usage guidelines for "Experimental" features within the `rhosocial-activerecord` project. Experimental features are intended to provide a way to test new ideas and gather feedback in real-world environments without immediately committing to a stable API.

**Core Principle**: Experimental features are **not** suitable for production environments. Their API may undergo incompatible changes in any version (including patch versions) or even be removed entirely.

## 2. What are Experimental Features?

The following types of changes may be marked as experimental:

*   **New APIs or Modules**: Introducing entirely new functionalities whose design is not yet fully stable.
*   **Major Refactoring**: Significant changes to the underlying implementation of existing stable features, which might affect performance or behavior.
*   **Performance Optimizations**: Introducing performance improvements that may have edge cases.
*   **Integration with Third-Party Libraries**: Integration with new or unstable external libraries.
*   **Controversial Designs**: Design decisions that require validation of their value and usability in real-world scenarios.

## 3. Implementation Guidelines

All experimental code and features must adhere to the following rules.

### 3.1 Code Location

All experimental code should be placed under a dedicated `experimental` submodule.

*   **Core Package**: `src/rhosocial/activerecord/experimental/`
*   **Backend Package**: `src/rhosocial/activerecord/backend/impl/{backend}/experimental/`

This ensures that experimental code is physically isolated from stable code.

### 3.2 `@experimental` Decorator

All experimental features (classes, functions, or methods) **must** be marked with the `@experimental` decorator.

**Decorator Implementation**:

```python
# src/rhosocial/activerecord/experimental/decorator.py
import warnings
from functools import wraps

def experimental(thing):
    """
    Decorator to mark a function, method, or class as experimental.
    """
    @wraps(thing)
    def wrapper(*args, #, **kwargs): # Original mistake was here: #, **kwargs)
        warnings.warn(
            f"{thing.__name__} is an experimental feature. "
            "Its API may change or be removed in future releases without notice. "
            "Do not use in production.",
            FutureWarning,
            stacklevel=2
        )
        return thing(*args, **kwargs)
    return wrapper
```

**Usage Example**:

```python
from rhosocial.activerecord.experimental.decorator import experimental

@experimental
class AsyncQueryBuilder:
    """
    An experimental asynchronous query builder.
    
    .. warning::
       This class is experimental and should not be used in production.
    """
    # ... implementation ...
```

### 3.3 Documentation Requirements

*   **Docstrings**: The docstrings for all experimental features **must** begin with a clear warning stating that they are experimental.
*   **Project Documentation**: In the project's main documentation, experimental features should be described in a separate "Experimental" section and clearly labeled with their instability.

## 4. Lifecycle of Experimental Features

### 4.1 Introduction

*   New features are introduced through a standard PR process, but targeting the `experimental` module.
*   The PR description must state that the feature is experimental and explain its design goals.

### 4.2 Iteration & Feedback

*   During the experimental phase, the API may undergo **arbitrary breaking changes** based on feedback.
*   Users are encouraged to provide feedback via GitHub Issues, prefixed with `[Experimental]` in the title.
*   Significant adjustments to experimental features may occur between `dev`, `alpha`, or `beta` versions.

### 4.3 Graduation

For an experimental feature to become stable, all the following conditions must be met:

1.  **API Stability**: The API design has proven robust and has not undergone significant changes for at least one `beta` version cycle.
2.  **Sufficient Testing**:
    *   Code coverage meets or exceeds project standards (>90%).
    *   Includes comprehensive unit tests and integration tests.
    *   If applicable, also includes performance benchmarks.
3.  **Complete Documentation**: Provides clear, complete user documentation and API reference.
4.  **Community Validation**: Has received sufficient positive feedback, proving the feature is valuable and well-designed.

**Graduation Process**:

*   Submit a new PR to move the code from the `experimental` module to a stable module.
*   Remove the `@experimental` decorator.
*   Update all relevant documentation to remove experimental warnings.
*   This change should be released in the next **MINOR** version.

### 4.4 Removal

If an experimental feature proves unsuccessful (e.g., poor design, unused, better alternatives available), it can be removed directly.

*   **Notification**: The decision to remove will be discussed in the relevant GitHub Issue.
*   **Removal Version**: Can be removed in any **MINOR** or **MAJOR** version.
*   **No Deprecation Period**: Experimental features do not enjoy a standard deprecation cycle.

## 5. User Guidelines

### 5.1 Production Environment

**It is strongly recommended not to use experimental features in production environments.** If you choose to do so, you must accept the following risks:

*   Features may be changed or removed without warning.
*   Undiscovered critical bugs may exist.
*   Upgrading to new versions may cause your application to crash.

### 5.2 Providing Feedback

Your feedback on experimental features is highly welcomed and needed. Please:

*   Create new issues on GitHub to share your experiences.
*   Include the `[Experimental]` tag in the title.
*   Describe your use case, problems encountered, and suggestions for improvement in detail.

### 5.3 Version Locking

If you use experimental features from this library in your project (even an experimental one), it is **strongly recommended** to **precisely lock** the version of `rhosocial-activerecord`.

**Example (`pyproject.toml`)**:

```toml
[project]
dependencies = [
    "rhosocial-activerecord == 1.2.0a1"  # Precisely lock the version
]
```

This prevents unexpected breakage in your code due to patch or minor version upgrades.