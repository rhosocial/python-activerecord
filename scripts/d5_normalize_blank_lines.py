# scripts/d5_normalize_blank_lines.py  (temporary; delete after the wave)
"""Collapse runs of 3+ blank lines left by the declaration sweep."""
import sys
from pathlib import Path

def normalize(path: Path) -> int:
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")
    out = []
    blank = 0
    changed = 0
    for line in lines:
        if line.strip() == "":
            blank += 1
            if blank >= 3:
                changed += 1
                continue
        else:
            blank = 0
        out.append(line)
    if changed:
        text = "\n".join(out)
        if crlf:
            text = text.replace("\n", "\r\n")
        path.write_bytes(text.encode("utf-8"))
    return changed

def main() -> None:
    total = files = 0
    for arg in sys.argv[1:]:
        for path in sorted(Path(arg).rglob("*.py")):
            if "__pycache__" in path.as_posix():
                continue
            n = normalize(path)
            if n:
                files += 1
                total += n
    print(f"collapsed {total} blank lines in {files} files")

if __name__ == "__main__":
    main()
