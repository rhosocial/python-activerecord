# tests/rhosocial/activerecord_test/logging_module/test_quiet_defaults.py
"""The library is quiet by default and the application decides how loud it is.

These tests cover the two halves of that contract:

* importing ActiveRecord creates no stderr output and installs no handler;
* an application that sets a level (directly on the logger, or through its
    root configuration) keeps that decision, because library loggers propagate
    and do not overwrite an explicitly set level.
"""

import io
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from rhosocial.activerecord.logging import (
    LoggingConfig,
    configure_logging,
    get_logger,
    reset_default_logging_config,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


def unique_logger_name(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4()}"


@pytest.fixture(autouse=True)
def reset_logging():
    reset_default_logging_config()
    yield
    reset_default_logging_config()


class TestImportSilence:
    """Importing the library must not write to stderr."""

    def test_import_produces_no_stderr(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-c", "import rhosocial.activerecord"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr == ""

    def test_default_config_installs_no_handler(self):
        config = LoggingConfig()
        logger = config.get_logger(unique_logger_name("test.quiet_default"))

        assert logger.handlers == []
        assert logger.propagate is True
        # The quiet default is inherited instead of written to the logger.
        assert logger.level == logging.NOTSET

    def test_library_logger_keeps_default_level_implicit(self):
        root = logging.getLogger()
        namespace = logging.getLogger("rhosocial.activerecord")
        model_namespace = logging.getLogger("rhosocial.activerecord.model")
        original_root = root.level
        original_namespace = namespace.level
        original_model_namespace = model_namespace.level

        root.setLevel(logging.WARNING)
        namespace.setLevel(logging.NOTSET)
        model_namespace.setLevel(logging.NOTSET)
        try:
            logger = LoggingConfig().get_logger(
                unique_logger_name("rhosocial.activerecord.model")
            )

            assert logger.handlers == []
            assert logger.propagate is True
            # No explicit WARNING: the root logger's own default applies,
            # which is what lets an application change it later.
            assert logger.level == logging.NOTSET
            assert logger.getEffectiveLevel() == logging.WARNING
        finally:
            root.setLevel(original_root)
            namespace.setLevel(original_namespace)
            model_namespace.setLevel(original_model_namespace)


class TestDefaultLevel:
    """WARNING is the default; detail must be asked for."""

    def test_debug_and_info_are_suppressed(self):
        root = logging.getLogger()
        parent = logging.getLogger("test")
        original_root = root.level
        original_parent = parent.level

        logger = logging.getLogger(unique_logger_name("test.quiet_level"))
        logger.handlers.clear()
        logger.propagate = False

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        root.setLevel(logging.WARNING)
        parent.setLevel(logging.NOTSET)
        config = LoggingConfig()
        config.get_logger(logger.name)

        try:
            logger.debug("debug detail")
            logger.info("info detail")
            logger.warning("warning detail")

            output = stream.getvalue()
            assert "debug detail" not in output
            assert "info detail" not in output
            assert "warning detail" in output
        finally:
            logger.handlers.clear()
            root.setLevel(original_root)
            parent.setLevel(original_parent)

    def test_configure_logging_level_is_honoured(self, caplog):
        configure_logging(level=logging.DEBUG)

        logger = get_logger(unique_logger_name("test.quiet_configured"))
        with caplog.at_level(logging.DEBUG):
            logger.debug("enabled by application")

        assert "enabled by application" in caplog.text


class TestApplicationOwnership:
    """A decision the application made is not overwritten by the library."""

    def test_explicit_app_level_is_preserved(self):
        logger = logging.getLogger(unique_logger_name("rhosocial.activerecord.model"))
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        config = LoggingConfig(default_level=logging.DEBUG)
        configured = config.get_logger(logger.name)

        assert configured is logger
        assert configured.level == logging.INFO

    def test_application_namespace_level_is_inherited(self):
        namespace = logging.getLogger("rhosocial.activerecord")
        model_namespace = logging.getLogger("rhosocial.activerecord.model")
        original_namespace = namespace.level
        original_model_namespace = model_namespace.level

        namespace.setLevel(logging.DEBUG)
        model_namespace.setLevel(logging.NOTSET)
        try:
            logger = LoggingConfig().get_logger(
                unique_logger_name("rhosocial.activerecord.model")
            )

            assert logger.level == logging.NOTSET
            assert logger.getEffectiveLevel() == logging.DEBUG
        finally:
            namespace.setLevel(original_namespace)
            model_namespace.setLevel(original_model_namespace)

    def test_application_root_level_is_inherited(self):
        root = logging.getLogger()
        namespace = logging.getLogger("rhosocial.activerecord")
        model_namespace = logging.getLogger("rhosocial.activerecord.model")
        original_root = root.level
        original_namespace = namespace.level
        original_model_namespace = model_namespace.level

        root.setLevel(logging.INFO)
        namespace.setLevel(logging.NOTSET)
        model_namespace.setLevel(logging.NOTSET)
        try:
            logger = LoggingConfig().get_logger(
                unique_logger_name("rhosocial.activerecord.model")
            )

            assert logger.level == logging.NOTSET
            assert logger.getEffectiveLevel() == logging.INFO
        finally:
            root.setLevel(original_root)
            namespace.setLevel(original_namespace)
            model_namespace.setLevel(original_model_namespace)

    def test_root_handler_receives_propagated_records(self, caplog):
        configure_logging(level=logging.DEBUG, auto_setup=False)

        logger = get_logger(unique_logger_name("test.app_root"))
        with caplog.at_level(logging.DEBUG):
            logger.info("propagated to root")

        assert "propagated to root" in caplog.text

    def test_application_can_silence_library_loggers(self, caplog):
        configure_logging(level=logging.DEBUG, auto_setup=False)
        logger = get_logger(unique_logger_name("test.app_silence"))

        logger.setLevel(logging.CRITICAL)
        with caplog.at_level(logging.DEBUG):
            logger.debug("should not be seen")

        assert "should not be seen" not in caplog.text
