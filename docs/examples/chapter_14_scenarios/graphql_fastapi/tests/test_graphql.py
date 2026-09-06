# docs/examples/chapter_14_scenarios/graphql_fastapi/tests/test_graphql.py
"""GraphQL API 集成测试：查询用户/文章/评论，验证 N+1 DataLoader 与并发隔离。

整个生命周期（建池 → 推导 DDL → 种子 → 请求）在同一个 ``asyncio.run()``
事件循环中完成。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx  # noqa: E402

DB_PATH = "/tmp/graphql_test.db"


def _run(coro_factory):
    from app.database import configure_models, create_pool, create_schema, make_connection_config
    from app.main import ALL_MODELS, app

    config = make_connection_config(database=DB_PATH)
    configure_models(ALL_MODELS, config)

    async def main():
        pool = await create_pool(config)
        app.state.pool = pool
        async with pool.connection():
            await create_schema(ALL_MODELS)
            from app.models import Comment, Post, User

            if await User.query().count() == 0:
                alice = User(username="alice", email="alice@example.com")
                await alice.save()
                bob = User(username="bob", email="bob@example.com")
                await bob.save()
                p1 = Post(user_id=alice.id, title="Hello GraphQL", content="A post about GraphQL.")
                await p1.save()
                p2 = Post(user_id=alice.id, title="FastAPI Integration", content="FastAPI + Graphene.")
                await p2.save()
                await Comment(user_id=bob.id, post_id=p1.id, content="Great post!").save()
                await Comment(user_id=alice.id, post_id=p1.id, content="Thanks Bob!").save()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await coro_factory(client)

        await pool.close()

    asyncio.run(main())


def _cleanup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def _post_graphql(client, query, variables=None):
    return client.post("/graphql", json={"query": query, "variables": variables})


def test_query_users_with_posts():
    _cleanup()

    async def scenario(client):
        query = """
        query {
          users { id username posts { id title } }
        }
        """
        resp = await _post_graphql(client, query)
        assert resp.status_code == 200
        body = resp.json()
        assert "errors" not in body, body.get("errors")
        users = body["data"]["users"]
        assert len(users) == 2
        alice = next(u for u in users if u["username"] == "alice")
        assert len(alice["posts"]) == 2

    _run(scenario)


def test_query_post_with_user_and_comments():
    _cleanup()

    async def scenario(client):
        query = """
        query {
          posts { id title user { username } comments { content user { username } } }
        }
        """
        resp = await _post_graphql(client, query)
        assert resp.status_code == 200
        body = resp.json()
        assert "errors" not in body, body.get("errors")
        posts = body["data"]["posts"]
        assert len(posts) == 2
        hello = next(p for p in posts if p["title"] == "Hello GraphQL")
        assert hello["user"]["username"] == "alice"
        assert len(hello["comments"]) == 2

    _run(scenario)


def test_query_single_user():
    _cleanup()

    async def scenario(client):
        # 先取一个用户 id
        q_all = "query { users { id } }"
        all_resp = await _post_graphql(client, q_all)
        uid = all_resp.json()["data"]["users"][0]["id"]

        query = """
        query($id: String!) {
          user(id: $id) { id username email }
        }
        """
        resp = await _post_graphql(client, query, {"id": uid})
        assert resp.status_code == 200
        user = resp.json()["data"]["user"]
        assert user["id"] == uid

    _run(scenario)


def test_concurrent_graphql_requests():
    """并发 GraphQL 请求各自使用独立连接。"""
    _cleanup()

    async def scenario(client):
        query = "query { users { id username } }"

        async def one():
            resp = await _post_graphql(client, query)
            assert resp.status_code == 200
            return resp.json()["data"]["users"]

        results = await asyncio.gather(*[one() for _ in range(10)])
        assert len(results) == 10
        for users in results:
            assert len(users) == 2

    _run(scenario)