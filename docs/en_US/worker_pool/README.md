# 7. Worker Pool Module

`WorkerPool` is a standalone module that provides a resident worker process pool for parallel task execution. It uses `spawn` mode multiprocessing to ensure cross-platform consistency.

## Contents

*   **[Worker Pool Guide](worker_pool.md)**: Complete guide for using Worker Pool, including lifecycle hooks, management and statistics, best practices, and common pitfalls.

## Core Features

| Feature | Description |
|---------|-------------|
| **Spawn Mode** | Uses `spawn` context for cross-platform consistency |
| **Resident Workers** | Workers persist, avoiding repeated process startup overhead |
| **Crash Recovery** | Workers automatically restart after crashes |
| **Task Tracing** | Failed tasks can be tracked even if Worker crashes |
| **Future Pattern** | Supports timeout-based async result handling |
| **Graceful Shutdown** | Three-phase shutdown: DRAINING → STOPPING → KILLING → STOPPED |
| **Lifecycle Hooks** | Supports Worker-level and task-level hook functions |
| **Resource Monitoring** | Task execution time, memory delta, and other statistics |

## Difference from Connection Pool

| Feature | Worker Pool | Connection Pool |
|---------|-------------|-----------------|
| **Concurrency Level** | Process-level | Thread/coroutine-level |
| **Isolation** | Complete isolation (independent process space) | Shared process space |
| **Overhead** | High (IPC, memory, serialization) | Low (memory sharing) |
| **Use Cases** | CPU-intensive, tasks requiring isolation | I/O-intensive, database access |
| **ActiveRecord Integration** | Standalone module, no dependency | Deep integration, context-aware |

## Example Code

Complete example code for this chapter can be found at `docs/examples/chapter_07_worker_pool/`.
