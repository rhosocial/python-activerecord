# exp5_multithread_warning.py - 展示多线程共享连接的问题（反面教材）
# docs/examples/chapter_12_scenarios/parallel_workers/exp5_multithread_warning.py
"""
实验目标：
    使用真实的 ActiveRecord ORM，展示多线程共享连接时的危险。

    场景 0：验证 SQLiteConnectionConfig.check_same_thread 默认值为 True
    场景 1：多线程共享同一 __backend__（危险，未定义行为）
    场景 2：每线程独立调用 configure()（行不通——configure 是类级别属性）

⚠️  这是反面教材，展示错误的做法。
    正确方案是使用多进程（见 exp1_basic_multiprocess.py）。

运行方式：
    python setup_db.py   # 先初始化数据库
    python exp5_multithread_warning.py
"""

from __future__ import annotations

import os
import sys
import threading
import time

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend  # noqa: E402
from rhosocial.activerecord.backend.impl.sqlite.config import (  # noqa: E402
    SQLiteConnectionConfig,
)

from models import Comment, Post, User  # noqa: E402

DB_PATH = "parallel_workers.db"
NUM_THREADS = 4

_errors: list[str] = []
_error_lock = threading.Lock()


def make_config(check_same_thread: bool = True) -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(
        database=DB_PATH,
        check_same_thread=check_same_thread,
        pragmas={"journal_mode": "WAL"},
    )


def reset_view_counts() -> None:
    """重置所有文章的 view_count"""
    config = make_config(check_same_thread=False)
    Post.configure(config, SQLiteBackend)
    for p in Post.query().all():
        p.view_count = 0
        p.save()
    Post.backend().disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# 场景 0：验证 check_same_thread 默认值
# ─────────────────────────────────────────────────────────────────────────────


def scenario_0_check_same_thread() -> None:
    """
    验证 SQLiteConnectionConfig.check_same_thread 默认为 True。
    在父线程 configure() 后，子线程访问同一 backend 会抛出 ProgrammingError。
    """
    print("=== 场景 0：验证 check_same_thread 默认值 ===\n")

    results: dict[str, str] = {}

    # ── 测试 A：check_same_thread=True（默认）──
    config_strict = make_config(check_same_thread=True)
    User.configure(config_strict, SQLiteBackend)

    def use_in_thread_strict() -> None:
        try:
            User.query().count()
            results["strict"] = "✅ 无报错（不应发生）"
        except Exception as e:
            results["strict"] = f"❌ {type(e).__name__}: {e}"

    t = threading.Thread(target=use_in_thread_strict)
    t.start()
    t.join()
    User.backend().disconnect()
    print(f"  check_same_thread=True  → {results['strict']}")

    # ── 测试 B：check_same_thread=False（关闭检查）──
    config_loose = make_config(check_same_thread=False)
    User.configure(config_loose, SQLiteBackend)

    def use_in_thread_loose() -> None:
        try:
            User.query().count()
            results["loose"] = "✅ 无报错（但不保证线程安全）"
        except Exception as e:
            results["loose"] = f"❌ {type(e).__name__}: {e}"

    t = threading.Thread(target=use_in_thread_loose)
    t.start()
    t.join()
    User.backend().disconnect()
    print(f"  check_same_thread=False → {results['loose']}")
    print("\n  结论：默认值 True 会拦截跨线程使用；False 仅关闭检查，不解决并发安全问题。\n")


# ─────────────────────────────────────────────────────────────────────────────
# 场景 1：多线程共享同一 __backend__（危险）
# ─────────────────────────────────────────────────────────────────────────────


def scenario_1_shared_backend() -> None:
    """
    ❌ 错误做法：多线程共享同一个 __backend__（等同于共享连接）。
    即使用 check_same_thread=False 关闭了 sqlite3 的自检，
    并发写入仍可能导致游标混乱或数据损坏。
    """
    print("=== 场景 1：多线程共享同一 __backend__（❌ 错误做法）===\n")

    config = make_config(check_same_thread=False)
    # ❌ 在主线程 configure()，所有子线程共用同一 backend 实例
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    reset_view_counts()
    _errors.clear()

    # 获取所有文章 ID（主线程查询，子线程写入）
    all_posts = Post.query().order_by(Post.c.id).all()
    chunk_size = max(1, len(all_posts) // NUM_THREADS)
    chunks = [all_posts[i : i + chunk_size] for i in range(0, len(all_posts), chunk_size)]

    def thread_worker_shared(posts: list[Post]) -> None:
        for post in posts:
            try:
                time.sleep(0.002)  # 制造竞态机会
                # ❌ 多线程共用同一连接，游标可能混乱
                post.view_count += 1
                post.save()
            except Exception as e:
                with _error_lock:
                    _errors.append(f"线程 {threading.current_thread().name}: {e}")

    threads = [
        threading.Thread(
            target=thread_worker_shared,
            args=(chunks[i],),
            name=f"T{i}",
        )
        for i in range(min(NUM_THREADS, len(chunks)))
    ]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    elapsed = time.perf_counter() - t0

    User.backend().disconnect()

    if _errors:
        print(f"  ❌ 发生 {len(_errors)} 个错误（展示前 3 个）：")
        for e in _errors[:3]:
            print(f"     {e}")
    else:
        print("  （本次未报错，但这是偶然的；共享连接不保证安全）")

    print(f"  耗时：{elapsed:.3f}s")
    print("  注意：即使没有抛出异常，数据完整性也无法保证。\n")


# ─────────────────────────────────────────────────────────────────────────────
# 场景 2：每线程独立 configure()（无效——configure 是类级属性）
# ─────────────────────────────────────────────────────────────────────────────


def scenario_2_per_thread_configure() -> None:
    """
    ❌ 误解：以为每个线程调用 configure() 就能得到独立连接。
    实际上 configure() 写入的是类级属性 __backend__，
    最后一个线程的 configure() 会覆盖所有线程的后端。
    """
    print("=== 场景 2：每线程调用 configure()（❌ 无效，类属性被互相覆盖）===\n")

    reset_view_counts()
    _errors.clear()
    backend_ids: list[int] = []
    lock = threading.Lock()

    def thread_worker_configure(thread_id: int, posts: list[Post]) -> None:
        # 每个线程都调用 configure()
        config = make_config(check_same_thread=False)
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()

        # 记录 backend 对象 id，验证是否真的独立
        with lock:
            backend_ids.append(id(Post.backend()))

        time.sleep(0.01)  # 等待其他线程也完成 configure()

        for post in posts:
            try:
                post.view_count += 1
                post.save()
            except Exception as e:
                with _error_lock:
                    _errors.append(f"Thread-{thread_id}: {e}")

    all_posts = Post.query().order_by(Post.c.id).all()
    chunk_size = max(1, len(all_posts) // NUM_THREADS)
    chunks = [all_posts[i : i + chunk_size] for i in range(0, len(all_posts), chunk_size)]

    threads = [
        threading.Thread(target=thread_worker_configure, args=(i, chunks[i]))
        for i in range(min(NUM_THREADS, len(chunks)))
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    unique_backends = len(set(backend_ids))
    print(
        f"  {NUM_THREADS} 个线程各自 configure()，实际 backend 实例数：{unique_backends}（应为 {NUM_THREADS}，实为 1）"
    )
    print("  原因：__backend__ 是类属性，最后一次 configure() 覆盖了前面所有的。\n")

    if _errors:
        print(f"  ❌ 发生 {len(_errors)} 个错误：")
        for e in _errors[:3]:
            print(f"     {e}")
    else:
        print("  （本次无报错，但 backend 不独立，安全性无法保证）\n")


# ─────────────────────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    scenario_0_check_same_thread()
    scenario_1_shared_backend()
    scenario_2_per_thread_configure()

    print("=" * 55)
    print(
        "总结：为什么推荐多进程而非多线程？\n"
        "\n"
        "  场景 1（共享 __backend__）：\n"
        "    - configure() 写入类属性，所有线程共享同一 backend\n"
        "    - 底层连接对象不是线程安全的\n"
        "    - check_same_thread=False 仅关闭检查，不解决并发问题\n"
        "\n"
        "  场景 2（每线程 configure()）：\n"
        "    - configure() 是类级属性写入，后者覆盖前者\n"
        "    - 线程之间无法真正拥有独立的 backend\n"
        "\n"
        "  推荐方案（多进程）：\n"
        "    - 进程有独立内存空间，configure() 真正隔离\n"
        "    - 绕过 GIL，实现真正的 CPU 并行\n"
        "    - 见 exp1_basic_multiprocess.py\n"
    )


if __name__ == "__main__":
    main()
