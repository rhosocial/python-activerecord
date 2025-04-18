# Schema Change Management

## Introduction

Database schema changes are an inevitable part of application development. As your application evolves, you'll need to add new tables, modify existing columns, or restructure relationships. rhosocial ActiveRecord provides a systematic approach to manage these changes through migration scripts.

## Migration Basics

### What is a Migration?

A migration is a versioned change to your database schema that can be applied or reverted as needed. Migrations in rhosocial ActiveRecord are Python scripts that define transformations to your database structure.

### Migration File Structure

A typical migration file includes:

```python
from rhosocial.activerecord.migration import Migration

class AddUserTable(Migration):
    """Migration to add the user table."""
    
    def up(self):
        """Apply the migration."""
        self.create_table('user', [
            self.column('id', 'integer', primary_key=True, auto_increment=True),
            self.column('username', 'string', length=64, null=False, unique=True),
            self.column('email', 'string', length=255, null=False),
            self.column('created_at', 'datetime'),
            self.column('updated_at', 'datetime')
        ])
        
        self.create_index('user', 'email')
    
    def down(self):
        """Revert the migration."""
        self.drop_table('user')
```

## Managing Migrations

### Creating a New Migration

To create a new migration, use the migration generator command:

```bash
python -m rhosocial.activerecord.migration create add_user_table
```

This creates a timestamped migration file in your migrations directory.

### Applying Migrations

To apply pending migrations:

```bash
python -m rhosocial.activerecord.migration up
```

To apply a specific number of migrations:

```bash
python -m rhosocial.activerecord.migration up 3
```

### Reverting Migrations

To revert the most recent migration:

```bash
python -m rhosocial.activerecord.migration down
```

To revert a specific number of migrations:

```bash
python -m rhosocial.activerecord.migration down 3
```

### Checking Migration Status

To see which migrations have been applied and which are pending:

```bash
python -m rhosocial.activerecord.migration status
```

## Best Practices for Schema Changes

### 1. Make Migrations Reversible

Whenever possible, ensure that your migrations can be reverted by implementing both `up()` and `down()` methods.

### 2. Keep Migrations Small and Focused

Each migration should handle a single logical change to your schema. This makes migrations easier to understand, test, and troubleshoot.

### 3. Use Database-Agnostic Operations

Use the migration API's database-agnostic methods rather than raw SQL when possible. This ensures your migrations work across different database backends.

### 4. Test Migrations Before Deployment

Always test migrations in a development or staging environment before applying them to production.

### 5. Version Control Your Migrations

Migrations should be committed to version control along with your application code.

## Common Schema Change Operations

### Creating Tables

```python
def up(self):
    self.create_table('product', [
        self.column('id', 'integer', primary_key=True, auto_increment=True),
        self.column('name', 'string', length=128, null=False),
        self.column('price', 'decimal', precision=10, scale=2, null=False),
        self.column('description', 'text'),
        self.column('category_id', 'integer'),
        self.column('created_at', 'datetime'),
        self.column('updated_at', 'datetime')
    ])
```

### Adding Columns

```python
def up(self):
    self.add_column('user', 'last_login_at', 'datetime', null=True)
```

### Modifying Columns

```python
def up(self):
    self.change_column('product', 'price', 'decimal', precision=12, scale=4)
```

### Creating Indexes

```python
def up(self):
    self.create_index('product', 'category_id')
    self.create_index('product', ['name', 'category_id'], unique=True)
```

### Adding Foreign Keys

```python
def up(self):
    self.add_foreign_key('product', 'category_id', 'category', 'id', on_delete='CASCADE')
```

## Handling Complex Schema Changes

For complex schema changes that involve data transformations, you may need to combine schema changes with data migration steps:

```python
def up(self):
    # 1. Add new column
    self.add_column('user', 'full_name', 'string', length=255, null=True)
    
    # 2. Migrate data (using raw SQL for complex transformations)
    self.execute("UPDATE user SET full_name = CONCAT(first_name, ' ', last_name)")
    
    # 3. Make the column non-nullable after data is migrated
    self.change_column('user', 'full_name', 'string', length=255, null=False)
    
    # 4. Remove old columns
    self.remove_column('user', 'first_name')
    self.remove_column('user', 'last_name')
```

## Database-Specific Considerations

While rhosocial ActiveRecord aims to provide database-agnostic migrations, some operations may have database-specific behaviors. Consult the documentation for your specific database backend for details on how certain operations are implemented.

## Conclusion

Effective schema change management is crucial for maintaining database integrity while allowing your application to evolve. By following the patterns and practices outlined in this guide, you can implement database changes in a controlled, reversible manner that minimizes risk and downtime.