# Relationships in ActiveRecord

This section covers the various relationship types supported by rhosocial ActiveRecord and how to use them effectively in your applications.

## Contents

- [One-to-One Relationships](one_to_one_relationships.md) - Define and work with one-to-one relationships
- [One-to-Many Relationships](one_to_many_relationships.md) - Define and work with one-to-many relationships
- [Many-to-Many Relationships](many_to_many_relationships.md) - Define and work with many-to-many relationships
- [Polymorphic Relationships](polymorphic_relationships.md) - Define and work with polymorphic relationships
- [Self-referential Relationships](self_referential_relationships.md) - Define and work with self-referential relationships
- [Relationship Loading Strategies](relationship_loading_strategies.md) - Understand eager loading and lazy loading
- [Eager Loading and Lazy Loading](eager_and_lazy_loading.md) - Optimize performance with different loading strategies
- [Cross-database Relationships](cross_database_relationships.md) - Work with relationships across different databases

## Overview

Relationships in ActiveRecord represent associations between database tables, allowing you to work with related data in an object-oriented way. rhosocial ActiveRecord provides a rich set of relationship types and loading strategies to help you model complex data relationships efficiently.

The relationship system in rhosocial ActiveRecord is designed to be:

- **Type-safe**: Leveraging Python's type hints for better IDE support and runtime validation
- **Intuitive**: Using descriptive class attributes to define relationships
- **Efficient**: Supporting various loading strategies to optimize performance
- **Flexible**: Supporting complex relationship types including polymorphic and self-referential relationships

## Key Concepts

### Relationship Types

rhosocial ActiveRecord supports several relationship types:

- **BelongsTo**: Represents a many-to-one relationship where the current model contains a foreign key referencing another model
- **HasOne**: Represents a one-to-one relationship where another model contains a foreign key referencing the current model
- **HasMany**: Represents a one-to-many relationship where multiple records in another model contain foreign keys referencing the current model
- **Many-to-Many**: Represented through intermediate join tables, allowing many records in one model to be associated with many records in another model

### Relationship Loading

rhosocial ActiveRecord supports different strategies for loading related data:

- **Lazy Loading**: Related data is loaded only when explicitly accessed
- **Eager Loading**: Related data is loaded upfront in a single query or a minimal number of queries

Proper use of these loading strategies is crucial for application performance, especially when dealing with large datasets or complex relationship chains.