# When to Choose Each ORM

## When to Choose rhosocial ActiveRecord
- When you need strong type validation and data conversion
- When you're using FastAPI or other Pydantic-based frameworks
- When you want an intuitive model API and clean code structure
- When you need complex aggregation capabilities but want a more intuitive API
- When you want to use both synchronous and asynchronous code
- When you prefer the ActiveRecord pattern and are familiar with Ruby on Rails or Yii2

## When to Choose SQLAlchemy
- When you need maximum flexibility and control over database operations
- When your application relies on complex queries and optimizations
- When you need to integrate with many specialized database dialects
- When you prefer the Data Mapper pattern
- When you need enterprise-grade features at scale and can accept the complexity

## When to Choose Django ORM
- When you're building a full Django application
- When you need rapid web application development
- When you want built-in admin interface and form functionality
- When you value a comprehensive "batteries-included" approach
- When you don't need complex database operations

## When to Choose Peewee
- When you need a lightweight ORM with minimal dependencies
- When you're working in resource-constrained environments
- When you prefer simplicity over a comprehensive feature set
- When building small to medium applications
- When you need very low memory footprint