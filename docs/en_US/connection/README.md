# Connection Management

This chapter covers how to manage database connections, from basic connection groups to advanced connection pooling.

## Table of Contents

* **[Connection Groups & Manager](connection_management.md)**: Using `BackendGroup` and `BackendManager` to manage multi-model, multi-database connections.
* **[Connection Pool](connection_pool.md)**: Efficient connection management with context-aware access patterns, connection reuse, lifecycle management, and ActiveRecord integration.

## Overview

### Connection Management Layers

```mermaid
graph TB
    subgraph Basic["Basic Layer"]
        CG["BackendGroup<br/>Single Group Models"]
        CM["BackendManager<br/>Multi-Group Models"]
    end

    subgraph Advanced["Advanced Layer"]
        BP["BackendPool<br/>Pooling & Context Awareness"]
    end

    subgraph Integration["Integration Layer"]
        AR["ActiveRecord Models"]
        CTX["Context Awareness"]
    end

    CG --> CM
    CM --> BP
    BP --> AR
    BP --> CTX

    style Basic fill:#e3f2fd,stroke:#1976d2
    style Advanced fill:#e8f5e9,stroke:#388e3c
    style Integration fill:#fff3e0,stroke:#f57c00
```

### Feature Comparison

| Feature | BackendGroup | BackendManager | BackendPool |
|---------|-----------------|-------------------|-------------|
| Multi-model Connection | ✓ | ✓ | ✓ |
| Multi-database | ✗ | ✓ | ✓ |
| Connection Reuse | ✗ | ✗ | ✓ |
| Context Awareness | ✗ | ✗ | ✓ |
| Transaction Management | ✗ | ✗ | ✓ |
| ActiveRecord Integration | Basic | Basic | Deep |

## Example Code

Complete example code for this chapter can be found at `docs/examples/chapter_06_connection/`.
