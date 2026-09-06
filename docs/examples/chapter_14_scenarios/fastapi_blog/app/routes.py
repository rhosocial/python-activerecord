# docs/examples/chapter_14_scenarios/fastapi_blog/app/routes.py
"""博客 API 路由。"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .database import get_db_context
from .models import Post, User

router = APIRouter(prefix="/api", dependencies=[Depends(get_db_context)])


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------

@router.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(username: str, email: str, bio: Optional[str] = None):
    if await User.query().where(User.c.username == username).one():
        raise HTTPException(status_code=409, detail="用户名已存在")
    if await User.query().where(User.c.email == email).one():
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    user = User(username=username, email=email, bio=bio)
    await user.save()
    return user


@router.get("/users/")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
):
    query = User.query()
    if is_active is not None:
        query = query.where(User.c.is_active == is_active)
    users = await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return users


@router.get("/users/{user_id}")
async def get_user(user_id: uuid.UUID):
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# ---------------------------------------------------------------------------
# 文章
# ---------------------------------------------------------------------------

@router.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(title: str, content: str, user_id: uuid.UUID):
    author = await User.find_one(user_id)
    if not author:
        raise HTTPException(status_code=404, detail="作者不存在")

    post = Post(title=title, content=content, user_id=user_id)
    await post.save()
    return post


@router.get("/posts/")
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_published: Optional[bool] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
):
    query = Post.query()
    if is_published is not None:
        query = query.where(Post.c.is_published == is_published)
    if user_id is not None:
        query = query.where(Post.c.user_id == user_id)
    posts = await query.order_by((Post.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return posts


@router.get("/posts/{post_id}")
async def get_post(post_id: uuid.UUID):
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: uuid.UUID):
    """发布文章：设置发布时间并标记为已发布。"""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    post.is_published = True
    post.published_at = datetime.now(timezone.utc)
    await post.save()
    return post


# ---------------------------------------------------------------------------
# 关联查询
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/posts", response_model=List)
async def get_user_posts(
    user_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    posts = await user.posts_query().limit(limit).offset(skip).all()
    return posts