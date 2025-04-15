# 自定义ActiveQuery类

本文档说明如何创建和使用自定义ActiveQuery类来扩展特定模型的查询功能。

## 介绍

虽然默认的`ActiveQuery`类提供了全面的查询功能，但您可能需要为特定模型添加模型特定的查询方法或自定义查询行为。自定义ActiveQuery类允许您在专用类中封装模型特定的查询逻辑。

## 创建自定义ActiveQuery类

要创建自定义ActiveQuery类，请扩展基础`ActiveQuery`类并添加您的专门方法：

```python
from rhosocial.activerecord.query import ActiveQuery

class UserQuery(ActiveQuery):
    """具有专门查询方法的User模型自定义查询类。"""
    
    def active(self):
        """仅查找活跃用户。"""
        return self.where('status = ?', 'active')
    
    def by_role(self, role):
        """查找具有特定角色的用户。"""
        return self.where('role = ?', role)
    
    def with_recent_orders(self, days=30):
        """包括在最近N天内下订单的用户。"""
        return self.join('JOIN orders ON users.id = orders.user_id')\
                  .where('orders.created_at > NOW() - INTERVAL ? DAY', days)\
                  .group_by('users.id')
```

## 配置模型使用自定义查询类

要将自定义查询类与特定模型一起使用，请在模型类中设置`__query_class__`属性：

```python
from rhosocial.activerecord import ActiveRecord
from .queries import UserQuery

class User(ActiveRecord):
    """带有自定义查询类的用户模型。"""
    
    __table_name__ = 'users'
    __query_class__ = UserQuery  # 指定自定义查询类
    
    # 模型定义继续...
```

通过此配置，调用`User.query()`将返回`UserQuery`的实例，而不是默认的`ActiveQuery`。

## 使用自定义查询方法

配置完成后，您可以直接使用自定义查询方法：

```python
# 查找活跃用户
active_users = User.query().active().all()

# 查找管理员
admins = User.query().by_role('admin').all()

# 查找有近期订单的用户
recent_customers = User.query().with_recent_orders(7).all()

# 链接自定义和标准方法
results = User.query()\
    .active()\
    .by_role('customer')\
    .with_recent_orders()\
    .order_by('name')\
    .limit(10)\
    .all()
```

## 最佳实践

1. **保持方法链接**：始终从自定义查询方法返回`self`以支持方法链接。

2. **文档查询方法**：为自定义查询方法提供清晰的文档字符串，以解释其目的和参数。

3. **保持方法专注**：每个查询方法应该有单一的责任和明确的目的。

4. **考虑查询组合**：设计可以与其他查询方法有效组合的方法。

5. **重用常见模式**：如果多个模型共享类似的查询模式，考虑使用混入而不是复制代码。

## 高级示例：查询类层次结构

对于复杂的应用程序，您可能会创建查询类的层次结构：

```python
# 具有通用方法的基础查询类
class AppBaseQuery(ActiveQuery):
    def active_records(self):
        return self.where('is_active = ?', True)

# 部门特定的查询类
class DepartmentQuery(AppBaseQuery):
    def with_manager(self):
        return self.join('JOIN users ON departments.manager_id = users.id')\
                  .select('departments.*', 'users.name AS manager_name')

# 用户特定的查询类
class UserQuery(AppBaseQuery):
    def by_department(self, department_id):
        return self.where('department_id = ?', department_id)
```

然后配置您的模型使用适当的查询类：

```python
class Department(ActiveRecord):
    __query_class__ = DepartmentQuery
    # ...

class User(ActiveRecord):
    __query_class__ = UserQuery
    # ...
```

## 结论

自定义ActiveQuery类提供了一种强大的方式来组织和封装模型特定的查询逻辑。通过创建专用的查询类，您可以使代码更易于维护，提高可读性，并为使用模型提供更直观的API。