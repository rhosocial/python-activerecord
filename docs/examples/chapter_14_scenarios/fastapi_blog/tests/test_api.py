# docs/examples/chapter_14_scenarios/fastapi_blog/tests/test_api.py
"""博客 API 集成测试：验证 CRUD、并发连接隔离与 Prometheus 指标。

使用 httpx ASGITransport 在进程内驱动 FastAPI。整个测试生命周期
（建池 → 推导 DDL 建表 → 种子 → 请求 → 关池）在**同一个**
``asyncio.run()`` 事件循环中完成，避免跨事件循环使用连接池。
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx  # noqa: E402


DB_PATH = "/tmp/fastapi_blog_test.db"


def _run_with_app(coro_factory):
    """在单一事件循环内完成：建池 → 建表 → 种子 → 执行请求 → 关池。"""
    from app.database import configure_models, create_pool, create_schema, make_connection_config
    from app.main import ALL_MODELS, app

    config = make_connection_config(database=DB_PATH)
    configure_models(ALL_MODELS, config)

    async def main():
        pool = await create_pool(config)
        app.state.pool = pool
        async with pool.connection():
            await create_schema(ALL_MODELS)
            from app.models import Post, User

            if await User.query().count() == 0:
                alice = User(username="alice", email="alice@example.com")
                await alice.save()
                await Post(user_id=alice.id, title="Hello", content="c1").save()
                await Post(user_id=alice.id, title="World", content="c2").save()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await coro_factory(client)

        await pool.close()

    asyncio.run(main())


def _cleanup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def test_list_users():
    _cleanup()

    async def scenario(client):
        resp = await client.get("/api/users/")
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 1
        assert users[0]["username"] == "alice"

    _run_with_app(scenario)


def test_create_and_get_post():
    _cleanup()

    async def scenario(client):
        users = (await client.get("/api/users/")).json()
        uid = users[0]["id"]
        resp = await client.post("/api/posts/", params={"title": "Third", "content": "c3", "user_id": uid})
        assert resp.status_code == 201
        post = resp.json()
        got = await client.get(f"/api/posts/{post['id']}")
        assert got.status_code == 200
        assert got.json()["content"] == "c3"

    _run_with_app(scenario)


def test_publish_post():
    _cleanup()

    async def scenario(client):
        users = (await client.get("/api/users/")).json()
        uid = users[0]["id"]
        posts = (await client.get(f"/api/users/{uid}/posts")).json()
        pid = posts[0]["id"]
        resp = await client.post(f"/api/posts/{pid}/publish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_published"] is True
        assert body["published_at"] is not None

    _run_with_app(scenario)


def test_parallel_requests_use_isolated_connections():
    """并发请求各自使用独立连接（AsyncBackendPool + contextvar 隔离）。"""
    _cleanup()

    async def scenario(client):
        async def hit():
            resp = await client.get("/api/users/")
            assert resp.status_code == 200
            return resp.json()

        results = await asyncio.gather(*[hit() for _ in range(20)])
        assert len(results) == 20
        for users in results:
            assert users[0]["username"] == "alice"

    _run_with_app(scenario)


def test_metrics_endpoint():
    _cleanup()

    async def scenario(client):
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "http_requests_total" in body
        assert "http_request_duration_seconds" in body

    _run_with_app(scenario)


def test_user_not_found():
    _cleanup()

    async def scenario(client):
        resp = await client.get(f"/api/users/{uuid.uuid4()}")
        assert resp.status_code == 404

    _run_with_app(scenario)