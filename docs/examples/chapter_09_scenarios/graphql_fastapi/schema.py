import graphene
from graphene import ObjectType, String, Schema, Field, List
from aiodataloader import DataLoader
from starlette.concurrency import run_in_threadpool
from models import User, Post, Comment

# --- DataLoaders ---
# We use aiodataloader which is async.
# Since our ORM is synchronous, we run queries in threadpool.

class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        # keys are user_ids
        def load_users():
            users = User.query().where(User.c.id.in_(keys)).all()
            user_map = {str(u.id): u for u in users}
            return [user_map.get(str(k)) for k in keys]
            
        return await run_in_threadpool(load_users)

class PostLoader(DataLoader):
    async def batch_load_fn(self, keys):
        def load_posts():
            posts = Post.query().where(Post.c.id.in_(keys)).all()
            post_map = {str(p.id): p for p in posts}
            return [post_map.get(str(k)) for k in keys]
            
        return await run_in_threadpool(load_posts)

class PostsByUserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        def load_posts_by_user():
            # Load all posts for these users
            posts = Post.query().where(Post.c.user_id.in_(user_ids)).all()
            
            # Group by user_id
            from collections import defaultdict
            posts_by_user = defaultdict(list)
            for post in posts:
                posts_by_user[str(post.user_id)].append(post)
                
            return [posts_by_user.get(str(uid), []) for uid in user_ids]
            
        return await run_in_threadpool(load_posts_by_user)

class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        def load_comments():
            comments = Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
            
            from collections import defaultdict
            comments_by_post = defaultdict(list)
            for comment in comments:
                comments_by_post[str(comment.post_id)].append(comment)
                
            return [comments_by_post.get(str(pid), []) for pid in post_ids]
            
        return await run_in_threadpool(load_comments)


# --- Types ---

class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)
    
    async def resolve_posts(root, info):
        return await info.context['loaders'].posts_by_user_loader.load(root.id)

class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)
        
    async def resolve_comments(root, info):
        return await info.context['loaders'].comments_by_post_loader.load(root.id)

class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context['loaders'].post_loader.load(root.post_id)

# --- Query ---

class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)
    user = Field(UserType, id=String(required=True))
    post = Field(PostType, id=String(required=True))

    async def resolve_users(root, info):
        return await run_in_threadpool(lambda: User.find_all())

    async def resolve_posts(root, info):
        return await run_in_threadpool(lambda: Post.find_all())
    
    async def resolve_user(root, info, id):
        return await run_in_threadpool(lambda: User.find(id))
        
    async def resolve_post(root, info, id):
        return await run_in_threadpool(lambda: Post.find(id))

schema = Schema(query=Query)
