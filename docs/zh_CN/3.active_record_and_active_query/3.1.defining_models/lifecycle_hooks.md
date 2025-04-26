# 生命周期钩子

本文档解释了如何在ActiveRecord模型中使用生命周期钩子。生命周期钩子允许您在模型生命周期的特定点执行自定义代码，例如在保存、更新或删除记录之前或之后。

## 概述

rhosocial ActiveRecord提供了一个全面的事件系统，允许您挂接到模型生命周期的各个阶段。这使您能够实现自定义行为，例如：

- 保存前的数据转换
- 超出基本字段验证的验证
- 自动字段更新
- 日志记录和审计
- 触发副作用（例如，发送通知）

## 可用的生命周期事件

ActiveRecord模型中提供以下生命周期事件：

| 事件 | 时机 | 用例 |
|-------|--------|----------|
| `BEFORE_VALIDATE` | 执行验证之前 | 在验证之前预处理数据 |
| `AFTER_VALIDATE` | 成功验证之后 | 执行依赖于有效数据的操作 |
| `BEFORE_SAVE` | 记录保存（创建或更新）之前 | 在数据保存之前修改数据的最后机会 |
| `AFTER_SAVE` | 记录成功保存之后 | 执行依赖于已保存状态的操作 |
| `BEFORE_CREATE` | 创建新记录之前 | 为新记录设置默认值或生成数据 |
| `AFTER_CREATE` | 新记录成功创建之后 | 特定于新记录的操作（例如，欢迎邮件） |
| `BEFORE_UPDATE` | 更新现有记录之前 | 准备更新数据或检查条件 |
| `AFTER_UPDATE` | 现有记录成功更新之后 | 对记录变化做出反应 |
| `BEFORE_DELETE` | 删除记录之前 | 执行清理或检查是否允许删除 |
| `AFTER_DELETE` | 记录成功删除之后 | 清理相关数据或通知删除 |

## 注册事件处理程序

### 使用`on()`方法

注册事件处理程序最常见的方式是使用`on()`方法：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent

class User(ActiveRecord):
    id: int
    username: str
    email: str
    last_login: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 注册事件处理程序
        self.on(ModelEvent.BEFORE_SAVE, self.normalize_email)
        self.on(ModelEvent.AFTER_CREATE, self.send_welcome_email)
    
    def normalize_email(self, event):
        """保存前规范化电子邮件地址。"""
        if self.email:
            self.email = self.email.lower().strip()
    
    def send_welcome_email(self, event):
        """用户创建后发送欢迎邮件。"""
        # 发送欢迎邮件的实现
        print(f"向{self.email}发送欢迎邮件")
```

### 类级别事件处理程序

您还可以注册适用于所有实例的类级别事件处理程序：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent

class AuditableMixin(ActiveRecord):
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        
        # 注册类级别事件处理程序
        cls.on_class(ModelEvent.BEFORE_CREATE, cls.set_timestamps)
        cls.on_class(ModelEvent.BEFORE_UPDATE, cls.update_timestamps)
    
    @classmethod
    def set_timestamps(cls, instance, event):
        """在新记录创建时设置两个时间戳。"""
        now = datetime.now()
        instance.created_at = now
        instance.updated_at = now
    
    @classmethod
    def update_timestamps(cls, instance, event):
        """在记录更新时更新updated_at时间戳。"""
        instance.updated_at = datetime.now()
```

## 事件处理程序签名

事件处理程序可以有不同的签名，取决于它们是实例方法、类方法还是独立函数：

### 实例方法处理程序

```python
def handler_method(self, event):
    # self是模型实例
    # event是触发此处理程序的ModelEvent
    pass
```

### 类方法处理程序

```python
@classmethod
def handler_method(cls, instance, event):
    # cls是模型类
    # instance是触发事件的模型实例
    # event是触发此处理程序的ModelEvent
    pass
```

### 独立函数处理程序

```python
def handler_function(instance, event):
    # instance是触发事件的模型实例
    # event是触发此处理程序的ModelEvent
    pass
```

## 实际示例

### 自动生成别名

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent
import re

class Article(ActiveRecord):
    id: int
    title: str
    slug: Optional[str] = None
    content: str
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_VALIDATE, self.generate_slug)
    
    def generate_slug(self, event):
        """从标题生成URL友好的别名。"""
        if not self.slug and self.title:
            # 转换为小写，用连字符替换空格，删除特殊字符
            self.slug = re.sub(r'[^\w\s-]', '', self.title.lower())
            self.slug = re.sub(r'[\s_]+', '-', self.slug)
```

### 级联删除

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent

class Post(ActiveRecord):
    id: int
    title: str
    content: str
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.AFTER_DELETE, self.delete_comments)
    
    def delete_comments(self, event):
        """删除与此帖子关联的所有评论。"""
        from .comment import Comment  # 在这里导入以避免循环导入
        Comment.query().where(post_id=self.id).delete_all()
```

### 数据加密

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureNote(ActiveRecord):
    id: int
    title: str
    content: str  # 这将存储加密内容
    _raw_content: str = None  # 未加密内容的临时存储
    
    def __init__(self, **data):
        if 'content' in data and data['content']:
            # 临时存储未加密内容
            self._raw_content = data['content']
            # 从数据中删除，防止直接设置
            data['content'] = None
        
        super().__init__(**data)
        
        self.on(ModelEvent.BEFORE_SAVE, self.encrypt_content)
        self.on(ModelEvent.AFTER_FIND, self.decrypt_content)
    
    def encrypt_content(self, event):
        """在保存到数据库之前加密内容。"""
        if self._raw_content:
            # 加密实现
            key = self._get_encryption_key()
            f = Fernet(key)
            self.content = f.encrypt(self._raw_content.encode()).decode()
            self._raw_content = None
    
    def decrypt_content(self, event):
        """从数据库加载后解密内容。"""
        if self.content:
            # 解密实现
            key = self._get_encryption_key()
            f = Fernet(key)
            self._raw_content = f.decrypt(self.content.encode()).decode()
    
    def _get_encryption_key(self):
        """生成或检索加密密钥。"""
        # 这是一个简化示例 - 在实际应用中，您需要适当的密钥管理
        password = os.environ.get('ENCRYPTION_KEY', 'default-key').encode()
        salt = b'static-salt'  # 在实际应用中，为每条记录使用唯一的盐
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
```

## 高级用法

### 事件传播

事件通过继承链传播，允许父类处理由子类触发的事件。这对于在基类或混入中实现通用行为很有用。

### 多个处理程序

您可以为同一事件注册多个处理程序。它们将按照注册顺序执行。

```python
class User(ActiveRecord):
    # ... 字段 ...
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 同一事件的多个处理程序
        self.on(ModelEvent.BEFORE_SAVE, self.normalize_email)
        self.on(ModelEvent.BEFORE_SAVE, self.validate_username)
        self.on(ModelEvent.BEFORE_SAVE, self.check_password_strength)
```

### 移除处理程序

您可以使用`off()`方法移除先前注册的处理程序：

```python
# 移除特定处理程序
self.off(ModelEvent.BEFORE_SAVE, self.normalize_email)

# 移除事件的所有处理程序
self.off(ModelEvent.BEFORE_SAVE)
```

### 一次性处理程序

您可以注册只执行一次然后自动移除的处理程序：

```python
# 注册一次性处理程序
self.once(ModelEvent.AFTER_SAVE, self.send_confirmation)
```

## 最佳实践

1. **保持处理程序专注**：每个处理程序应该有单一责任。

2. **处理异常**：事件处理程序应该优雅地处理异常，以防止扰乱模型的生命周期。

3. **避免重操作**：对于性能关键的代码，考虑将重操作移至后台作业。

4. **使用混入实现通用行为**：将通用生命周期行为提取到混入中，以便在模型之间重用。

5. **小心副作用**：生命周期钩子可能有不立即明显的副作用。清楚地记录它们。

6. **测试您的钩子**：专门为您的生命周期钩子编写单元测试，以确保它们按预期行为。

## 结论

生命周期钩子是rhosocial ActiveRecord的强大功能，允许您在模型生命周期的各个点自定义模型的行为。通过利用这些钩子，您可以实现复杂的业务逻辑，自动化重复任务，并确保整个应用程序的数据一致性。