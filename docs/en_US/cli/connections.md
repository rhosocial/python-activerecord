# Connections and model references

The CLI operates on model classes. It must import the class and obtain a
connection config and a backend class before any command runs.

## Model references

A model reference is `module:Class`, not `module.Class`:

```bash
rhosocial-activerecord dql list --model app.models:User
```

The CLI puts the current working directory and every `--path DIR` (repeatable)
on `sys.path` before importing the model. The class must be an `ActiveRecord` or
`AsyncActiveRecord` subclass; anything else is rejected with a clear message.

## Backend and connection

The core package keeps no registry of backends, so name the classes your project
actually uses:

| Flag | Meaning |
|------|---------|
| `--backend-class MODULE:CLASS` | Backend class; for an async model it must be an `AsyncStorageBackend` subclass |
| `--config-class MODULE:CLASS` | Connection config class |
| `--config KEY=VALUE` | Set a config field; may be repeated |
| `--connection MODULE:CALLABLE` | Named connection callable returning a `ConnectionConfig` |

Each half resolves independently:

- **Backend class**: `--backend-class`, otherwise the model's own `configure()`.
- **Connection config**: `--connection`, or `--config-class` with `--config`
  values, otherwise the model's own `configure()`.

So a named connection may supply credentials while the model module supplies the
backend class, or the reverse.

`--connection` and `--config-class` are mutually exclusive. `--config` values
override the resolved config in all three paths (named connection, config class,
model configuration). Unknown keys and `options.KEY` entries go into
`config.options`. Values are coerced to the config field's type: `true`/`yes`/
`1`/`on` for booleans, integers, floats, otherwise strings.

```bash
# Model module does not call configure(): pass both halves
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --config-class rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig \
  --config database=app.db -o json

# Named connection plus an explicit backend class
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class mypkg.backend:MyBackend \
  --connection app.connections:prod_db -o json
```

If the model module calls `configure()`, `--backend-class` and `--connection` /
`--config-class` may be omitted; any `--config` values then override the model's
existing configuration.

## Async models

The CLI detects the model type automatically. `ActiveRecord` uses the synchronous
backend; `AsyncActiveRecord` uses the asynchronous backend and an event loop
inside the CLI. There is no `--async` flag, but `--backend-class` must name a
class that matches the model: an `AsyncStorageBackend` subclass for an
asynchronous model, a `StorageBackend` subclass otherwise.

## Python module form

```bash
python -m rhosocial.activerecord.cli dql list --model app.models:User -o json
```

The installed console script (`rhosocial-activerecord`) is the same entry point.
The backend-specific command (for example `rhosocial-activerecord-sqlite`) is a
different tool that executes SQL and introspects the database; it does not know
about model classes.

## Using these commands from an AI agent

- Do not guess backend or config class paths. Read them from the project's
  settings, or ask the user; a wrong path exits 4 with `Cannot import ...`.
- When the model module already calls `configure()`, pass only `--model` and let
  the model supply the connection.
- `--path` is repeatable and is the supported way to point the CLI at a source
  tree without installing it.
- The model class must be a real `ActiveRecord` / `AsyncActiveRecord` subclass;
  a module-level function or a plain Pydantic model is rejected.
- Use `python -m rhosocial.activerecord.cli` when the console script is not on
  `PATH`.
