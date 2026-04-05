# Competitor Analysis

This section provides detailed comparisons between rhosocial-activerecord and mainstream Python ORM frameworks to help developers choose the right tool.

## Documents

- [Competitive Advantages Summary](./summary.md) — Quick selection guide
- [vs SQLAlchemy](./sqlalchemy.md) — Comparison with the Data Mapper pattern representative
- [vs Django ORM](./django_orm.md) — Comparison with framework-bound ORM
- [vs SQLModel](./sqlmodel.md) — Comparison with Pydantic+SQLAlchemy hybrid solution
- [vs Peewee](./peewee.md) — Comparison with lightweight ActiveRecord
- [vs Tortoise ORM](./tortoise_orm.md) — Comparison with async-first ORM

## Quick Comparison

| Framework | Design Pattern | Key Features | Use Cases |
|-----------|---------------|--------------|-----------|
| **SQLAlchemy** | Data Mapper | Enterprise-grade, feature-complete, steep learning curve | Large enterprise applications |
| **Django ORM** | ActiveRecord | Tightly integrated with Django, mature and stable | Django projects |
| **SQLModel** | Hybrid | Pydantic + SQLAlchemy | FastAPI + SQLAlchemy users |
| **Peewee** | ActiveRecord | Lightweight, self-contained | Small projects |
| **Tortoise ORM** | ActiveRecord | Async-first, Django-style | Pure async projects |
| **rhosocial-activerecord** | ActiveRecord | Native Pydantic, sync-async parity | Modern Python projects |
