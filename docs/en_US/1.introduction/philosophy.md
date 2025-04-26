# Philosophy and Design Approach

## rhosocial ActiveRecord

rhosocial ActiveRecord follows the Active Record pattern, where:
- Each model class corresponds to a database table
- Each instance corresponds to a row in that table
- Model objects directly manage database operations through their methods

The library embraces a "convention over configuration" approach, using Pydantic for strong type validation, and
prioritizes an intuitive, model-centric API that feels natural in Python code. This Pydantic integration is a core
distinguishing feature enabling seamless interaction with other Pydantic-based systems.

rhosocial ActiveRecord also adopts a progressive approach to asynchronous programming, allowing developers to choose
between synchronous and asynchronous interfaces based on their application needs.

## SQLAlchemy

SQLAlchemy follows a more complex architecture with two distinct layers:
- Core: A SQL expression language providing direct SQL construction
- ORM: An optional layer that implements the Data Mapper pattern

SQLAlchemy emphasizes explicit configuration and flexibility, allowing fine-grained control over SQL generation
and execution. It separates database operations from model objects, making it more suitable for complex database
schemas and operations.

While SQLAlchemy offers asynchronous support in version 1.4 and above, it requires a somewhat different approach
compared to synchronous code, leading to potential inconsistencies in application design.

## Django ORM

As part of the Django web framework, Django ORM is designed to be:
- Tightly integrated with Django's other components
- Easy to use with minimal configuration
- Optimized for web application development patterns

Django ORM follows the Active Record pattern but makes specific design choices to complement Django's "batteries-included" philosophy.

Django has added limited asynchronous support in recent versions, but it's not as comprehensive as frameworks built
with async capabilities from the ground up.

## Peewee

Peewee is designed as a lightweight alternative, focusing on:
- Simplicity and a small footprint
- Minimal dependencies
- Easy-to-understand implementation

It follows the Active Record pattern similar to rhosocial ActiveRecord but with less focus on advanced features or
extensive type validation.

Peewee's asynchronous support is provided through a separate extension, peewee-async, requiring different patterns
when switching between sync and async modes.