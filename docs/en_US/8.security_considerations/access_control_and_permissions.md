# Access Control and Permissions

Implementing proper access control and permission management is essential for securing your database applications. This document outlines strategies and best practices for implementing access control when using rhosocial ActiveRecord.

## Levels of Access Control

Access control can be implemented at multiple levels:

1. **Database Level**: Permissions enforced by the database system itself
2. **Application Level**: Permissions enforced by your application code
3. **ORM Level**: Permissions enforced through rhosocial ActiveRecord

## Database-Level Access Control

### User Permissions

Most database systems allow you to create users with specific permissions:

```sql
-- Example for PostgreSQL
CREATE USER app_readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

CREATE USER app_readwrite WITH PASSWORD 'different_secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;
```

In your rhosocial ActiveRecord configuration, you can use different connection settings based on the required access level:

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

# Use different connections based on operation needs
read_only_connection = Connection(read_only_config)
read_write_connection = Connection(read_write_config)
```

### Row-Level Security (RLS)

Some databases like PostgreSQL support Row-Level Security, which allows you to define policies that restrict which rows a user can access:

```sql
-- Enable RLS on a table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create a policy that users can only see their own documents
CREATE POLICY user_documents ON documents
    USING (user_id = current_user_id());
```

To use RLS with rhosocial ActiveRecord, you'll need to set the current user context in your database session:

```python
class Document(ActiveRecord):
    @classmethod
    def set_user_context(cls, connection, user_id):
        # Set the user context for the current session
        connection.execute("SET LOCAL my_app.current_user_id = ?", [user_id])
    
    @classmethod
    def get_documents(cls, user_id):
        connection = cls.get_connection()
        # Set the user context before querying
        cls.set_user_context(connection, user_id)
        # RLS will automatically filter results based on the policy
        return cls.objects.all()
```

## Application-Level Access Control

### Role-Based Access Control (RBAC)

Implementing RBAC in your application:

```python
class User(ActiveRecord):
    # User model fields
    # ...
    
    def has_permission(self, permission_name):
        # Query to check if user has the specified permission
        return Permission.objects.filter(
            role__users__id=self.id,
            name=permission_name
        ).exists()

class Role(ActiveRecord):
    # Role model fields
    # ...

class Permission(ActiveRecord):
    # Permission model fields
    # ...

# Usage example
def update_document(user, document_id, new_content):
    if not user.has_permission('document:edit'):
        raise PermissionError("User does not have permission to edit documents")
    
    document = Document.objects.get(id=document_id)
    document.content = new_content
    document.save()
```

### Object-Level Permissions

Implementing permissions for specific objects:

```python
class Document(ActiveRecord):
    # Document model fields
    # ...
    
    def user_can_access(self, user, permission_type):
        # Check if user is the owner
        if self.owner_id == user.id:
            return True
        
        # Check if user has been granted specific access to this document
        return DocumentPermission.objects.filter(
            document_id=self.id,
            user_id=user.id,
            permission_type=permission_type
        ).exists()

class DocumentPermission(ActiveRecord):
    # Fields to track user permissions on specific documents
    # ...
```

## ORM-Level Access Control

### Query Filtering

Automatically filtering queries based on user permissions:

```python
class UserScopedActiveQuery(ActiveQuery):
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.current_user:
            # Add user-specific filters
            queryset = queryset.filter(user_id=self.current_user.id)
        return queryset

class UserDocument(ActiveRecord):
    # Use custom query class
    objects = UserScopedActiveQuery()
    
    @classmethod
    def for_user(cls, user):
        # Return a query manager scoped to the specific user
        return cls.objects.with_user(user)
```

### Attribute-Based Access Control

Implementing attribute-based access control in your models:

```python
class SecureModel(ActiveRecord):
    def __init__(self, *args, **kwargs):
        self._accessible_fields = set()
        self._current_user = None
        super().__init__(*args, **kwargs)
    
    def set_current_user(self, user):
        self._current_user = user
        # Determine which fields this user can access
        self._accessible_fields = self._get_accessible_fields_for_user(user)
    
    def _get_accessible_fields_for_user(self, user):
        # Implement your logic to determine which fields are accessible
        # based on user roles, permissions, etc.
        if user.is_admin:
            return set(self._meta.fields.keys())  # Admin can access all fields
        else:
            # Regular users can only access non-sensitive fields
            return {f for f in self._meta.fields.keys() if not f.startswith('sensitive_')}
    
    def __getattribute__(self, name):
        # Special handling for attribute access
        if name.startswith('_') or name in ('set_current_user', '_get_accessible_fields_for_user'):
            return super().__getattribute__(name)
        
        # Check if attribute is accessible to current user
        accessible_fields = super().__getattribute__('_accessible_fields')
        current_user = super().__getattribute__('_current_user')
        
        if current_user and name in self._meta.fields and name not in accessible_fields:
            raise PermissionError(f"User does not have permission to access field '{name}'")
        
        return super().__getattribute__(name)
```

## Best Practices

1. **Principle of Least Privilege**: Grant only the minimum permissions necessary for each user or component.

2. **Defense in Depth**: Implement access controls at multiple levels (database, application, ORM).

3. **Centralize Authorization Logic**: Create a central authorization service or module rather than scattering permission checks throughout your code.

4. **Audit Access**: Log access attempts, especially for sensitive operations or data.

5. **Regular Permission Reviews**: Periodically review and clean up permissions to prevent permission creep.

6. **Use Environment-Specific Configurations**: Different environments (development, testing, production) should have different permission settings.

7. **Secure by Default**: Start with everything locked down and only open access as needed.

## Example: Complete Access Control Implementation

Here's a more complete example combining multiple approaches:

```python
from rhosocial.activerecord import ActiveRecord, ActiveQuery
from rhosocial.activerecord.backend import Connection
import os

# Define permission constants
PERM_READ = 'read'
PERM_WRITE = 'write'
PERM_ADMIN = 'admin'

# Custom query class that enforces permissions
class PermissionedQuery(ActiveQuery):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.permission = kwargs.pop('permission', PERM_READ)
        super().__init__(*args, **kwargs)
    
    def with_user(self, user):
        # Create a new query with the user set
        query = self._clone()
        query.user = user
        return query
    
    def with_permission(self, permission):
        # Create a new query with the permission set
        query = self._clone()
        query.permission = permission
        return query
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.user:
            if self.user.is_admin:
                # Admins can see everything
                return queryset
            
            # Apply permission filters based on user and required permission
            if self.permission == PERM_READ:
                # For read permission, user can see public records and their own
                return queryset.filter(Q(is_public=True) | Q(owner_id=self.user.id))
            elif self.permission == PERM_WRITE:
                # For write permission, user can only see their own records
                return queryset.filter(owner_id=self.user.id)
            else:
                # For any other permission, deny access by default
                return queryset.filter(id=-1)  # This will return empty queryset
        
        # If no user is set, only show public records
        return queryset.filter(is_public=True)

# Base model with permission handling
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
            raise PermissionError(f"User {user.id} does not have permission to save this {self.__class__.__name__}")
        super().save(*args, **kwargs)

# Example usage
class Document(PermissionedModel):
    title = Field(str)
    content = Field(str)
    is_public = Field(bool, default=False)
    owner_id = Field(int)

# Application code
def view_document(user, document_id):
    try:
        # This will automatically filter based on permissions
        document = Document.viewable_by(user).get(id=document_id)
        return document
    except Document.DoesNotExist:
        raise PermissionError("Document not found or you don't have permission to view it")

def update_document(user, document_id, new_content):
    try:
        # This will automatically filter based on permissions
        document = Document.editable_by(user).get(id=document_id)
        document.content = new_content
        document.save(user=user)  # Pass user to save method for permission check
        return document
    except Document.DoesNotExist:
        raise PermissionError("Document not found or you don't have permission to edit it")
```

## Conclusion

Implementing robust access control is crucial for securing your database applications. rhosocial ActiveRecord provides the flexibility to implement various access control strategies at different levels.

By combining database-level permissions, application-level role-based access control, and ORM-level query filtering, you can create a comprehensive security model that protects your data while providing appropriate access to authorized users.

Remember that security is an ongoing process. Regularly review and update your access control mechanisms to address new requirements and potential vulnerabilities.