# Error Handling Best Practices

This guide covers comprehensive error handling strategies for RhoSocial ActiveRecord applications, with examples from social media and e-commerce domains.

## Error Types

### Core Exceptions

```python
from rhosocial.activerecord.backend import (
    DatabaseError,          # Base database error
    ConnectionError,        # Connection issues
    TransactionError,       # Transaction failures
    QueryError,            # Invalid queries
    ValidationError,       # Data validation failures
    LockError,             # Lock acquisition failures
    DeadlockError,         # Deadlock detection
    IntegrityError,        # Constraint violations
    TypeConversionError,   # Type conversion issues
    OperationalError,      # Operational problems
    RecordNotFound         # Record lookup failures
)
```

### Custom Exceptions

```python
class OrderError(DatabaseError):
    """Base class for order-related errors."""
    pass

class PaymentError(OrderError):
    """Payment processing errors."""
    pass

class InventoryError(OrderError):
    """Inventory-related errors."""
    pass

class PostError(DatabaseError):
    """Base class for post-related errors."""
    pass

class MediaProcessingError(PostError):
    """Media processing errors."""
    def __init__(self, message: str, last_successful_id: Optional[int] = None):
        super().__init__(message)
        self.last_successful_id = last_successful_id
```

## Basic Error Handling

### Simple Try-Except

```python
# Social Media Example
def create_post(user_id: int, content: str) -> Post:
    """Create new post with error handling."""
    try:
        post = Post(
            user_id=user_id,
            content=content,
            created_at=datetime.now()
        )
        post.save()
        return post
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

# E-commerce Example
def process_order(order_id: int) -> None:
    """Process order with error handling."""
    try:
        order = Order.find_one_or_fail(order_id)
        order.process()
    except RecordNotFound:
        logger.error(f"Order {order_id} not found")
        raise
    except PaymentError as e:
        logger.error(f"Payment failed for order {order_id}: {e}")
        raise
    except DatabaseError as e:
        logger.error(f"Database error processing order {order_id}: {e}")
        raise
```

### Context Managers

```python
class DatabaseOperation:
    """Context manager for database operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        duration = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"Completed {self.operation_name} in {duration:.2f}s")
        else:
            logger.error(
                f"Error in {self.operation_name}: {exc_value}",
                exc_info=(exc_type, exc_value, traceback)
            )
        return False  # Re-raise exceptions

# Usage
def update_user_profile(user_id: int, data: dict):
    with DatabaseOperation("update_user_profile"):
        user = User.find_one_or_fail(user_id)
        user.update(data)
        user.save()
```

## Advanced Error Handling

### Retry Mechanism

```python
from functools import wraps
from time import sleep

def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (OperationalError, DeadlockError)
):
    """Decorator for retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt + 1 < max_attempts:
                        sleep_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed, "
                            f"retrying in {sleep_time:.2f}s: {e}"
                        )
                        sleep(sleep_time)
                    continue
            
            logger.error(f"All {max_attempts} attempts failed")
            raise last_error
        
        return wrapper
    return decorator

# Usage
@with_retry()
def process_payment(order: Order) -> None:
    """Process payment with retry logic."""
    with order.transaction():
        payment = create_payment(order)
        order.payment_id = payment.id
        order.status = 'paid'
        order.save()
```

### Error Recovery

```python
class ErrorRecovery:
    """Base class for error recovery strategies."""
    
    def __init__(self):
        self.errors = []
    
    def handle_error(self, error: Exception) -> bool:
        """Handle error and return whether to continue."""
        self.errors.append(error)
        return True
    
    def should_abort(self) -> bool:
        """Check if operation should be aborted."""
        return False
    
    def cleanup(self) -> None:
        """Perform cleanup after errors."""
        pass

class OrderProcessingRecovery(ErrorRecovery):
    """Recovery strategy for order processing."""
    
    def __init__(self, max_payment_attempts: int = 3):
        super().__init__()
        self.max_payment_attempts = max_payment_attempts
        self.payment_attempts = 0
    
    def handle_error(self, error: Exception) -> bool:
        super().handle_error(error)
        
        if isinstance(error, PaymentError):
            self.payment_attempts += 1
            return self.payment_attempts < self.max_payment_attempts
        
        if isinstance(error, InventoryError):
            # Don't retry inventory errors
            return False
        
        return True
    
    def should_abort(self) -> bool:
        return self.payment_attempts >= self.max_payment_attempts
    
    def cleanup(self) -> None:
        if self.errors:
            logger.error(f"Order processing failed after {len(self.errors)} errors")
            for error in self.errors:
                logger.error(f"Error: {error}")

# Usage
def process_order(order: Order) -> None:
    """Process order with error recovery."""
    recovery = OrderProcessingRecovery()
    
    while not recovery.should_abort():
        try:
            with order.transaction():
                # Process payment
                payment = process_payment(order)
                order.payment_id = payment.id
                
                # Update inventory
                for item in order.items:
                    update_inventory(item)
                
                # Complete order
                order.status = 'completed'
                order.save()
                
                break
                
        except Exception as e:
            if not recovery.handle_error(e):
                break
    
    recovery.cleanup()
```

### Logging and Monitoring

```python
class ErrorMonitor:
    """Monitor and track errors."""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_errors = deque(maxlen=100)
    
    def record_error(self, error: Exception) -> None:
        """Record error occurrence."""
        error_type = type(error).__name__
        self.error_counts[error_type] += 1
        self.last_errors.append((
            datetime.now(),
            error_type,
            str(error)
        ))
        
        # Alert on high error rates
        if self.error_counts[error_type] > 100:
            self.alert_high_error_rate(error_type)
    
    def alert_high_error_rate(self, error_type: str) -> None:
        """Send alert for high error rate."""
        logger.critical(
            f"High error rate detected for {error_type}: "
            f"{self.error_counts[error_type]} occurrences"
        )

# Global error monitor
error_monitor = ErrorMonitor()

def log_error(error: Exception, context: dict = None) -> None:
    """Log error with context."""
    error_monitor.record_error(error)
    
    logger.error(
        f"Error: {error}",
        extra={
            'error_type': type(error).__name__,
            'context': context or {}
        },
        exc_info=True
    )
```

## Error Handling Patterns

### Circuit Breaker

```python
class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'open':
                if self._should_reset():
                    self._reset()
                else:
                    raise CircuitBreakerError("Circuit is open")
            
            try:
                result = func(*args, **kwargs)
                self._success()
                return result
            except Exception as e:
                self._failure()
                raise
        
        return wrapper
    
    def _failure(self):
        """Handle failure."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = 'open'
    
    def _success(self):
        """Handle success."""
        self.failures = 0
        self.state = 'closed'
    
    def _should_reset(self) -> bool:
        """Check if circuit should reset."""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.reset_timeout
    
    def _reset(self):
        """Reset circuit breaker."""
        self.failures = 0
        self.state = 'closed'
        self.last_failure_time = None

# Usage
payment_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)

@payment_breaker
def process_payment(order: Order) -> None:
    """Process payment with circuit breaker."""
    # Payment processing logic here
    pass
```

### Fallback Strategy

```python
class Fallback:
    """Fallback strategy implementation."""
    
    def __init__(self, fallback_func):
        self.fallback_func = fallback_func
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function failed, using fallback: {e}")
                return self.fallback_func(*args, **kwargs)
        
        return wrapper

# Usage
def offline_payment(order: Order) -> None:
    """Offline payment processing."""
    order.status = 'pending_manual_payment'
    order.save()

@Fallback(offline_payment)
def process_payment(order: Order) -> None:
    """Process payment with fallback."""
    # Online payment processing logic here
    pass
```

## Best Practices

1. **Error Hierarchy**
   - Use appropriate error types
   - Create custom exceptions when needed
   - Maintain clear error hierarchy
   - Document error conditions

2. **Error Handling**
   - Catch specific exceptions
   - Implement retry logic
   - Use circuit breakers
   - Provide fallback strategies

3. **Logging and Monitoring**
   - Log errors with context
   - Monitor error rates
   - Set up alerts
   - Track error patterns

4. **Recovery**
   - Implement recovery strategies
   - Clean up resources
   - Maintain data consistency
   - Handle partial failures

5. **Documentation**
   - Document error conditions
   - Provide error handling examples
   - Explain recovery procedures
   - Maintain error codes

## Next Steps

1. Study [Performance Optimization](performance_optimization.md)
2. Learn about [Testing Strategy](testing_strategy.md)
3. Review [Transaction Usage](transaction_usage.md)