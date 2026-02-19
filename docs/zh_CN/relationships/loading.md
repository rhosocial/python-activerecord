# 加载策略 (Loading Strategies)

在使用关联关系时，选择合适的加载策略对于应用性能至关重要。不同的加载策略适用于不同的使用场景。

> 💡 **AI提示词示例**: "ActiveRecord中的关联关系加载策略有哪些？它们各有什么优缺点？"

## N+1 查询问题

当遍历一个对象列表并访问其关联关系时，可能会触发大量的数据库查询，这就是著名的 N+1 问题。

```python
# 导入必要的模块
from typing import List
from rhosocial.activerecord.model import ActiveRecord

# 假设我们有User和Profile模型，定义了一对一关系
# User.has_one(Profile) 和 Profile.belongs_to(User)

# N+1 查询问题示例
print("=== N+1 查询问题示例 ===")

# 第1次查询：获取所有用户
users = User.query().all()  # 执行1次查询
print(f"获取到 {len(users)} 个用户")

# 遍历用户并访问关联的资料
for user in users:
    # 每次调用profile()都会执行1次数据库查询
    # 如果有100个用户，就会执行100次查询
    profile = user.profile()  # 执行N次查询（N=用户数量）
    if profile:
        print(f"用户 {user.username} 的简介: {profile.bio}")
    else:
        print(f"用户 {user.username} 没有资料")

# 总查询次数 = 1 + N = 101次查询（假设有100个用户）
print(f"总共执行了 {1 + len(users)} 次数据库查询")

# N+1问题的影响：
# 1. 数据库压力增大
# 2. 网络延迟累积
# 3. 应用响应时间变长
# 4. 数据库连接资源消耗增加
```

> 💡 **AI提示词示例**: "什么是N+1查询问题？它会对应用性能造成什么影响？"

## 预加载 (Eager Loading)

使用 `with_()` 方法可以在主查询中一并加载关联数据，有效解决 N+1 问题。

```python
# 预加载示例
print("=== 预加载示例 ===")

# 使用预加载一次性获取用户及其资料
# with_('profile')告诉ORM在查询用户时同时加载关联的资料数据
users_with_profiles = User.query().with_('profile').all()  # 只执行1次查询（或少量查询）

print(f"通过预加载获取到 {len(users_with_profiles)} 个用户及其资料")

# 遍历用户并访问关联的资料
for user in users_with_profiles:
    # 这里不再触发数据库查询，直接从缓存读取
    # 因为资料数据已经在预加载时一并获取了
    profile = user.profile()  # 从缓存中获取，不执行查询
    if profile:
        print(f"用户 {user.username} 的简介: {profile.bio}")
    else:
        print(f"用户 {user.username} 没有资料")

# 总查询次数 = 1次（或通过JOIN获取所有数据）
print(f"总共执行了 1 次数据库查询")

# 预加载的优势：
# 1. 显著减少数据库查询次数
# 2. 降低网络延迟
# 3. 提高应用响应速度
# 4. 减少数据库连接资源消耗

# 预加载多个关联关系
print("\n=== 预加载多个关联关系 ===")

# 假设User还有posts关联关系（一对多）
# 可以同时预加载多个关联关系
users_with_relations = User.query().with_('profile').with_('posts').all()

for user in users_with_relations:
    # 访问预加载的资料
    profile = user.profile()  # 从缓存获取
    
    # 访问预加载的文章
    posts = user.posts()  # 从缓存获取
    
    print(f"用户 {user.username} 有 {len(posts)} 篇文章")
    if profile:
        print(f"  简介: {profile.bio}")
```

> 💡 **AI提示词示例**: "如何使用with_()方法进行预加载？预加载能带来什么性能提升？"

## 延迟加载 (Lazy Loading)

默认情况下，关系是延迟加载的。只有当你调用关系方法时，才会执行 SQL 查询。

```python
# 延迟加载示例
print("=== 延迟加载示例 ===")

# 获取用户时不加载关联关系
user = User.find_one({'username': '张三'})  # 执行1次查询获取用户

# 此时用户对象已加载，但关联的资料还未加载
print(f"已获取用户: {user.username}")

# 当真正需要访问关联数据时才执行查询
if user:
    # 只有调用profile()时才执行数据库查询获取资料
    profile = user.profile()  # 执行1次查询获取资料
    
    if profile:
        print(f"用户资料: {profile.bio}")
    else:
        print("用户没有资料")
    
    # 再次访问同一个关联关系时，不会再执行查询
    # 因为数据已被缓存
    profile_again = user.profile()  # 从缓存获取，不执行查询
    print("第二次访问资料（从缓存获取）")

# 延迟加载的适用场景：
# 1. 不确定是否需要访问关联数据
# 2. 只需要访问部分对象的关联数据
# 3. 内存使用敏感的场景
# 4. 关联数据较大的情况

# 延迟加载的注意事项：
# 1. 可能导致N+1查询问题
# 2. 需要注意数据库连接的生命周期
# 3. 在循环中访问关联数据时要考虑性能影响
```

> 💡 **AI提示词示例**: "延迟加载在什么情况下比较适用？使用时需要注意什么问题？"

## 批量加载 (Batch Loading)

即使没有使用 `with_()`，某些高级加载器也支持在访问第一个元素的关联时，自动批量加载列表中所有其他元素的关联。

```python
# 批量加载概念示例（当前库主要依赖with_，但了解概念有帮助）
print("=== 批量加载概念示例 ===")

# 假设有一个支持批量加载的实现
users = User.query().all()  # 获取所有用户

# 当访问第一个用户的关联数据时
first_user_profile = users[0].profile()  # 访问第一个用户的资料

# 理想情况下，系统会自动批量加载所有用户的资料
# 而不仅仅是第一个用户的资料
# 这样可以避免后续访问其他用户资料时的多次查询

print("批量加载的优势：")
print("1. 在首次访问关联数据时智能预判需求")
print("2. 自动优化查询策略")
print("3. 平衡了预加载和延迟加载的优点")

# 当前推荐做法仍然是显式使用with_()
print("\n当前推荐做法：")
users_with_profiles = User.query().with_('profile').all()
print("显式预加载仍是最佳实践")
```

> 💡 **AI提示词示例**: "批量加载和预加载有什么区别？哪种方式更适合我的应用场景？"

## 性能对比和选择建议

```python
# 性能对比总结
print("=== 关联关系加载策略对比 ===")

print("""
1. 预加载 (Eager Loading) - with_()
   适用场景：
   - 确定需要访问大部分对象的关联数据
   - 对性能要求较高的场景
   - 需要避免N+1问题的情况
   
   优点：
   - 查询次数最少
   - 性能最佳
   - 可预测的数据库负载
   
   缺点：
   - 可能加载不必要的数据
   - 内存使用较多

2. 延迟加载 (Lazy Loading) - 默认行为
   适用场景：
   - 不确定是否需要访问关联数据
   - 只需要访问少数对象的关联数据
   - 内存使用敏感的场景
   
   优点：
   - 按需加载，节省内存
   - 灵活性高
   
   缺点：
   - 可能导致N+1问题
   - 性能不可预测

3. 选择建议：
   - 明确需要关联数据 → 使用预加载
   - 不确定是否需要 → 使用延迟加载
   - 循环访问关联数据 → 必须使用预加载
   - 性能关键路径 → 优先考虑预加载
""")
```

> 💡 **AI提示词示例**: "在实际项目中应该如何选择合适的关联关系加载策略？有什么最佳实践吗？"