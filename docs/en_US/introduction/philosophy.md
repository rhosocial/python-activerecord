# Philosophy

The design of `rhosocial-activerecord` is not just about providing a tool to manipulate databases; it is about establishing a rigorous, efficient, and flexible paradigm for data interaction in modern Python application development.

Our core design philosophy is reflected in the following three main aspects:

## 1. Layered Architecture: Backend and ActiveRecord

Traditional ORMs often tightly couple database connection management with model definitions. We explicitly distinguish between **Backend** and **ActiveRecord** in our design.

*   **Backend**: Responsible for low-level database connections, SQL execution, and dialect handling. It is a completely independent component that does not rely on any model definitions.
*   **ActiveRecord**: It is a "user" of the Backend. ActiveRecord utilizes the capabilities provided by the Backend to perform data persistence and querying.

This separation means that the **Backend can work completely independently**. You can use the Backend directly to execute raw SQL, manage transactions, or build custom data access layers without defining any Models. ActiveRecord is simply a high-level abstraction built upon this solid foundation.

Furthermore, **the Backend itself provides a powerful "Expression-Dialect" system**. This design allows us to easily extend support for mainstream relational databases. Currently, we provide the latest support for **SQLite3**, and plan to or already provide extensions for the following, committed to offering users a consistent development experience across different databases:

*   **MySQL**
*   **PostgreSQL**
*   **Oracle** (Planned)
*   **SQL Server** (Planned)
*   **MariaDB** (Planned)

## 2. Type Safety and Data Validation

We deeply understand the critical impact of good paradigms on system stability and development efficiency. Therefore, in the design of the data model layer, we made a key decision:

**Let ActiveRecord inherit directly from `pydantic.BaseModel` (Pydantic V2).**

We chose not to implement our own validation system for simple reasons:
*   **Maturity**: Pydantic is the de facto standard for data validation in the Python ecosystem, being extremely mature and powerful.
*   **Cost**: Implementing a validation system from scratch that matches Pydantic's level would be prohibitively expensive and prone to bugs.
*   **Ecosystem**: It allows direct integration with Pydantic's vast ecosystem (e.g., FastAPI integration, IDE intellisense).

Through this inheritance, every ActiveRecord model is essentially a Pydantic model, possessing powerful runtime type checking and data validation capabilities, ensuring the absolute purity of data entering the database.

## 3. Powerful Query System

ActiveRecord is not just about data models; it is paired with a powerful query system, primarily including:

*   **ActiveQuery**: The standard query builder.
*   **CTEQuery**: Common Table Expressions query.
*   **SetOperationQuery**: Set operation query (e.g., Union, Intersect).

**The core mission of ActiveQuery is to instantiate ActiveRecord instances (lists).** When you execute `User.query().where(...)`, it defaults to returning a list of fully validated `User` objects.

At the same time, to meet the needs of performance-sensitive scenarios, `ActiveQuery`, consistent with `CTEQuery` and `SetOperationQuery`, provides **`aggregate()`** functionality. This allows you to skip model instantiation when needed and directly retrieve aggregated data or raw dictionary results, achieving a perfect balance between flexibility and performance.
