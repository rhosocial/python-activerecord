Run code linting with ruff

Run code linting and formatting checks for the project.

Execute the following commands:
1. `ruff check src/` — lint only. `[tool.ruff]` selects E/F/B at line-length 120.
2. Do NOT run `ruff format`. The project has no `[tool.ruff.format]` section, and
   formatting is owned by black (`[tool.black]`, line-length 100) plus isort
   (`profile = "black"`). `ruff format` would reformat at 120 and fight black.

On Windows, use the wrapper, which resolves the virtualenv and locates ruff:

```powershell
./scripts/dev.ps1 lint              # ruff check src
./scripts/dev.ps1 lint src tests    # explicit targets
./scripts/dev.ps1 fmt               # ruff check --fix
./scripts/dev.ps1 fmt --with-black --with-isort
./scripts/dev.ps1 type              # mypy src ([tool.mypy] pins python_version = 3.8)
```

`ruff`, `mypy`, `black` and `isort` are not installed by default; install them with
`uv tool install ruff mypy black isort` (or add to the virtualenv).

Show any violations and suggest fixes.
