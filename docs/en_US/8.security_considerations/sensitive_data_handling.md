# Sensitive Data Handling

Handling sensitive data properly is a critical aspect of application security. This document outlines best practices for managing sensitive data when using rhosocial ActiveRecord.

## What Constitutes Sensitive Data?

Sensitive data typically includes:

- Personal Identifiable Information (PII)
- Authentication credentials (passwords, API keys, tokens)
- Financial information (credit card numbers, bank account details)
- Health information
- Business-sensitive information
- Session identifiers

## Best Practices for Sensitive Data Handling

### 1. Minimize Collection and Storage

- Only collect and store sensitive data that is absolutely necessary
- Implement data retention policies to remove sensitive data when no longer needed
- Consider using data anonymization or pseudonymization where appropriate

### 2. Secure Database Configuration

```python
# Store connection credentials in environment variables, not in code
from os import environ

config = {
    'host': environ.get('DB_HOST'),
    'user': environ.get('DB_USER'),
    'password': environ.get('DB_PASSWORD'),  # Never hardcode passwords
    'database': environ.get('DB_NAME'),
    'ssl_mode': 'require'  # Enable SSL for data in transit
}
```

### 3. Encryption for Sensitive Data

#### Data at Rest

For sensitive fields that need to be stored in the database:

```python
from cryptography.fernet import Fernet
import base64

class User(ActiveRecord):
    # Define encryption key management (preferably using a key management service)
    encryption_key = environ.get('ENCRYPTION_KEY')
    cipher_suite = Fernet(base64.urlsafe_b64encode(encryption_key.ljust(32)[:32].encode()))
    
    # Method to encrypt sensitive data before saving
    def encrypt_sensitive_data(self, data):
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    # Method to decrypt data when retrieved
    def decrypt_sensitive_data(self, encrypted_data):
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    # Override save method to encrypt sensitive fields
    def save(self, *args, **kwargs):
        if self.credit_card_number:  # Only encrypt if the field has a value
            self.credit_card_number = self.encrypt_sensitive_data(self.credit_card_number)
        super().save(*args, **kwargs)
```

#### Data in Transit

- Always use HTTPS/TLS for web applications
- Configure database connections to use SSL/TLS

### 4. Secure Password Handling

Never store plain-text passwords. Use strong hashing algorithms with salting:

```python
import hashlib
import os

class User(ActiveRecord):
    # Method to set password with proper hashing
    def set_password(self, password):
        # Generate a random salt
        salt = os.urandom(32)
        # Hash the password with the salt
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # Number of iterations
        )
        # Store both the salt and the hash
        self.password_salt = salt.hex()
        self.password_hash = password_hash.hex()
    
    # Method to verify password
    def verify_password(self, password):
        salt = bytes.fromhex(self.password_salt)
        stored_hash = bytes.fromhex(self.password_hash)
        # Hash the provided password with the stored salt
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # Same number of iterations as in set_password
        )
        # Compare the computed hash with the stored hash
        return computed_hash == stored_hash
```

### 5. Masking and Redaction

When displaying sensitive data in logs, UIs, or API responses:

```python
class CreditCard(ActiveRecord):
    # Method to get masked credit card number for display
    def get_masked_number(self):
        if not self.card_number:
            return None
        # Only show the last 4 digits
        return f"****-****-****-{self.card_number[-4:]}"
    
    # Override to_dict method to mask sensitive data
    def to_dict(self):
        data = super().to_dict()
        # Replace sensitive fields with masked versions
        if 'card_number' in data:
            data['card_number'] = self.get_masked_number()
        # Remove CVV entirely from dictionary representation
        if 'cvv' in data:
            del data['cvv']
        return data
```

### 6. Logging Considerations

```python
import logging

# Configure logging to avoid sensitive data
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_payment(user, credit_card, amount):
    # DO NOT log sensitive information
    logger.info(f"Processing payment for user {user.id} of amount {amount}")
    # DO NOT do this: logger.info(f"Credit card details: {credit_card.number}, CVV: {credit_card.cvv}")
    
    # Process payment logic here
    
    logger.info(f"Payment processed successfully for user {user.id}")
```

### 7. API Response Security

When returning model data through APIs:

```python
class UserAPI:
    def get_user_data(self, user_id):
        user = User.objects.get(id=user_id)
        
        # Create a sanitized version of user data for API response
        safe_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            # Exclude sensitive fields like password_hash, password_salt
            'last_login': user.last_login,
            'account_type': user.account_type
        }
        
        return safe_data
```

## Database-Level Protection

### Column-Level Encryption

Some databases offer column-level encryption. When available, this can provide an additional layer of security:

```sql
-- Example for PostgreSQL using pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sensitive_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plain_data TEXT,
    encrypted_data BYTEA  -- Will store encrypted data
);
```

In your ActiveRecord model:

```python
class SensitiveData(ActiveRecord):
    # Use raw SQL for encryption/decryption operations
    @classmethod
    def create_with_encrypted_data(cls, user_id, sensitive_data, encryption_key):
        query = """
        INSERT INTO sensitive_data (user_id, plain_data, encrypted_data) 
        VALUES (?, ?, pgp_sym_encrypt(?, ?)) 
        RETURNING id
        """
        result = cls.objects.execute_raw(
            query, 
            [user_id, None, sensitive_data, encryption_key]
        )
        return result[0]['id'] if result else None
    
    @classmethod
    def get_decrypted_data(cls, record_id, encryption_key):
        query = """
        SELECT id, user_id, pgp_sym_decrypt(encrypted_data, ?) as decrypted_data 
        FROM sensitive_data 
        WHERE id = ?
        """
        result = cls.objects.execute_raw(query, [encryption_key, record_id])
        return result[0]['decrypted_data'] if result else None
```

## Compliance Considerations

Depending on your application domain and jurisdiction, you may need to comply with regulations such as:

- GDPR (General Data Protection Regulation)
- HIPAA (Health Insurance Portability and Accountability Act)
- PCI DSS (Payment Card Industry Data Security Standard)
- CCPA (California Consumer Privacy Act)

Ensure your data handling practices meet the requirements of applicable regulations.

## Conclusion

Protecting sensitive data requires a multi-layered approach. rhosocial ActiveRecord provides the flexibility to implement these security measures, but it's up to you to ensure they are properly implemented and maintained.

Regularly review your sensitive data handling practices and stay informed about emerging security threats and best practices.