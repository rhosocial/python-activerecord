# exp3_deadlock_wrong.py - 无原子领取导致重复处理（反面教材）
# docs/examples/chapter_12_scenarios/parallel_workers/exp3_deadlock_wrong.py
"""
实验目标：
    演示"读后改"（Read-Then-Write）竞态条件，使用真实的 ActiveRecord ORM。

    多个 Worker 同时查询 draft 状态的文章并尝试将其标记为 published，
    由于没有原子领取，同一篇文章可能被多个 Worker 同时处理。

⚠️  这是反面教材，展示错误的做法。
    正确做法见 exp4_partition_correct.py。

运行方式：
    python setup_db.py   # 先初始化数据库
    python exp3_deadlock_wrong.py
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from collections import defaultdict

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend  # noqa: E402
from rhosocial.activerecord.backend.impl.sqlite.config import (  # noqa: E402
    SQLiteConnectionConfig,
)

from models import Post, User  # noqa: E402

DB_PATH = "parallel_workers.db"
NUM_WORKERS = 4
BATCH_SIZE = 5  # 每次查询 5 篇文章（数据集较小，易触发竞态）


def make_config() -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(
        database=DB_PATH,
        pragmas={"journal_mode": "WAL", "busy_timeout": "5000"},
    )


def reset_posts_to_draft() -> None:
    """将所有文章重置为 draft 状态"""
    config = make_config()
    Post.configure(config, SQLiteBackend)
    posts = Post.query().all()
    for p in posts:
        p.status = "draft"
        p.view_count = 0
        p.save()
    Post.backend().disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# ❌ 错误的 Worker 实现：先读取，再更新（非原子）
# ─────────────────────────────────────────────────────────────────────────────


def worker_wrong(worker_id: int) -> dict:
    """
    错误模式：先用 query() 查询 draft 文章列表，
    sleep 制造竞态窗口，再逐篇更新状态。

    关键缺陷：
      - query() 和后续的 save() 之间没有事务保护
      - 多个 Worker 可能在竞态窗口内读到相同的文章列表
      - 导致同一篇文章被多个 Worker 重复"发布"
    """
    config = make_config()
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()

    # ❌ 第一步：查询（非事务保护）
    pending = Post.query().where(Post.c.status == "draft").order_by(Post.c.id).limit(BATCH_SIZE).all()
    claimed_ids = [p.id for p in pending if p.id is not None]

    # ❌ 竞态窗口：sleep 模拟真实的网络/CPU 延迟
    # 此时其他 Worker 也可能查询到相同的文章列表
    time.sleep(0.02)

    # ❌ 第二步：更新（不检查当前状态，覆盖其他 Worker 的修改）
    for post in pending:
        post.status = "published"
        post.view_count += 1
        post.save()

    User.backend().disconnect()
    return {"worker_id": worker_id, "claimed_ids": claimed_ids}


# ─────────────────────────────────────────────────────────────────────────────
# 分析结果
# ─────────────────────────────────────────────────────────────────────────────


def analyze_duplicates(results: list[dict]) -> dict:
    id_to_workers: dict = defaultdict(list)
    for r in results:
        for post_id in r["claimed_ids"]:
            id_to_workers[post_id].append(r["worker_id"])
    return {pid: wids for pid, wids in id_to_workers.items() if len(wids) > 1}


# ─────────────────────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    reset_posts_to_draft()

    config = make_config()
    Post.configure(config, SQLiteBackend)
    total = Post.query().count()
    Post.backend().disconnect()

    if total < NUM_WORKERS:
        print("⚠️  文章数不足，请先运行 setup_db.py")
        sys.exit(1)

    print(f"实验设置：{NUM_WORKERS} 个进程同时启动，各自查询前 {BATCH_SIZE} 篇 draft 文章\n")
    print("=== 错误模式：无原子领取（竞态条件）===")
    print("观察点：多个 Worker 是否会处理相同的文章？\n")

    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results = pool.map(worker_wrong, list(range(NUM_WORKERS)))

    print("各 Worker 声称处理的文章数：")
    for r in results:
        print(f"  Worker {r['worker_id']}: {len(r['claimed_ids'])} 篇")

    duplicates = analyze_duplicates(results)
    print("\n重复处理分析：")
    if duplicates:
        print(f"  ⚠️  发现 {len(duplicates)} 篇文章被多个 Worker 同时处理：")
        for post_id, workers in sorted(duplicates.items())[:5]:
            print(f"     Post #{post_id} 被 Worker {workers} 同时领取")
        if len(duplicates) > 5:
            print(f"     … 还有 {len(duplicates) - 5} 篇（仅显示前 5 篇）")
    else:
        print("  （本次未检测到重复，但竞态是概率性的，可多次运行或增大 NUM_WORKERS）")

    print("""
结论：
  - "读后改"模式在多进程环境下存在竞态条件
  - 即使偶尔没有出现重复，也不代表代码正确
  - ActiveRecord 的 query().where().all() 返回快照，
    没有行级锁，其他进程随时可以修改同一批记录
  - 正确做法：在事务内查询并立即更新（见 exp4_partition_correct.py）
""")

    reset_posts_to_draft()
    print("✓ 已重置文章状态")


if __name__ == "__main__":
    main()
