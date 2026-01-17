# Comparison

Choosing an ORM is a major decision. Here is how `rhosocial-activerecord` compares to other popular Python ORMs.

| Feature | rhosocial-activerecord | SQLModel | SQLAlchemy | Django ORM |
| :--- | :--- | :--- | :--- | :--- |
| **Pattern** | Active Record | Data Mapper / Hybrid | Data Mapper | Active Record |
| **Validation** | Pydantic V2 (Native) | Pydantic V1/V2 | Optional / External | Internal System |
| **Type Safety** | High (Field Proxies) | High | High (2.0+) | Medium |
| **Zero-IO Testing** | **Yes (Native)** | No | No | No |
| **Performance** | Adjustable (Strict <-> Raw) | Medium | High | Low/Medium |
| **Learning Curve** | Low | Low | High | Medium |

## vs SQLModel
**SQLModel** is a fantastic library that inspired many modern Python ORMs. It attempts to unify Pydantic and SQLAlchemy.
*   **The Difference**: SQLModel inherits from both Pydantic and SQLAlchemy models, which can sometimes lead to "metaclass conflicts" and complex MRO (Method Resolution Order) issues. `rhosocial-activerecord` keeps things simpler: it *is* Pydantic, and it *uses* a custom backend system, avoiding the complexity of SQLAlchemy's session management for simple tasks.
*   **Choose `rhosocial` if**: You want a purer Active Record experience without the weight of SQLAlchemy.

## vs SQLAlchemy
**SQLAlchemy** is the industrial-strength standard for Python database access. It follows the Data Mapper pattern (DB tables mapped to classes, but decoupled).
*   **The Difference**: SQLAlchemy is incredibly powerful but has a steep learning curve. You need to understand Sessions, Engines, Metadata, and the Unit of Work pattern. `rhosocial-activerecord` abstracts this away. You call `save()`, and it saves.
*   **Choose `rhosocial` if**: You want to move fast and don't need the extreme flexibility of Data Mapper.

## vs Django ORM
**Django ORM** is the most famous Active Record implementation in Python.
*   **The Difference**: Django ORM is tightly coupled to the Django framework. You can't easily use it with FastAPI or Flask without dragging in the rest of Django. It also uses its own validation system, not Pydantic.
*   **Choose `rhosocial` if**: You are building a modern async app (e.g., FastAPI) and want Pydantic validation, or if you want a standalone ORM for scripts and tools.
