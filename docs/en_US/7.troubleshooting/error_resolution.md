# Error Resolution Guide

This guide covers strategies for resolving errors and implementing recovery procedures in RhoSocial ActiveRecord applications, with examples from both social media and e-commerce domains.

## Common Errors

### Database Errors

```python
from rhosocial.activerecord.backend import (
    DatabaseError,
    ConnectionError,
    TransactionError,
    IntegrityError
)

class ErrorHandler:
    """Handle common database errors."""
    
    @staticmethod
    def handle_database_error(e: Exception) -> None:
        """Handle specific database errors."""
        if isinstance(e, ConnectionError):
            # Handle connection issues
            logger.error(f"Connection error: {e}")
            notify_admin("Database connection error")
            raise
        
        elif isinstance(e, TransactionError):
            # Handle transaction failures
            logger.error(f"Transaction error: {e}")
            notify_admin("Transaction failure")
            raise
        
        elif isinstance(e, IntegrityError):
            # Handle constraint violations
            logger.error(f"Integrity error: {e}")
            raise ValidationError("Data integrity violation")
        
        elif isinstance(e, DatabaseError):
            # Handle other database errors
            logger.error(f"Database error: {e}")
            raise
        
        else:
            # Handle unexpected errors
            logger.error(f"Unexpected error: {e}")
            raise

# Usage
try:
    with Order.transaction():
        order.process()
except Exception as e:
    ErrorHandler.handle_database_error(e)
```

### Data Validation Errors

```python
class ValidationErrorHandler:
    """Handle validation errors."""
    
    def __init__(self):
        self.errors = []
    
    def add_error(self, field: str, message: str):
        """Add validation error."""
        self.errors.append({
            'field': field,
            'message': message
        })
    
    def has_errors(self) -> bool:
        """Check if there are errors."""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[Dict[str, str]]:
        """Get all errors."""
        return self.errors
    
    def clear(self):
        """Clear all errors."""
        self.errors = []

# Usage with model validation
class User(ActiveRecord):
    username: str
    email: str
    
    def validate(self) -> None:
        """Validate user data."""
        handler = ValidationErrorHandler()
        
        if len(self.username) < 3:
            handler.add_error('username', 'Username too short')
        
        if '@' not in self.email:
            handler.add_error('email', 'Invalid email format')
        
        if handler.has_errors():
            raise ValidationError(handler.get_errors())
```

## Recovery Strategies

### Transaction Recovery

```python
class TransactionRecovery:
    """Implement transaction recovery strategies."""
    
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.current_attempt = 0
    
    def execute_with_recovery(self, func: callable) -> Any:
        """Execute function with recovery."""
        while self.current_attempt < self.max_attempts:
            try:
                return func()
            except TransactionError as e:
                self.current_attempt += 1
                if self.current_attempt >= self.max_attempts:
                    raise
                logger.warning(
                    f"Transaction attempt {self.current_attempt} failed: {e}"
                )
                time.sleep(1 * self.current_attempt)
                continue
            except Exception as e:
                logger.error(f"Unrecoverable error: {e}")
                raise

# Usage
def process_order(order_id: int) -> None:
    recovery = TransactionRecovery()
    
    def process():
        with Order.transaction():
            order = Order.find_one_or_fail(order_id)
            order.process()
    
    recovery.execute_with_recovery(process)
```

### Data Recovery

```python
class DataRecovery:
    """Implement data recovery strategies."""
    
    def __init__(self):
        self.backup_data = {}
    
    def backup_record(self, record: ActiveRecord):
        """Create backup of record."""
        self.backup_data[record.id] = record.model_dump()
    
    def restore_record(self, record: ActiveRecord):
        """Restore record from backup."""
        if record.id in self.backup_data:
            backup = self.backup_data[record.id]
            for key, value in backup.items():
                setattr(record, key, value)
            record.save()
    
    def cleanup_backup(self, record: ActiveRecord):
        """Remove backup data."""
        self.backup_data.pop(record.id, None)

# Usage
def update_user_profile(user_id: int, data: dict):
    recovery = DataRecovery()
    user = User.find_one_or_fail(user_id)
    
    try:
        # Backup current state
        recovery.backup_record(user)
        
        # Update profile
        user.update(data)
        user.save()
        
        # Clean up backup
        recovery.cleanup_backup(user)
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        # Restore previous state
        recovery.restore_record(user)
        raise
```

### System Recovery

```python
class SystemRecovery:
    """Implement system-wide recovery strategies."""
    
    def __init__(self):
        self.status = 'normal'
        self.error_count = 0
        self.last_error = None
    
    def record_error(self, error: Exception):
        """Record system error."""
        self.error_count += 1
        self.last_error = error
        
        # Update system status
        if self.error_count > 10:
            self.status = 'degraded'
        if self.error_count > 50:
            self.status = 'critical'
    
    def check_health(self) -> bool:
        """Check system health."""
        try:
            # Test database connection
            User.query().limit(1).one()
            
            # Reset error count on success
            self.error_count = 0
            self.status = 'normal'
            return True
            
        except Exception as e:
            self.record_error(e)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            'status': self.status,
            'error_count': self.error_count,
            'last_error': str(self.last_error) if self.last_error else None
        }

# Usage
recovery = SystemRecovery()

# Monitor system health
def health_check():
    if not recovery.check_health():
        status = recovery.get_status()
        notify_admin(f"System health check failed: {status}")
```

## Error Prevention

### Validation Strategies

```python
class ValidationStrategy:
    """Implement validation strategies."""
    
    @staticmethod
    def validate_user(user: User) -> List[str]:
        """Validate user data."""
        errors = []
        
        # Username validation
        if not user.username:
            errors.append("Username is required")
        elif len(user.username) < 3:
            errors.append("Username must be at least 3 characters")
        
        # Email validation
        if not user.email:
            errors.append("Email is required")
        elif '@' not in user.email:
            errors.append("Invalid email format")
        
        return errors
    
    @staticmethod
    def validate_order(order: Order) -> List[str]:
        """Validate order data."""
        errors = []
        
        # Check items
        if not order.items:
            errors.append("Order must have items")
        
        # Check total
        if order.total <= 0:
            errors.append("Order total must be positive")
        
        # Check inventory
        for item in order.items:
            if item.quantity > item.product.stock:
                errors.append(f"Insufficient stock for {item.product.name}")
        
        return errors

# Usage
def save_with_validation(record: ActiveRecord) -> None:
    """Save record with validation."""
    if isinstance(record, User):
        errors = ValidationStrategy.validate_user(record)
    elif isinstance(record, Order):
        errors = ValidationStrategy.validate_order(record)
    else:
        errors = []
    
    if errors:
        raise ValidationError(errors)
    
    record.save()
```

### Data Consistency

```python
class ConsistencyChecker:
    """Check data consistency."""
    
    @staticmethod
    def check_order_consistency(order: Order) -> List[str]:
        """Check order data consistency."""
        issues = []
        
        # Check order total
        calculated_total = sum(
            item.quantity * item.price 
            for item in order.items
        )
        if abs(calculated_total - order.total) > Decimal('0.01'):
            issues.append("Order total mismatch")
        
        # Check inventory levels
        for item in order.items:
            if item.quantity > item.product.stock:
                issues.append(f"Invalid stock level for {item.product.name}")
        
        return issues
    
    @staticmethod
    def fix_order_consistency(order: Order) -> None:
        """Fix order consistency issues."""
        # Recalculate total
        order.total = sum(
            item.quantity * item.price 
            for item in order.items
        )
        
        # Update stock levels if needed
        for item in order.items:
            if item.quantity > item.product.stock:
                item.quantity = item.product.stock
        
        order.save()

# Usage
def process_order_safely(order: Order) -> None:
    """Process order with consistency checks."""
    issues = ConsistencyChecker.check_order_consistency(order)
    
    if issues:
        logger.warning(f"Order consistency issues: {issues}")
        ConsistencyChecker.fix_order_consistency(order)
    
    with Order.transaction():
        order.process()
```

## Best Practices

1. **Error Handling**
   - Handle specific errors
   - Implement recovery strategies
   - Log error details
   - Notify administrators

2. **Data Validation**
   - Validate input data
   - Check consistency
   - Implement fixes
   - Monitor validation failures

3. **Recovery Procedures**
   - Implement retries
   - Backup data
   - Restore functionality
   - Document procedures

4. **System Health**
   - Monitor status
   - Track error rates
   - Implement checks
   - Maintain documentation

## Next Steps

1. Review [Common Issues](common_issues.md)
2. Study [Debugging Guide](debugging_guide.md)
3. Learn about [Performance Problems](performance_problems.md)