# 竞争对手分析

本章节提供 rhosocial-activerecord 与主流 Python ORM 框架的详细对比分析，帮助开发者选择适合的工具。

## 文档列表

- [竞争优势总结](./summary.md) — 快速选择指南
- [vs SQLAlchemy](./sqlalchemy.md) — 与 Data Mapper 模式代表对比
- [vs Django ORM](./django_orm.md) — 与框架绑定 ORM 对比
- [vs SQLModel](./sqlmodel.md) — 与 Pydantic+SQLAlchemy 混合方案对比
- [vs Peewee](./peewee.md) — 与轻量级 ActiveRecord 对比
- [vs Tortoise ORM](./tortoise_orm.md) — 与异步优先 ORM 对比

## 快速对比

| 框架 | 设计模式 | 核心特点 | 适用场景 |
|------|----------|----------|----------|
| **SQLAlchemy** | Data Mapper | 企业级、功能完整、学习曲线陡 | 大型企业应用 |
| **Django ORM** | ActiveRecord | Django 紧密集成、成熟稳定 | Django 项目 |
| **SQLModel** | 混合 | Pydantic + SQLAlchemy | FastAPI + SQLAlchemy 用户 |
| **Peewee** | ActiveRecord | 轻量、自包含 | 小型项目 |
| **Tortoise ORM** | ActiveRecord | 异步优先、Django 风格 | 纯异步项目 |
| **rhosocial-activerecord** | ActiveRecord | Pydantic 原生、同步异步对等 | 现代 Python 项目 |
