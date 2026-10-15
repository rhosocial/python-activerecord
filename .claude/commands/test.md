Run the full test suite for rhosocial-activerecord.

Before running tests, ensure PYTHONPATH is set (note the `tests` half — it makes
`providers/registry.py` importable; see .claude/testing.md §2):

```powershell
$env:PYTHONPATH="src;tests"   # Windows PowerShell 7
```

On Windows, prefer the wrapper, which resolves the virtualenv and sets PYTHONPATH for you:

```powershell
./scripts/dev.ps1 test              # serial (AGENTS.md iron rule 1)
./scripts/dev.ps1 test -Parallel    # opt-in, mirrors CI: -n auto --dist=loadgroup + plugin
./scripts/dev.ps1 collect           # import check only, no tests executed
```

Show the complete unfiltered output. Do not filter with grep or truncate with head/tail.
