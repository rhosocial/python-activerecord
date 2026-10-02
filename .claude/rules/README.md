# Rules

How this codebase is built, and what has been tried and rejected. Each file
stands alone; read the one that concerns the change in front of you.

| Rule | Covers |
|---|---|
| [expression-direction.md](expression-direction.md) | `expr -> format` and why the reverse direction is where injection and unreviewable inference live. What a factory signature may accept. |
| [column-and-result-types.md](column-and-result-types.md) | Designing column classes; the core / backend / user layering; stating a result type the source cannot settle, and why it is a mixin rather than a keyword. |
| [static-analysis.md](static-analysis.md) | Making a checker actually check: `py.typed`, a configuration that loads, and the defects that opt out of checking silently. |
| [anti-patterns.md](anti-patterns.md) | The catalogue, with what each one cost. Read this before adding a runtime lookup, a coercion helper, or a `__getattr__`. |

Two rules decide most of the rest:

1. **Information flows one way**, from a typed object to SQL text. A formatter
   needs an expression to have anything to format, so nothing may manufacture
   the expression it is about to render.
2. **A backend is entirely static.** An IDE and a type checker give a definite
   answer. Nothing is worked out at run time, and nothing is left for the
   caller to assert in a form a checker cannot read.
