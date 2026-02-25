# 4. Relationships

Relationships are the bridge connecting isolated data tables into a meaningful information network. This library uses explicit, type-safe descriptors to define relationships.

In the TechBlog system, we will build the following relationship network:
*   **User** <-> **Profile** (1:1)
*   **User** <-> **Post** (1:N)
*   **Post** <-> **Comment** (1:N)
*   **Post** <-> **Tag** (N:N, via PostTag intermediate table)

> 💡 **AI Prompt Example**: "I want to implement relationships between users, posts, comments, and tags in a blog system, how should I design it?"

## Table of Contents

*   **[Definitions (1:1, 1:N)](definitions.md)**: Defining `HasOne`, `BelongsTo`, `HasMany`.
*   **[Many-to-Many](many_to_many.md)**: Implementing complex N:N relationships via intermediate models.
*   **[Loading Strategies](loading.md)**: Solving the N+1 problem, mastering Eager Loading and Lazy Loading.

## Example Code

Full example code for this chapter can be found at `docs/examples/chapter_04_relationships/relationships.py`.

> 💡 **AI Prompt Example**: "How should relationships be properly used in real projects? Is there a complete example I can reference?"