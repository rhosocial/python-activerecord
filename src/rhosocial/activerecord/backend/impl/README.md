# Backend Implementation Directory

This directory contains the specific storage backend implementations for ActiveRecord. Each implementation is organized in its own subdirectory with a lowercase name (e.g., `sqlite`).

## Purpose

- All database-related implementations from optional packages are placed in this directory
- Each backend implementation should be stored in its own subdirectory
- The subdirectory name should be lowercase and match the backend name

## Creating Custom Backends

If you want to implement your own storage backend, you should follow the implementation pattern of `sqlite` as a reference. Your custom implementation should:

1. Be placed in its own subdirectory with a lowercase name
2. Follow the same structure and interface patterns as the existing implementations
3. Implement all required methods and classes to ensure compatibility with the ActiveRecord framework

## Existing Implementations

Currently, you can refer to the `sqlite` implementation as a guide for creating new backend implementations.