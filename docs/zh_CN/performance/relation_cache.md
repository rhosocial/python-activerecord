# 关系缓存后端

关系缓存支持可插拔的 `CacheBackend` 协议，允许在不同存储后端之间切换。

## 缓存后端协议

所有缓存后端都实现 `CacheBackend[T]` 协议：

```python
from typing import Protocol, Optional, TypeVar, Generic

class CacheBackend(Protocol[T]):
    def get(self, key: str) -> Optional[CacheResult[T]]: ...
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

## 内置后端

### InMemoryCache（默认）

内存缓存是默认的后端，存储在模型实例的 `_relation_cache_{name}` 属性中。

```python
from rhosocial.activerecord.relation.cache_backends.in_memory import InMemoryCache

# 创建内存缓存（通常不需要手动创建，系统使用默认实例）
cache = InMemoryCache()
```

### RedisCache（分布式）

Redis 后端支持跨进程、跨实例的缓存共享。

```python
from rhosocial.activerecord.relation.cache_backends.redis import RedisCache
import redis.asyncio as aioredis

# 配置 Redis
redis_client = aioredis.from_url("redis://localhost:6379/0")

# 创建 Redis 缓存后端
cache = RedisCache(
    client=redis_client,
    ttl=600,           # 缓存有效期（秒）
    prefix="myapp:"    # 键前缀
)
```

## 缓存序列化

`CacheSerializer` 支持三种序列化格式：

| 格式 | 类 | 说明 |
|------|------|------|
| JSON | `JsonSerializer` | 通用、可读，适合简单数据 |
| MessagePack | `MsgPackSerializer` | 紧凑二进制，性能均衡 |
| Pickle | `PickleSerializer` | Python 原生，支持复杂对象 |

```python
from rhosocial.activerecord.relation.cache_backends._protocol import CacheSerializer

class CustomSerializer(CacheSerializer):
    def serialize(self, value) -> bytes: ...
    def deserialize(self, data: bytes): ...
```

## CacheResult 元数据

每次缓存查询返回带有元数据的结果：

```python
from rhosocial.activerecord.relation.cache_backends._protocol import CacheResult

result = cache.get("my_key")
if result:
    print(f"数据来源: {result.origin}")    # "cache" 或 "database"
    print(f"缓存时间: {result.age}s")      # 已缓存秒数
    print(f"剩余 TTL: {result.ttl}s")      # 剩余有效期
```

## 自定义后端

实现 `CacheBackend` 协议即可：

```python
from typing import Optional
from rhosocial.activerecord.relation.cache_backends._protocol import CacheBackend, CacheResult

class MyBackend(CacheBackend[dict]):
    def get(self, key: str) -> Optional[CacheResult[dict]]:
        # 从自定义存储中读取
        ...

    def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        # 写入自定义存储
        ...

    def delete(self, key: str) -> None:
        # 从自定义存储中删除
        ...
```
