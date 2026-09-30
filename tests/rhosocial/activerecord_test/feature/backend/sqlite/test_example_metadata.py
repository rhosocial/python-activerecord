# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_example_metadata.py
"""``examples/conftest.py`` must describe every example that exists.

The metadata is what makes an example discoverable to the tooling that reads
this directory, so an unregistered example is not merely undocumented -- it is
invisible. The tree already drifted once: 18 of the 53 example modules carried no
entry at all, every one of them in the named-* families, which is exactly where a
reader would go looking.

Both directions are checked, because the failure mode is not one-sided. A key
with no file behind it advertises an example that cannot be run, and a file with
no key hides one that can.
"""

import ast
import importlib.util
import pathlib

import pytest

def _repo_root():
    """Walk up to the directory holding the project pyproject.toml.

    Preferred over a fixed ``parents[n]``: the index shifts whenever a level is
    inserted, and fails silently by pointing at a sibling path.
    """
    for candidate in pathlib.Path(__file__).resolve().parents:
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file() and "[tool.pytest.ini_options]" in pyproject.read_text(
            encoding="utf-8"
        ):
            return candidate
    raise AssertionError("could not locate the repository root from this test file")


EXAMPLES_DIR = _repo_root() / "src/rhosocial/activerecord/backend/impl/sqlite/examples"

# Infrastructure, not examples: package markers, the metadata file itself, and the
# run_* drivers (which execute other examples rather than being one).
NOT_EXAMPLES = {"__init__.py", "conftest.py"}


def _load_meta():
    spec = importlib.util.spec_from_file_location(
        "sqlite_examples_conftest", EXAMPLES_DIR / "conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EXAMPLES_META


def _example_files():
    return sorted(
        str(path.relative_to(EXAMPLES_DIR))
        for path in EXAMPLES_DIR.rglob("*.py")
        if "__pycache__" not in path.parts
        and path.name not in NOT_EXAMPLES
        and not path.name.startswith("run_")
    )


EXAMPLES_META = _load_meta()
ON_DISK = _example_files()


def test_examples_directory_exists():
    """Guard the path arithmetic above; a bad parent would vacuously pass."""
    assert EXAMPLES_DIR.is_dir(), f"examples dir not found at {EXAMPLES_DIR}"
    assert ON_DISK, "no example files discovered -- discovery is broken"


@pytest.mark.parametrize("relative_path", ON_DISK)
def test_every_example_is_registered(relative_path):
    assert relative_path in EXAMPLES_META, (
        f"{relative_path} has no EXAMPLES_META entry, so metadata-driven tooling "
        f"cannot see it"
    )


@pytest.mark.parametrize("key", sorted(EXAMPLES_META))
def test_every_registration_points_at_a_real_file(key):
    assert (EXAMPLES_DIR / key).is_file(), (
        f"EXAMPLES_META registers {key}, which does not exist"
    )


@pytest.mark.parametrize("key", sorted(EXAMPLES_META))
def test_registration_has_the_expected_shape(key):
    entry = EXAMPLES_META[key]
    assert set(entry) == {"title", "dialect_protocols", "priority"}, (
        f"{key} has keys {sorted(entry)}; the inspector reads "
        f"title/dialect_protocols/priority"
    )
    assert entry["title"].strip(), f"{key} has an empty title"
    assert isinstance(entry["dialect_protocols"], list), f"{key}: not a list"
    assert isinstance(entry["priority"], int), f"{key}: priority is not an int"


@pytest.mark.parametrize("key", sorted(EXAMPLES_META))
def test_dialect_protocols_name_real_protocols(key):
    """A protocol name that does not exist is worse than none.

    Nothing in the tree validates these strings, so a typo -- ``JSONSuport`` --
    would pass as a requirement the example does not actually have, or fail a
    filter in whatever tooling consumes the metadata.
    """
    from rhosocial.activerecord.backend.dialect import protocols

    for name in EXAMPLES_META[key]["dialect_protocols"]:
        assert hasattr(protocols, name), (
            f"{key} requires dialect protocol {name!r}, which is not defined in "
            f"rhosocial.activerecord.backend.dialect.protocols"
        )


def test_conftest_parses():
    """The metadata file is read by path, not imported as a package module.

    Importing it normally would work too, but a syntax error would then surface
    as a collection error with no indication which file caused it.
    """
    ast.parse((EXAMPLES_DIR / "conftest.py").read_text(encoding="utf-8"))
