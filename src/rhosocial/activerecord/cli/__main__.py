# src/rhosocial/activerecord/cli/__main__.py
"""Allow ``python -m rhosocial.activerecord.cli``."""

from . import main

if __name__ == "__main__":
    raise SystemExit(main())
