# Scenarios

Integrating `rhosocial-activerecord` into modern Web frameworks and using it correctly in complex concurrent scenarios.

## Contents

*   **[FastAPI Integration](fastapi.md)**: Async, connection-pool isolation, derived DDL, logging, and Prometheus metrics.
*   **[GraphQL Integration](graphql.md)**: Solving the N+1 problem and building efficient APIs.
*   **[Parallel Worker Patterns](parallel_workers.md)**: Multi-process and async patterns for parallel processing.

## Example Code

Full example code for this chapter can be found at `docs/examples/chapter_14_scenarios/`.

| Directory          | Contents                                      |
|--------------------|-----------------------------------------------|
| `fastapi_blog/`    | FastAPI blog REST API (pool + logging + metrics) |
| `graphql_fastapi/` | GraphQL + FastAPI integration example         |
