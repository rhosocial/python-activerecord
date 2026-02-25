# 9. Backend System

This is an advanced topic for users who want to understand the internal workings of the ORM or need to support a new database.

## Backend Ecosystem

The design intent of `rhosocial-activerecord` is to support multiple database backends. In addition to the SQLite implementation included in the core library (where the asynchronous SQLite is primarily for testing verification), we also provide or plan to provide the following independent backend packages:

*   `rhosocial-activerecord-mysql`
*   `rhosocial-activerecord-postgres`
*   `rhosocial-activerecord-oracle` (Planned)
*   `rhosocial-activerecord-sqlserver` (Planned)
*   `rhosocial-activerecord-mariadb` (Planned)

These independent packages can also serve as examples for you to develop custom third-party backends.

## Contents

*   **[Expression System](expression/README.md)**: How Python objects are transformed into SQL strings.
*   **[Custom Backend](custom_backend.md)**: Implementing a new database driver.

## Example Code

Full example code for this chapter can be found at `docs/examples/chapter_07_backend/`.
