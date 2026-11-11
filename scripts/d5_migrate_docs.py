# scripts/d5_migrate_docs.py
"""Rewrite declaration examples in Markdown: dunder assignment -> method override.

Only the *assignment* form is rewritten (``__table_name__ = "x"`` inside a
code block). Prose that merely mentions a dunder name is left alone: those
sentences need a human decision, and the rules doc already states the
policy they should be read against.
"""
import re
import sys
from pathlib import Path

MAP = {
    "__table_name__": "table_name",
    "__schema_name__": "schema_name",
    "__primary_key__": "primary_key",
    "__pk_auto_generated__": "pk_auto_generated",
    "__deleted_at_field__": "deleted_at_field",
    "__created_at_field__": "created_at_field",
    "__updated_at_field__": "updated_at_field",
    "__version_field__": "version_field",
    "__version_increment_by__": "version_increment_by",
    "__read_only__": "read_only",
}


def convert(path: Path, dry: bool) -> int:
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    lines = text.split("\n")
    pending = {}
    for dunder in MAP:
        pattern = re.compile(
            r"(?m)^(\s*)" + re.escape(dunder) + r"\s*=\s*(.*?)\s*$"
        )
        for index, line in enumerate(lines):
            if index in pending:
                continue
            match = pattern.match(line)
            if match:
                pending[index] = (match.group(1), match.group(2), MAP[dunder])

    if not pending:
        return 0
    out = []
    for index, line in enumerate(lines):
        if index not in pending:
            out.append(line)
            continue
        indent, value, method = pending[index]
        out.append(f"{indent}@classmethod")
        out.append(f"{indent}def {method}(cls):")
        out.append(f"{indent}    return {value}")
        nxt = lines[index + 1] if index + 1 < len(lines) else ""
        if nxt.strip():
            out.append("")
    if not dry:
        text = "\n".join(out)
        if crlf:
            text = text.replace("\n", "\r\n")
        path.write_bytes(text.encode("utf-8"))
    return len(pending)


def main() -> None:
    dry = "--dry" in sys.argv
    roots = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = total = 0
    for root in roots:
        for path in sorted(Path(root).rglob("*.md")):
            count = convert(path, dry)
            if count:
                files += 1
                total += count
                if dry:
                    print(f"{path.as_posix()}: {count}")
    print(f"{'would rewrite' if dry else 'rewrote'} {total} examples in {files} files")


if __name__ == "__main__":
    main()
