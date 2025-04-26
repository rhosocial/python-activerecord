# 自引用关系

自引用关系是模型与自身相关联的关系。在rhosocial ActiveRecord中，自引用关系允许您在单个模型内建模层次结构、网络和其他复杂关系。

## 概述

自引用关系对于建模各种数据结构非常有用，包括：

- 层次结构（例如，员工和经理、类别和子类别）
- 网络结构（例如，社交网络中的朋友、关注者和被关注者）
- 树形结构（例如，组织结构图、文件系统）
- 递归结构（例如，物料清单、嵌套评论）

在rhosocial ActiveRecord中，自引用关系使用与其他关系相同的关系描述符（`HasOne`、`HasMany`、`BelongsTo`）实现，但模型引用自身。

## 自引用关系的类型

### 一对多自引用关系

一对多自引用关系常用于层次结构，其中每条记录可以有多个子记录，但只有一个父记录。

#### 示例：类别和子类别

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Category(IntegerPKMixin, ActiveRecord):
    __table_name__ = "categories"
    
    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None  # 指向父类别的外键
    
    # 定义与父类别的关系
    parent: ClassVar[BelongsTo['Category']] = BelongsTo(
        foreign_key='parent_id',
        inverse_of='children'
    )
    
    # 定义与子类别的关系
    children: ClassVar[HasMany['Category']] = HasMany(
        foreign_key='parent_id',
        inverse_of='parent'
    )
    
    # 获取所有祖先的辅助方法
    def ancestors(self):
        ancestors = []
        current = self.parent()
        while current:
            ancestors.append(current)
            current = current.parent()
        return ancestors
    
    # 获取所有后代的辅助方法
    def descendants(self):
        result = []
        for child in self.children():
            result.append(child)
            result.extend(child.descendants())
        return result
```

### 多对多自引用关系

多对多自引用关系对于建模网络非常有用，其中每条记录可以与同类型的多条其他记录相关联。

#### 示例：社交网络中的朋友

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # 定义与Friendship模型的关系，表示由该用户发起的友谊
    friendships_initiated: ClassVar[HasMany['Friendship']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )
    
    # 定义与Friendship模型的关系，表示该用户接收的友谊
    friendships_received: ClassVar[HasMany['Friendship']] = HasMany(
        foreign_key='friend_id',
        inverse_of='friend'
    )
    
    # 获取所有朋友的辅助方法
    def friends(self):
        # 获取由该用户发起的友谊中的朋友
        initiated = self.friendships_initiated()
        friend_ids_initiated = [friendship.friend_id for friendship in initiated]
        
        # 获取该用户接收的友谊中的朋友
        received = self.friendships_received()
        friend_ids_received = [friendship.user_id for friendship in received]
        
        # 合并所有朋友ID
        all_friend_ids = friend_ids_initiated + friend_ids_received
        
        # 返回所有朋友
        return User.find_all().where(id__in=all_friend_ids).all()

class Friendship(IntegerPKMixin, ActiveRecord):
    __table_name__ = "friendships"
    
    id: Optional[int] = None
    user_id: int      # 发起友谊的用户
    friend_id: int    # 接收友谊请求的用户
    status: str       # 例如，'pending'（待定）, 'accepted'（已接受）, 'rejected'（已拒绝）
    created_at: datetime
    
    # 定义与User模型的关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='friendships_initiated'
    )
    
    friend: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='friend_id',
        inverse_of='friendships_received'
    )
```

## 使用自引用关系

### 创建层次结构

```python
# 创建父类别
electronics = Category(name="电子产品")
electronics.save()

# 创建子类别
phones = Category(name="手机", parent_id=electronics.id)
phones.save()

laptops = Category(name="笔记本电脑", parent_id=electronics.id)
laptops.save()

# 创建子类别的子类别
smartphones = Category(name="智能手机", parent_id=phones.id)
smartphones.save()
```

### 导航层次结构

```python
# 获取一个类别
smartphones = Category.find_by(name="智能手机")

# 获取父类别
parent = smartphones.parent()
print(f"父类别: {parent.name}")  # 输出: 父类别: 手机

# 获取所有祖先
ancestors = smartphones.ancestors()
for ancestor in ancestors:
    print(f"祖先: {ancestor.name}")  # 输出: 祖先: 手机, 祖先: 电子产品

# 获取类别的所有子类别
electronics = Category.find_by(name="电子产品")
children = electronics.children()
for child in children:
    print(f"子类别: {child.name}")  # 输出: 子类别: 手机, 子类别: 笔记本电脑

# 获取所有后代
descendants = electronics.descendants()
for descendant in descendants:
    print(f"后代: {descendant.name}")  # 输出: 后代: 手机, 后代: 笔记本电脑, 后代: 智能手机
```

### 管理朋友关系

```python
# 创建用户
alice = User(username="alice", email="alice@example.com")
alice.save()

bob = User(username="bob", email="bob@example.com")
bob.save()

charlie = User(username="charlie", email="charlie@example.com")
charlie.save()

# 创建友谊关系
alice_bob_friendship = Friendship(
    user_id=alice.id,
    friend_id=bob.id,
    status="accepted",
    created_at=datetime.now()
)
alice_bob_friendship.save()

alice_charlie_friendship = Friendship(
    user_id=alice.id,
    friend_id=charlie.id,
    status="accepted",
    created_at=datetime.now()
)
alice_charlie_friendship.save()

# 获取用户的所有朋友
alice = User.find_by(username="alice")
friends = alice.friends()

for friend in friends:
    print(f"朋友: {friend.username}")  # 输出: 朋友: bob, 朋友: charlie
```

## 高级技术

### 递归查询

对于复杂的层次结构，您可能需要执行递归查询以高效地检索所有祖先或后代。这可以使用SQL中的递归公共表表达式（CTE）来完成，您可以使用原始SQL查询实现：

```python
# 使用递归CTE获取类别的所有后代
def get_all_descendants(category_id):
    sql = """
    WITH RECURSIVE descendants AS (
        SELECT id, name, parent_id
        FROM categories
        WHERE id = %s
        UNION ALL
        SELECT c.id, c.name, c.parent_id
        FROM categories c
        JOIN descendants d ON c.parent_id = d.id
    )
    SELECT * FROM descendants WHERE id != %s;
    """
    
    # 执行原始SQL查询
    return Category.find_by_sql(sql, [category_id, category_id])

# 使用示例
electronics = Category.find_by(name="电子产品")
descendants = get_all_descendants(electronics.id)
```

### 防止循环引用

在处理层次结构时，防止循环引用（例如，一个类别成为自己的祖先）非常重要。您可以实现验证逻辑来检查这一点：

```python
class Category(IntegerPKMixin, ActiveRecord):
    # ... 现有代码 ...
    
    def validate(self):
        super().validate()
        
        # 检查循环引用
        if self.parent_id and self.id:
            # 检查此类别是否被设置为自身的后代
            current = Category.find_by(id=self.parent_id)
            while current:
                if current.id == self.id:
                    self.add_error("parent_id", "不能将类别设置为自身的后代")
                    break
                current = current.parent()
```

## 最佳实践

1. **使用清晰的命名约定**：在定义自引用关系时，为关系使用清晰且描述性的名称（例如，`parent`、`children`、`friends`）。

2. **实现辅助方法**：在模型中添加辅助方法，使自引用关系的使用更加直观，如上面的示例所示。

3. **注意深层次结构**：深层次结构可能导致性能问题。对于非常深的层次结构，考虑使用物化路径或嵌套集等技术。

4. **防止循环引用**：实现验证逻辑，防止层次结构中的循环引用。

5. **使用预加载**：在检索具有相关记录的多个记录时，使用预加载以避免N+1查询问题。

## 结论

rhosocial ActiveRecord中的自引用关系提供了一种强大的方式，可以在单个模型内建模复杂结构。通过使用与其他关系相同的关系描述符，但让模型引用自身，您可以创建层次结构、网络和其他复杂关系。通过添加辅助方法和验证逻辑，您可以为应用程序创建直观且健壮的模型。