# Lifecycle Hooks

This document explains how to use lifecycle hooks in your ActiveRecord models. Lifecycle hooks allow you to execute custom code at specific points in a model's lifecycle, such as before or after saving, updating, or deleting records.

## Overview

rhosocial ActiveRecord provides a comprehensive event system that allows you to hook into various stages of a model's lifecycle. This enables you to implement custom behavior, such as:

- Data transformation before saving
- Validation beyond basic field validation
- Automatic field updates
- Logging and auditing
- Triggering side effects (e.g., sending notifications)

## Available Lifecycle Events

The following lifecycle events are available in ActiveRecord models:

| Event | Timing | Use Case |
|-------|--------|----------|
| `BEFORE_VALIDATE` | Before validation is performed | Pre-process data before validation |
| `AFTER_VALIDATE` | After successful validation | Perform actions that depend on valid data |
| `BEFORE_SAVE` | Before a record is saved (created or updated) | Last chance to modify data before it's saved |
| `AFTER_SAVE` | After a record is successfully saved | Perform actions that depend on the saved state |
| `BEFORE_CREATE` | Before a new record is created | Set default values or generate data for new records |
| `AFTER_CREATE` | After a new record is successfully created | Actions specific to new records (e.g., welcome emails) |
| `BEFORE_UPDATE` | Before an existing record is updated | Prepare data for update or check conditions |
| `AFTER_UPDATE` | After an existing record is successfully updated | React to changes in the record |
| `BEFORE_DELETE` | Before a record is deleted | Perform cleanup or check if deletion is allowed |
| `AFTER_DELETE` | After a record is successfully deleted | Cleanup related data or notify about deletion |

## Registering Event Handlers

### Using the `on()` Method

The most common way to register event handlers is using the `on()` method:

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
        
        # Register event handlers
        self.on(ModelEvent.BEFORE_SAVE, self.normalize_email)
        self.on(ModelEvent.AFTER_CREATE, self.send_welcome_email)
    
    def normalize_email(self, event):
        """Normalize email address before saving."""
        if self.email:
            self.email = self.email.lower().strip()
    
    def send_welcome_email(self, event):
        """Send welcome email after user creation."""
        # Implementation of sending welcome email
        print(f"Sending welcome email to {self.email}")
```

### Class-Level Event Handlers

You can also register class-level event handlers that apply to all instances:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent

class AuditableMixin(ActiveRecord):
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        
        # Register class-level event handlers
        cls.on_class(ModelEvent.BEFORE_CREATE, cls.set_timestamps)
        cls.on_class(ModelEvent.BEFORE_UPDATE, cls.update_timestamps)
    
    @classmethod
    def set_timestamps(cls, instance, event):
        """Set both timestamps on new record creation."""
        now = datetime.now()
        instance.created_at = now
        instance.updated_at = now
    
    @classmethod
    def update_timestamps(cls, instance, event):
        """Update the updated_at timestamp on record update."""
        instance.updated_at = datetime.now()
```

## Event Handler Signature

Event handlers can have different signatures depending on whether they are instance methods, class methods, or standalone functions:

### Instance Method Handlers

```python
def handler_method(self, event):
    # self is the model instance
    # event is the ModelEvent that triggered this handler
    pass
```

### Class Method Handlers

```python
@classmethod
def handler_method(cls, instance, event):
    # cls is the model class
    # instance is the model instance that triggered the event
    # event is the ModelEvent that triggered this handler
    pass
```

### Standalone Function Handlers

```python
def handler_function(instance, event):
    # instance is the model instance that triggered the event
    # event is the ModelEvent that triggered this handler
    pass
```

## Practical Examples

### Automatic Slug Generation

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
        """Generate a URL-friendly slug from the title."""
        if not self.slug and self.title:
            # Convert to lowercase, replace spaces with hyphens, remove special chars
            self.slug = re.sub(r'[^\w\s-]', '', self.title.lower())
            self.slug = re.sub(r'[\s_]+', '-', self.slug)
```

### Cascading Deletes

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
        """Delete all comments associated with this post."""
        from .comment import Comment  # Import here to avoid circular imports
        Comment.query().where(post_id=self.id).delete_all()
```

### Data Encryption

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
    content: str  # This will store encrypted content
    _raw_content: str = None  # Temporary storage for unencrypted content
    
    def __init__(self, **data):
        if 'content' in data and data['content']:
            # Store unencrypted content temporarily
            self._raw_content = data['content']
            # Remove from data to prevent it from being set directly
            data['content'] = None
        
        super().__init__(**data)
        
        self.on(ModelEvent.BEFORE_SAVE, self.encrypt_content)
        self.on(ModelEvent.AFTER_FIND, self.decrypt_content)
    
    def encrypt_content(self, event):
        """Encrypt content before saving to database."""
        if self._raw_content:
            # Implementation of encryption
            key = self._get_encryption_key()
            f = Fernet(key)
            self.content = f.encrypt(self._raw_content.encode()).decode()
            self._raw_content = None
    
    def decrypt_content(self, event):
        """Decrypt content after loading from database."""
        if self.content:
            # Implementation of decryption
            key = self._get_encryption_key()
            f = Fernet(key)
            self._raw_content = f.decrypt(self.content.encode()).decode()
    
    def _get_encryption_key(self):
        """Generate or retrieve encryption key."""
        # This is a simplified example - in a real app, you'd need proper key management
        password = os.environ.get('ENCRYPTION_KEY', 'default-key').encode()
        salt = b'static-salt'  # In a real app, use a unique salt per record
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
```

## Advanced Usage

### Event Propagation

Events propagate through the inheritance chain, allowing parent classes to handle events triggered by child classes. This is useful for implementing common behavior in base classes or mixins.

### Multiple Handlers

You can register multiple handlers for the same event. They will be executed in the order they were registered.

```python
class User(ActiveRecord):
    # ... fields ...
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Multiple handlers for the same event
        self.on(ModelEvent.BEFORE_SAVE, self.normalize_email)
        self.on(ModelEvent.BEFORE_SAVE, self.validate_username)
        self.on(ModelEvent.BEFORE_SAVE, self.check_password_strength)
```

### Removing Handlers

You can remove previously registered handlers using the `off()` method:

```python
# Remove a specific handler
self.off(ModelEvent.BEFORE_SAVE, self.normalize_email)

# Remove all handlers for an event
self.off(ModelEvent.BEFORE_SAVE)
```

### One-Time Handlers

You can register handlers that will be executed only once and then automatically removed:

```python
# Register a one-time handler
self.once(ModelEvent.AFTER_SAVE, self.send_confirmation)
```

## Best Practices

1. **Keep Handlers Focused**: Each handler should have a single responsibility.

2. **Handle Exceptions**: Event handlers should handle exceptions gracefully to prevent disrupting the model's lifecycle.

3. **Avoid Heavy Operations**: For performance-critical code, consider moving heavy operations to background jobs.

4. **Use Mixins for Common Behavior**: Extract common lifecycle behavior into mixins for reuse across models.

5. **Be Careful with Side Effects**: Lifecycle hooks can have side effects that might not be immediately obvious. Document them clearly.

6. **Test Your Hooks**: Write unit tests specifically for your lifecycle hooks to ensure they behave as expected.

## Conclusion

Lifecycle hooks are a powerful feature of rhosocial ActiveRecord that allow you to customize the behavior of your models at various points in their lifecycle. By leveraging these hooks, you can implement complex business logic, automate repetitive tasks, and ensure data consistency throughout your application.