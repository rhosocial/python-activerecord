# Static checking has to actually check

A checker that silently skips your code is worse than no checker, because it
lets a claim stand. Every rule here exists because something got past one.

## Ship the marker

`py.typed` (PEP 561) tells a checker the package carries inline annotations.
Without it the installed package is treated as untyped and **skipped
entirely** -- so the annotations are present but invisible to every consumer.
It also has to be declared as package data or it never reaches the wheel:

```toml
[tool.setuptools.package-data]
rhosocial = ["py.typed"]
```

## The configuration has to run

`[mypy] python_version = "3.8"` was set while the project's interpreter is
3.14, and mypy no longer accepts 3.8 -- so every run printed a configuration
error and the run continued far enough to look successful. A checker whose
configuration does not load is not a checker.

Verify the configuration actually loaded before believing any of its output:

```bash
mypy --version && mypy --show-config 2>&1 | head
```

## A class with `__getattr__` opts out of checking entirely

Nine value-expression classes forwarded unknown attributes to a wrapped node:

```python
def __getattr__(self, name):
    call = self.__dict__.get("call")
    if call is None:
        raise AttributeError(name)
    return getattr(call, name)
```

A checker reads `__getattr__` and stops. On those classes every attribute
looked valid, so the property the type system was supposed to provide -- a
wrong continuation caught on the line you wrote it -- was not being delivered
at all. Every experiment run against those classes had been passing for that
reason.

Do not add `__getattr__` to an expression class. If attribute forwarding is
genuinely needed, forward the specific attributes explicitly.

## Know what the checker cannot see

Syntax validity is not style, and neither is a partial rule set:

- Indentation inside brackets is not a syntax error, so `ast.parse` passes on a
  misindented base-class list. `ruff`'s `E1xx` rules are preview-only and do not
  cover bracket alignment either.
- The project's `select = ["E", "F", "B"]` does not include `E1`/`W1`. Running
  `ruff check <files>` proves less than it appears to.

When reporting that a check passed, say which rules ran and what they cover.

## Confirm the tool is looking at the right thing

Two failures of this kind, both mine:

- A scan that found nothing because its glob matched no files reports zero
  findings forever.
- A test that counts violations against a recorded baseline can be silenced by
  editing the baseline. Assert that the recorded number still corresponds to
  something real.

A check that has not been shown to fail on a known defect has not been shown
to work. Break the thing on purpose, watch the checker catch it, then put it
back.

## Run the directory, not the files you edited

The check that would have caught the last regression was not run, because the
edit was in a file and the error was in the argument that file passes to another:

```python
Case("macaddr8", lambda d: PostgresMacAddr8Type(d, type_name="..."), ...)
```

Every case raised `TypeError` on a keyword the type constructor does not take,
and all eleven PostgreSQL versions went red — including 18, which is far past
every version floor involved. That asymmetry is the tell: a version problem
cannot affect a server eight versions above the boundary it is about.

Two files were edited and two files were tested, so the failure lived in neither.
The tests that would have caught it were in the same directory.

A signature error has no version to it. When CI is red across every version at
once, suspect an argument or an import before suspecting a gate.
