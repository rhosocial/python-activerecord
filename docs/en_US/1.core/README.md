# Core Concepts

This section covers the core concepts and components of RhoSocial ActiveRecord. We'll use a consistent set of examples throughout to demonstrate how these concepts work together.

## Example Domain Models

Throughout this documentation, we'll use two main example scenarios:

### Social Media Application

```python
User
 ├── id: int
 ├── username: str
 ├── email: str
 ├── created_at: datetime
 ├── posts: HasMany[Post]
 └── comments: HasMany[Comment]

Post
 ├── id: int
 ├── user_id: int
 ├── content: str
 ├── created_at: datetime
 ├── author: BelongsTo[User]
 └── comments: HasMany[Comment]

Comment
 ├── id: int
 ├── post_id: int
 ├── user_id: int
 ├── content: str
 ├── created_at: datetime
 ├── author: BelongsTo[User]
 └── post: BelongsTo[Post]
```

### E-Commerce System

```python
User
 ├── id: int
 ├── email: str
 ├── name: str
 └── orders: HasMany[Order]

Order
 ├── id: int
 ├── user_id: int
 ├── total: Decimal
 ├── status: str
 ├── created_at: datetime
 ├── user: BelongsTo[User]
 └── items: HasMany[OrderItem]

Product
 ├── id: int
 ├── name: str
 ├── price: Decimal
 ├── stock: int
 └── order_items: HasMany[OrderItem]

OrderItem
 ├── id: int
 ├── order_id: int
 ├── product_id: int
 ├── quantity: int
 ├── price: Decimal
 ├── order: BelongsTo[Order]
 └── product: BelongsTo[Product]
```

## Core Components

1. **Models**
   - Model definition and structure
   - Field types and validation
   - Model lifecycle events
   - Inheritance and mixins

2. **Fields**
   - Built-in field types
   - Custom field types
   - Field validation
   - Field options and constraints

3. **Relationships**
   - One-to-one (HasOne/BelongsTo)
   - One-to-many (HasMany)
   - Eager loading
   - Relationship queries

4. **Querying**
   - Basic CRUD operations
   - Query building
   - Conditions and filters
   - Sorting and pagination
   - Eager loading in queries

5. **Transactions**
   - Transaction management
   - Savepoints
   - Nested transactions
   - Error handling

## Organization

The core documentation is organized as follows:

- [Models](models.md): Understanding model definition and behavior
- [Fields](fields.md): Working with different field types
- [Field Mixins](field_mixins.md): Using pre-built field combinations
- [Field Validation](field_validation.md): Implementing validation rules
- [Custom Fields](custom_fields.md): Creating custom field types
- [Relationships](relationships.md): Managing model relationships
- [Basic Operations](basic_operations.md): Core CRUD operations
- [Querying](querying.md): Advanced query building

## Key Concepts

### Active Record Pattern

The Active Record pattern wraps database operations in object-oriented classes:
- Each class corresponds to a table
- Each instance corresponds to a row
- Properties map to columns

### Type Safety

RhoSocial ActiveRecord uses Pydantic for type safety:
- Type checking at runtime
- IDE support through type hints
- Validation during data assignment

### Data Consistency

The library ensures data consistency through:
- Transaction support
- Validation rules
- Event hooks
- Relationship integrity

## Next Steps

1. Start with [Models](models.md) to understand the foundation
2. Explore [Fields](fields.md) to learn about data types
3. Study [Relationships](relationships.md) for model connections
4. Master [Querying](querying.md) for data retrieval

Each section includes practical examples using our social media and e-commerce scenarios to demonstrate concepts in real-world contexts.