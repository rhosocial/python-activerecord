# Chapter 3: Modeling Data

Models are the core of `rhosocial-activerecord`. They not only define the data structure but also encapsulate business logic, validation rules, and query capabilities.

This chapter details how to define powerful data models.

## Core Concepts

1.  **Powered by Pydantic**: Models are essentially Pydantic `BaseModel`s, giving you robust data validation and serialization capabilities.
2.  **Active Record Pattern**: Each model class corresponds to a database table, and each instance corresponds to a row.
3.  **Type Safety**: With `FieldProxy`, we achieve type-safe querying in Python, avoiding hardcoded strings.

## Chapter Contents

*   **[Fields & Proxies](fields.md)**
    *   How to define model fields
    *   Using `FieldProxy` for type-safe queries
    *   Mapping legacy database columns (`UseColumn`)
*   **[Mixins](mixins.md)**
    *   Using built-in Mixins (`UUIDMixin`, `TimestampMixin`)
    *   Creating custom Mixins for reusable logic
*   **[Validation & Hooks](validation.md)**
    *   Pydantic validators
    *   Lifecycle hooks (`before_save`, `after_create`, etc.)

## Example Code

Full example code for this chapter can be found at:
[docs/examples/chapter_03_modeling/basic_models.py](../../../examples/chapter_03_modeling/basic_models.py)
