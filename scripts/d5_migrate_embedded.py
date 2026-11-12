# scripts/d5_migrate_embedded.py  (temporary; delete after the wave)
"""Rewrite declaration dunders inside embedded model-source strings.

The CLI tests generate model modules from a source string, so those
declarations are code inside a string and the AST sweep never sees them.
The rewrite is the same three-line method form, applied to the literal
statement text.
"""
import ast
import re
import sys
from pathlib import Path

MAP = {
    "__table_name__": "table_name",
    "__schema_name__": "schema_name",
    "__primary_key__": "primary_key",
    "__pk_auto_generated__": "pk_auto_generated",
    "__read_only__": "read_only",
}


def rewrite(path: Path) -> int:
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    changed = 0
    for dunder, method in MAP.items():
        pattern = re.compile(
            r"(?m)^(\s*)" + re.escape(dunder) + r"\s*=\s*(.*?)\s*$"
        )

        def repl(m: "re.Match") -> str:
            indent, value = m.group(1), m.group(2)
            return (
                f"{indent}@classmethod\n"
                f"{indent}def {method}(cls):\n"
                f"{indent}    return {value}"
            )

        text, n = pattern.subn(repl, text)
        changed += n
    if not changed:
        return 0
    if crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))
    return changed


def main() -> None:
    total = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        n = rewrite(p)
        if n:
            print(f"{p.as_posix()}: {n}")
            total += n
    print(f"rewrote {total} embedded declarations")


if __name__ == "__main__":
    main()
