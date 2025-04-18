# 敏感数据处理

正确处理敏感数据是应用程序安全的关键方面。本文档概述了使用rhosocial ActiveRecord时管理敏感数据的最佳实践。

## 什么构成敏感数据？

敏感数据通常包括：

- 个人身份信息（PII）
- 认证凭证（密码、API密钥、令牌）
- 财务信息（信用卡号码、银行账户详情）
- 健康信息
- 商业敏感信息
- 会话标识符

## 敏感数据处理的最佳实践

### 1. 最小化收集和存储

- 只收集和存储绝对必要的敏感数据
- 实施数据保留策略，在不再需要敏感数据时删除它
- 考虑在适当的情况下使用数据匿名化或假名化

### 2. 安全的数据库配置

```python
# 将连接凭证存储在环境变量中，而不是代码中
from os import environ

config = {
    'host': environ.get('DB_HOST'),
    'user': environ.get('DB_USER'),
    'password': environ.get('DB_PASSWORD'),  # 永远不要硬编码密码
    'database': environ.get('DB_NAME'),
    'ssl_mode': 'require'  # 为传输中的数据启用SSL
}
```

### 3. 敏感数据加密

#### 静态数据加密

对于需要存储在数据库中的敏感字段：

```python
from cryptography.fernet import Fernet
import base64

class User(ActiveRecord):
    # 定义加密密钥管理（最好使用密钥管理服务）
    encryption_key = environ.get('ENCRYPTION_KEY')
    cipher_suite = Fernet(base64.urlsafe_b64encode(encryption_key.ljust(32)[:32].encode()))
    
    # 保存前加密敏感数据的方法
    def encrypt_sensitive_data(self, data):
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    # 检索时解密数据的方法
    def decrypt_sensitive_data(self, encrypted_data):
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    # 重写save方法以加密敏感字段
    def save(self, *args, **kwargs):
        if self.credit_card_number:  # 只有当字段有值时才加密
            self.credit_card_number = self.encrypt_sensitive_data(self.credit_card_number)
        super().save(*args, **kwargs)
```

#### 传输中的数据

- 网络应用程序始终使用HTTPS/TLS
- 配置数据库连接使用SSL/TLS

### 4. 安全的密码处理

永远不要存储明文密码。使用带盐的强哈希算法：

```python
import hashlib
import os

class User(ActiveRecord):
    # 使用适当哈希设置密码的方法
    def set_password(self, password):
        # 生成随机盐
        salt = os.urandom(32)
        # 使用盐对密码进行哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # 迭代次数
        )
        # 存储盐和哈希
        self.password_salt = salt.hex()
        self.password_hash = password_hash.hex()
    
    # 验证密码的方法
    def verify_password(self, password):
        salt = bytes.fromhex(self.password_salt)
        stored_hash = bytes.fromhex(self.password_hash)
        # 使用存储的盐对提供的密码进行哈希
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # 与set_password中相同的迭代次数
        )
        # 比较计算的哈希与存储的哈希
        return computed_hash == stored_hash
```

### 5. 掩码和编辑

在日志、UI或API响应中显示敏感数据时：

```python
class CreditCard(ActiveRecord):
    # 获取用于显示的掩码信用卡号码的方法
    def get_masked_number(self):
        if not self.card_number:
            return None
        # 只显示最后4位数字
        return f"****-****-****-{self.card_number[-4:]}"
    
    # 重写to_dict方法以掩码敏感数据
    def to_dict(self):
        data = super().to_dict()
        # 用掩码版本替换敏感字段
        if 'card_number' in data:
            data['card_number'] = self.get_masked_number()
        # 从字典表示中完全删除CVV
        if 'cvv' in data:
            del data['cvv']
        return data
```

### 6. 日志记录注意事项

```python
import logging

# 配置日志以避免敏感数据
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_payment(user, credit_card, amount):
    # 不要记录敏感信息
    logger.info(f"为用户 {user.id} 处理金额为 {amount} 的付款")
    # 不要这样做：logger.info(f"信用卡详情：{credit_card.number}，CVV：{credit_card.cvv}")
    
    # 处理付款逻辑
    
    logger.info(f"用户 {user.id} 的付款处理成功")
```

### 7. API响应安全

通过API返回模型数据时：

```python
class UserAPI:
    def get_user_data(self, user_id):
        user = User.objects.get(id=user_id)
        
        # 为API响应创建用户数据的净化版本
        safe_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            # 排除敏感字段，如password_hash、password_salt
            'last_login': user.last_login,
            'account_type': user.account_type
        }
        
        return safe_data
```

## 数据库级别保护

### 列级加密

一些数据库提供列级加密。当可用时，这可以提供额外的安全层：

```sql
-- PostgreSQL使用pgcrypto扩展的示例
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sensitive_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plain_data TEXT,
    encrypted_data BYTEA  -- 将存储加密数据
);
```

在您的ActiveRecord模型中：

```python
class SensitiveData(ActiveRecord):
    # 使用原始SQL进行加密/解密操作
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

## 合规性考虑

根据您的应用程序领域和司法管辖区，您可能需要遵守以下法规：

- GDPR（通用数据保护条例）
- HIPAA（健康保险可携性和责任法案）
- PCI DSS（支付卡行业数据安全标准）
- CCPA（加州消费者隐私法案）

确保您的数据处理实践符合适用法规的要求。

## 结论

保护敏感数据需要多层次的方法。rhosocial ActiveRecord提供了实现这些安全措施的灵活性，但您需要确保它们得到正确实施和维护。

定期审查您的敏感数据处理实践，并了解新出现的安全威胁和最佳实践。