# SSL/TLS Configuration

## Overview

When the {database} server has a valid CA-signed certificate, clients can connect without specifying SSL parameters — SSL is enabled by default.

## Basic Usage

```python
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend

# When server certificate is signed by a trusted CA, no additional config needed
backend = {Backend}Backend(
    host='db.example.com',
    port={port},
    database='myapp',
    username='user',
    password='password',
)
backend.connect()
```

## SSL Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ssl_ca | str | - | CA certificate path |
| ssl_cert | str | - | Client certificate path |
| ssl_key | str | - | Client private key path |
| ssl_verify_cert | bool | True | Whether to verify server certificate |
| ssl_verify_identity | bool | False | Whether to verify server identity |

## Self-Signed Certificates

For self-signed certificates, additional configuration is required:

```python
config = {Backend}ConnectionConfig(
    host='db.example.com',
    port={port},
    database='myapp',
    username='user',
    password='password',
    ssl_ca='/path/to/self-signed-ca.pem',
    ssl_verify_cert=False,
)

backend = {Backend}Backend(config)
```

💡 *AI Prompt:* "What is the difference between SSL, TLS, and SSH? Why is SSL needed for database connections?"
