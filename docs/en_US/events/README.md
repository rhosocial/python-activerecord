# 9. Events System

The event system in rhosocial-activerecord is a key mechanism for decoupling business logic. By listening to lifecycle events, you can add features such as logging, data validation, and association updates without modifying the core model logic.

## Contents

*   [Lifecycle Events](lifecycle.md): Details on all available hooks and their usage.

## Core Concepts

*   **ModelEvent**: Enum type defining all supported event points.
*   **Observer Pattern**: Based on the observer pattern, supporting multiple listeners.
*   **Mixin Friendly**: Designed to encourage composing behaviors via Mixins.

## Example Code

Complete example code for this chapter can be found at `docs/examples/chapter_09_events/`.

| File | Description |
|------|-------------|
| [01_lifecycle_hooks.py](../../examples/chapter_09_events/01_lifecycle_hooks.py) | Lifecycle hooks: before_save, after_save, before_delete, after_delete |
| [02_event_listeners.py](../../examples/chapter_09_events/02_event_listeners.py) | Event listeners: using on() method, multiple listeners, dynamic registration |
| [03_mixin_pattern.py](../../examples/chapter_09_events/03_mixin_pattern.py) | Mixin pattern: reusable event logic, combining multiple Mixins
