"""Conftest for CRUD benchmark bridge tests."""

from rhosocial.activerecord.testsuite.benchmark.conftest import (  # noqa: F401
    benchmark_size,
)
from rhosocial.activerecord.testsuite.benchmark.crud.conftest import (  # noqa: F401
    crud_sync_context,
    crud_async_context,
)


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--benchmark-size",
            action="store",
            default="small",
            choices=("small", "medium", "large"),
            help="Data size for rhosocial benchmark scenarios.",
        )
    except ValueError:
        pass
