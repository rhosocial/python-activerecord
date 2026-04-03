# 9. Serialization

rhosocial-activerecord fully leverages Pydantic V2's serialization capabilities, making conversion between models and formats like JSON or dictionaries extremely simple and type-safe.

## Contents

*   [JSON Serialization](json.md): Introduces how to convert models to JSON and dictionaries, and how to handle field filtering and related data.

## Core Features

*   **Pydantic Native**: Inherits directly from `BaseModel`, enjoying full Pydantic ecosystem support.
*   **Flexible Control**: Supports `include`, `exclude`, and other parameters for precise output control.
*   **Type Safe**: The serialization process follows strict type definitions.

## Example Code

Complete example code for this chapter can be found at `docs/examples/chapter_09_serialization/`.

| File | Description |
|------|-------------|
| [01_basic_serialization.py](../../examples/chapter_09_serialization/01_basic_serialization.py) | Basic serialization: model_dump(), model_dump_json(), field types |
| [02_field_filtering.py](../../examples/chapter_09_serialization/02_field_filtering.py) | Field filtering: exclude, include, nested filtering, context-aware |
| [03_related_data.py](../../examples/chapter_09_serialization/03_related_data.py) | Related data: serializing relationships, computed_field, nested patterns
