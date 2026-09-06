# docs/examples/chapter_14_scenarios/fastapi_blog/app/logging_conf.py
"""应用日志配置。

使用框架提供的 ``ActiveRecordFormatter``（统一输出 ``模块:行号`` 前缀），
并让 uvicorn 的访问日志与 ORM 内部日志共享同一套格式，汇聚到 root logger。
参考真实项目实践：文件轮转 + 控制台双输出。
"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from rhosocial.activerecord.logging import ActiveRecordFormatter


def setup_logging(
    log_dir: str = "logs",
    log_filename: str = "blog",
    level: str = "INFO",
    when: str = "d",
    backup_count: int = 7,
) -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = ActiveRecordFormatter()

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path / f"{log_filename}.log"),
        when=when,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # uvicorn 的访问/错误日志转发到 root，与 ORM 日志格式统一
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True