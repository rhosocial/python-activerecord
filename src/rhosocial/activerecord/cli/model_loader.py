# src/rhosocial/activerecord/cli/model_loader.py
"""Load an ActiveRecord model named as ``module:Class``."""

import importlib
import os
import sys
from typing import List, Optional

from ..interface import IActiveRecord, IAsyncActiveRecord
from .errors import CLIError


def prepare_sys_path(extra_paths: Optional[List[str]] = None) -> None:
    """Put the caller's working directory and ``--path`` entries on ``sys.path``.

    A console script starts with the script's directory on the path, not the
    directory the user invoked it from, so importing ``app.models`` needs this
    adjustment before any module import happens.

    Args:
        extra_paths: Additional directories from repeated ``--path`` options.
    """
    directories = [os.getcwd()] + list(extra_paths or [])
    for directory in reversed(directories):
        resolved = os.path.abspath(directory)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


def split_model_path(model_path: str):
    """Split ``module:Class`` into its two parts.

    Args:
        model_path: A value such as ``app.models:User``.

    Returns:
        Tuple of module path and class name.

    Raises:
        CLIError: When the value lacks the colon separator.
    """
    if ":" not in model_path:
        raise CLIError(
            f'Invalid model reference "{model_path}": expected the form module:Class, '
            "for example app.models:User"
        )
    module_path, class_name = model_path.rsplit(":", 1)
    if not module_path or not class_name:
        raise CLIError(
            f'Invalid model reference "{model_path}": both module and class must be present'
        )
    return module_path, class_name


def load_model(model_path: str):
    """Import and validate a model class.

    Args:
        model_path: A value such as ``app.models:User``.

    Returns:
        A :class:`ModelRef` describing the class and whether it is asynchronous.

    Raises:
        CLIError: When the module or class cannot be loaded, or the class is
            not an ActiveRecord model.
    """
    module_path, class_name = split_model_path(model_path)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", None) or module_path
        raise CLIError(
            f'Cannot import model "{model_path}": module "{missing}" was not found. '
            "Check the module name, or add its directory with --path."
        ) from None
    except Exception as exc:  # Import-time side effects can fail for many reasons.
        raise CLIError(f'Cannot import module "{module_path}": {exc}') from None

    try:
        model_class = getattr(module, class_name)
    except AttributeError:
        raise CLIError(
            f'Cannot load model "{model_path}": module "{module_path}" has no class "{class_name}"'
        ) from None

    if not isinstance(model_class, type):
        raise CLIError(f'Cannot load model "{model_path}": {class_name} is not a class')

    if issubclass(model_class, IAsyncActiveRecord):
        return ModelRef(model_class, is_async=True)
    if issubclass(model_class, IActiveRecord):
        return ModelRef(model_class, is_async=False)

    raise CLIError(
        f'Cannot load model "{model_path}": {class_name} is neither an '
        "IActiveRecord nor an IAsyncActiveRecord subclass"
    )


class ModelRef:
    """A loaded model class and the sync/async API it implements.

    Attributes:
        model: The model class.
        is_async: True when the class implements ``IAsyncActiveRecord``.
    """

    def __init__(self, model, is_async: bool):
        self.model = model
        self.is_async = is_async

    @property
    def name(self):
        """The model class name."""
        return self.model.__name__
