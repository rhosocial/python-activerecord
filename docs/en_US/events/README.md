# Chapter 7: Events

The event system in rhosocial-activerecord is a key mechanism for decoupling business logic. By listening to lifecycle events, you can add features such as logging, data validation, and association updates without modifying the core model logic.

## Contents

*   [Lifecycle Events](lifecycle.md): Details on all available hooks and their usage.

## Core Concepts

*   **ModelEvent**: Enum type defining all supported event points.
*   **Observer Pattern**: Based on the observer pattern, supporting multiple listeners.
*   **Mixin Friendly**: Designed to encourage composing behaviors via Mixins.
