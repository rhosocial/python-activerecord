# src/rhosocial/activerecord/backend/base/logging.py
import inspect
import logging
from typing import Optional

class LoggingMixin:
    """Mixin for logging functionality."""
    @property
    def logger(self) -> logging.Logger:
        return self._logger
    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or logging.getLogger('storage')
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        current_frame = inspect.currentframe().f_back
        stack_level = 1
        while current_frame:
            if current_frame.f_globals['__name__'] != 'storage':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1
        self.logger.log(level, msg, *args, stacklevel=stack_level, **kwargs)