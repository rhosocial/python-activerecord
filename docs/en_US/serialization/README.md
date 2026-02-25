# Chapter 8: Serialization

rhosocial-activerecord fully leverages Pydantic V2's serialization capabilities, making conversion between models and formats like JSON or dictionaries extremely simple and type-safe.

## Contents

*   [JSON Serialization](json.md): Introduces how to convert models to JSON and dictionaries, and how to handle field filtering and related data.

## Core Features

*   **Pydantic Native**: Inherits directly from `BaseModel`, enjoying full Pydantic ecosystem support.
*   **Flexible Control**: Supports `include`, `exclude`, and other parameters for precise output control.
*   **Type Safe**: The serialization process follows strict type definitions.
