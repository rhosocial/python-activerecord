# 访问控制与权限

实施适当的访问控制和权限管理对于保护数据库应用程序至关重要。本文档概述了使用rhosocial ActiveRecord实施访问控制的策略和最佳实践。

## 访问控制级别

访问控制可以在多个级别实施：

1. **数据库级别**：由数据库系统本身强制执行的权限
2. **应用程序级别**：由应用程序代码强制执行的权限
3. **ORM级别**：通过rhosocial ActiveRecord强制执行的权限

## 数据库级别访问控制

### 用户权限

大多数数据库系统允许您创建具有特定权限的用户：

```sql
-- PostgreSQL示例
CREATE USER app_readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

CREATE USER app_readwrite WITH PASSWORD 'different_secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;
```

在rhosocial ActiveRecord配置中，您可以根据所需的访问级别使用不同的连接设置：

```python
read_only_config = {
    'host': 'database.example.com',
    'user': 'app_readonly',
    'password': os.environ.get('DB_READONLY_PASSWORD'),
    'database': 'myapp'
}

read_write_config = {
    'host': 'database.example.com',
    'user': 'app_readwrite',
    'password': os.environ.get('DB_READWRITE_PASSWORD'),
    'database': 'myapp'
}

# 根据操作需求使用不同的连接
read_only_connection = Connection(read_only_config)
read_write_connection = Connection(read_write_config)
```

### 行级安全性（RLS）

一些数据库（如PostgreSQL）支持行级安全性，允许您定义限制用户可以访问哪些行的策略：

```sql
-- 在表上启用RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- 创建一个策略，用户只能看到自己的文档
CREATE POLICY user_documents ON documents
    USING (user_id = current_user_id());
```

要在rhosocial ActiveRecord中使用RLS，您需要在数据库会话中设置当前用户上下文：

```python
class Document(ActiveRecord):
    @classmethod
    def set_user_context(cls, connection, user_id):
        # 为当前会话设置用户上下文
        connection.execute("SET LOCAL my_app.current_user_id = ?", [user_id])
    
    @classmethod
    def get_documents(cls, user_id):
        connection = cls.get_connection()
        # 在查询前设置用户上下文
        cls.set_user_context(connection, user_id)
        # RLS将根据策略自动过滤结果
        return cls.objects.all()
```

## 应用程序级别访问控制

### 基于角色的访问控制（RBAC）

在应用程序中实施RBAC：

```python
class User(ActiveRecord):
    # 用户模型字段
    # ...
    
    def has_permission(self, permission_name):
        # 查询检查用户是否具有指定权限
        return Permission.objects.filter(
            role__users__id=self.id,
            name=permission_name
        ).exists()

class Role(ActiveRecord):
    # 角色模型字段
    # ...

class Permission(ActiveRecord):
    # 权限模型字段
    # ...

# 使用示例
def update_document(user, document_id, new_content):
    if not user.has_permission('document:edit'):
        raise PermissionError("用户没有编辑文档的权限")
    
    document = Document.objects.get(id=document_id)
    document.content = new_content
    document.save()
```

### 对象级权限

实施特定对象的权限：

```python
class Document(ActiveRecord):
    # 文档模型字段
    # ...
    
    def user_can_access(self, user, permission_type):
        # 检查用户是否是所有者
        if self.owner_id == user.id:
            return True
        
        # 检查用户是否被授予对此文档的特定访问权限
        return DocumentPermission.objects.filter(
            document_id=self.id,
            user_id=user.id,
            permission_type=permission_type
        ).exists()

class DocumentPermission(ActiveRecord):
    # 跟踪用户对特定文档的权限的字段
    # ...
```

## ORM级别访问控制

### 查询过滤

基于用户权限自动过滤查询：

```python
class UserScopedActiveQuery(ActiveQuery):
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.current_user:
            # 添加用户特定的过滤器
            queryset = queryset.filter(user_id=self.current_user.id)
        return queryset

class UserDocument(ActiveRecord):
    # 使用自定义查询类
    objects = UserScopedActiveQuery()
    
    @classmethod
    def for_user(cls, user):
        # 返回特定用户范围的查询管理器
        return cls.objects.with_user(user)
```

### 基于属性的访问控制

在模型中实施基于属性的访问控制：

```python
class SecureModel(ActiveRecord):
    def __init__(self, *args, **kwargs):
        self._accessible_fields = set()
        self._current_user = None
        super().__init__(*args, **kwargs)
    
    def set_current_user(self, user):
        self._current_user = user
        # 确定此用户可以访问哪些字段
        self._accessible_fields = self._get_accessible_fields_for_user(user)
    
    def _get_accessible_fields_for_user(self, user):
        # 实现您的逻辑，根据用户角色、权限等确定哪些字段可访问
        if user.is_admin:
            return set(self._meta.fields.keys())  # 管理员可以访问所有字段
        else:
            # 普通用户只能访问非敏感字段
            return {f for f in self._meta.fields.keys() if not f.startswith('sensitive_')}
    
    def __getattribute__(self, name):
        # 属性访问的特殊处理
        if name.startswith('_') or name in ('set_current_user', '_get_accessible_fields_for_user'):
            return super().__getattribute__(name)
        
        # 检查当前用户是否可以访问属性
        accessible_fields = super().__getattribute__('_accessible_fields')
        current_user = super().__getattribute__('_current_user')
        
        if current_user and name in self._meta.fields and name not in accessible_fields:
            raise PermissionError(f"用户没有权限访问字段 '{name}'")
        
        return super().__getattribute__(name)
```

## 最佳实践

1. **最小权限原则**：只为每个用户或组件授予必要的最小权限。

2. **纵深防御**：在多个级别（数据库、应用程序、ORM）实施访问控制。

3. **集中授权逻辑**：创建中央授权服务或模块，而不是在代码中分散权限检查。

4. **审计访问**：记录访问尝试，特别是对敏感操作或数据的访问。

5. **定期权限审查**：定期审查和清理权限，防止权限蔓延。

6. **使用环境特定配置**：不同环境（开发、测试、生产）应有不同的权限设置。

7. **默认安全**：从一切锁定开始，只在需要时开放访问。

## 示例：完整的访问控制实现

这是一个结合多种方法的更完整示例：

```python
from rhosocial.activerecord import ActiveRecord, ActiveQuery
from rhosocial.activerecord.backend import Connection
import os

# 定义权限常量
PERM_READ = 'read'
PERM_WRITE = 'write'
PERM_ADMIN = 'admin'

# 强制执行权限的自定义查询类
class PermissionedQuery(ActiveQuery):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.permission = kwargs.pop('permission', PERM_READ)
        super().__init__(*args, **kwargs)
    
    def with_user(self, user):
        # 创建设置了用户的新查询
        query = self._clone()
        query.user = user
        return query
    
    def with_permission(self, permission):
        # 创建设置了权限的新查询
        query = self._clone()
        query.permission = permission
        return query
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.user:
            if self.user.is_admin:
                # 管理员可以看到所有内容
                return queryset
            
            # 根据用户和所需权限应用权限过滤器
            if self.permission == PERM_READ:
                # 对于读取权限，用户可以看到公共记录和自己的记录
                return queryset.filter(Q(is_public=True) | Q(owner_id=self.user.id))
            elif self.permission == PERM_WRITE:
                # 对于写入权限，用户只能看到自己的记录
                return queryset.filter(owner_id=self.user.id)
            else:
                # 对于任何其他权限，默认拒绝访问
                return queryset.filter(id=-1)  # 这将返回空查询集
        
        # 如果未设置用户，则只显示公共记录
        return queryset.filter(is_public=True)

# 带有权限处理的基础模型
class PermissionedModel(ActiveRecord):
    objects = PermissionedQuery()
    
    @classmethod
    def viewable_by(cls, user):
        return cls.objects.with_user(user).with_permission(PERM_READ)
    
    @classmethod
    def editable_by(cls, user):
        return cls.objects.with_user(user).with_permission(PERM_WRITE)
    
    def user_can_view(self, user):
        if user.is_admin or self.is_public:
            return True
        return self.owner_id == user.id
    
    def user_can_edit(self, user):
        if user.is_admin:
            return True
        return self.owner_id == user.id
    
    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user and not self.user_can_edit(user):
            raise PermissionError(f"用户 {user.id} 没有权限保存此 {self.__class__.__name__}")
        super().save(*args, **kwargs)

# 使用示例
class Document(PermissionedModel):
    title = Field(str)
    content = Field(str)
    is_public = Field(bool, default=False)
    owner_id = Field(int)

# 应用程序代码
def view_document(user, document_id):
    try:
        # 这将根据权限自动过滤
        document = Document.viewable_by(user).get(id=document_id)
        return document
    except Document.DoesNotExist:
        raise PermissionError("文档未找到或您没有查看权限")

def update_document(user, document_id, new_content):
    try:
        # 这将根据权限自动过滤
        document = Document.editable_by(user).get(id=document_id)
        document.content = new_content
        document.save(user=user)  # 将用户传递给save方法进行权限检查
        return document
    except Document.DoesNotExist:
        raise PermissionError("文档未找到或您没有编辑权限")
```

## 结论

实施强大的访问控制对于保护数据库应用程序至关重要。rhosocial ActiveRecord提供了在不同级别实施各种访问控制策略的灵活性。

通过结合数据库级别权限、应用程序级别基于角色的访问控制和ORM级别查询过滤，您可以创建一个全面的安全模型，保护您的数据同时为授权用户提供适当的访问。

请记住，安全是一个持续的过程。定期审查和更新您的访问控制机制，以解决新的需求和潜在的漏洞。