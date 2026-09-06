# docs/examples/chapter_14_scenarios/graphql_fastapi/app/schema.py
"""Graphene Schema + 异步 DataLoader。

由于模型是异步的，resolver 直接 ``await`` 查询即可——不再需要
``run_in_threadpool``。DataLoader 继续用于合并批量的 N+1 查询。
"""
from aiodataloader import DataLoader
from graphene import Field, List, ObjectType, Schema, String

from .models import Comment, Post, User


# --- DataLoaders (批量加载，解决 N+1) ---


class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        users = await User.query().where(User.c.id.in_(keys)).all()
        user_map = {str(u.id): u for u in users}
        return [user_map.get(str(k)) for k in keys]


class PostLoader(DataLoader):
    async def batch_load_fn(self, keys):
        posts = await Post.query().where(Post.c.id.in_(keys)).all()
        post_map = {str(p.id): p for p in posts}
        return [post_map.get(str(k)) for k in keys]


class PostsByUserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        posts = await Post.query().where(Post.c.user_id.in_(user_ids)).all()
        from collections import defaultdict

        posts_by_user = defaultdict(list)
        for post in posts:
            posts_by_user[str(post.user_id)].append(post)
        return [posts_by_user.get(str(uid), []) for uid in user_ids]


class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        comments = await Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
        from collections import defaultdict

        comments_by_post = defaultdict(list)
        for comment in comments:
            comments_by_post[str(comment.post_id)].append(comment)
        return [comments_by_post.get(str(pid), []) for pid in post_ids]


# --- Types ---


class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)

    async def resolve_posts(root, info):
        return await info.context["loaders"].posts_by_user_loader.load(root.id)


class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_comments(root, info):
        return await info.context["loaders"].comments_by_post_loader.load(root.id)


class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context["loaders"].post_loader.load(root.post_id)


# --- Query ---


class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)
    user = Field(UserType, id=String(required=True))
    post = Field(PostType, id=String(required=True))

    async def resolve_users(root, info):
        return await User.find_all()

    async def resolve_posts(root, info):
        return await Post.find_all()

    async def resolve_user(root, info, id):
        return await User.find_one(id)

    async def resolve_post(root, info, id):
        return await Post.find_one(id)


class Loaders:
    """每个请求独立创建一组 DataLoader，避免跨请求缓存串扰。"""

    def __init__(self):
        self.user_loader = UserLoader()
        self.post_loader = PostLoader()
        self.posts_by_user_loader = PostsByUserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()


schema = Schema(query=Query)