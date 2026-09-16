# Character Set / Encoding

## Overview

Correctly configuring character sets is essential for handling multilingual text, emojis, and ensuring sorting behavior meets expectations. {database} supports multiple character sets and collations.

## Common Character Sets

| Character Set | Description | Emoji Support |
|--------------|-------------|---------------|
| utf8mb4 | UTF-8 encoding, up to 4 bytes | ✅ Supported |
| utf8 | UTF-8 encoding, up to 3 bytes | ❌ Not supported |

## Configuration Methods

### 1. Connection-Level Configuration

Specify character set when creating the backend:

```python
backend = {Backend}Backend(
    host='localhost',
    port={port},
    database='myapp',
    username='user',
    password='password',
    charset='utf8mb4',
)
```

### 2. Database-Level Configuration

```sql
CREATE DATABASE myapp CHARACTER SET utf8mb4;
```

### 3. Table-Level Configuration

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255)
) DEFAULT CHARSET=utf8mb4;
```

## Best Practices

1. **Unify Character Set**: Use `utf8mb4` consistently across database, tables, and columns to avoid conversion issues
2. **Choose Appropriate Collation**: For Chinese applications, consult {database}-specific collation options
3. **Note Index Length**: Some databases have index length limits when using multi-byte character sets

💡 *AI Prompt:* "What is the difference between character set and collation?"
