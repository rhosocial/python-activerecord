# Error Handling

This guide covers error handling in RhoSocial ActiveRecord, including error types, handling strategies, and best practices.

## Error Hierarchy

RhoSocial ActiveRecord provides a comprehensive error hierarchy:

```python
from rhosocial.activerecord.backend import (
    DatabaseError,          # Base class for all database errors
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

## Basic Error Handling

### Simple Error Handling

```python
# Social Media Example
try:
    post = Post.find_one_or_fail(1)
    post.content = "Updated content"
    post.save()
except RecordNotFound:
    print("Post not found")
except ValidationError as e:
    print(f"Validation failed: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")

# E-commerce Example
try:
    order = Order.find_one_or_fail(1)
    order.status = 'processing'
    order.save()
except RecordNotFound:
    print("Order not found")
except DatabaseError as e:
    print(f"Database error: {e}")
```

### Transaction Error Handling

```python
def process_order(order_id: int) -> bool:
    try:
        with Order.transaction():
            order = Order.find_one_or_fail(order_id)
            
            # Process payment
            process_payment(order)
            
            # Update inventory
            update_inventory(order)
            
            # Mark as completed
            order.status = 'completed'
            order.save()
            
            return True
            
    except RecordNotFound:
        log_error("Order not found", order_id)
        return False
    except TransactionError as e:
        log_error("Transaction failed", e)
        return False
    except ValidationError as e:
        log_error("Validation failed", e)
        return False
    except DatabaseError as e:
        log_error("Database error", e)
        return False
```

## Advanced Error Handling

### Retry Mechanism

```python
from time import sleep
from typing import TypeVar, Callable, Any

T = TypeVar('T')

def with_retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (OperationalError, ConnectionError)
) -> T:
    """Execute function with retry logic."""
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_error = e
            if attempt + 1 == max_attempts:
                raise
            
            sleep(delay * (backoff ** attempt))
    
    raise last_error

# Usage
def update_user_status(user_id: int, status: str):
    def _update():
        user = User.find_one_or_fail(user_id)
        user.status = status
        user.save()
    
    with_retry(_update)
```

### Custom Error Classes

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

def process_order(order: Order):
    try:
        with Order.transaction():
            # Process payment
            if not process_payment(order):
                raise PaymentError("Payment failed")
            
            # Check inventory
            for item in order.items:
                product = Product.find_one_or_fail(item.product_id)
                if product.stock < item.quantity:
                    raise InventoryError(
                        f"Insufficient stock for {product.name}"
                    )
            
            # Update order
            order.status = 'processing'
            order.save()
            
    except PaymentError as e:
        handle_payment_error(order, e)
    except InventoryError as e:
        handle_inventory_error(order, e)
    except OrderError as e:
        handle_general_order_error(order, e)
```

## Complex Error Handling Examples

### Social Media Post Creation

```python
def create_post_with_media(user_id: int, content: str, media_files: List[str]):
    """Create post with media attachments."""
    try:
        with Post.transaction() as tx:
            # Create post
            post = Post(
                user_id=user_id,
                content=content,
                created_at=datetime.now()
            )
            post.save()
            
            # Savepoint after post creation
            tx.create_savepoint('post_created')
            
            try:
                # Process media files
                for file_path in media_files:
                    try:
                        # Upload media
                        media_url = upload_media(file_path)
                        
                        # Create media attachment
                        MediaAttachment(
                            post_id=post.id,
                            url=media_url,
                            type=get_media_type(file_path)
                        ).save()
                        
                    except UploadError as e:
                        # Log error but continue with other files
                        log_error(f"Failed to upload {file_path}: {e}")
                        continue
                
                return post
                
            except Exception as e:
                # Rollback to post creation
                tx.rollback_to_savepoint('post_created')
                
                # Update post status
                post.status = 'media_failed'
                post.error_message = str(e)
                post.save()
                
                raise
                
    except ValidationError as e:
        log_validation_error(e)
        raise
    except TransactionError as e:
        log_transaction_error(e)
        raise
    except DatabaseError as e:
        log_database_error(e)
        raise
```

### E-commerce Order Processing

```python
class OrderProcessor:
    def __init__(self, order_id: int):
        self.order_id = order_id
        self.logger = logging.getLogger('order_processor')
    
    def process(self) -> bool:
        """Process order with comprehensive error handling."""
        try:
            with Order.transaction() as tx:
                # Load order
                order = self._load_order()
                
                # Validate order
                self._validate_order(order)
                
                # Create savepoint
                tx.create_savepoint('validated')
                
                try:
                    # Process payment
                    self._process_payment(order)
                    
                    # Create savepoint
                    tx.create_savepoint('paid')
                    
                    try:
                        # Update inventory
                        self._update_inventory(order)
                        
                        # Mark as completed
                        order.status = 'completed'
                        order.save()
                        
                        return True
                        
                    except InventoryError as e:
                        # Rollback to payment
                        tx.rollback_to_savepoint('paid')
                        
                        # Refund payment
                        self._refund_payment(order)
                        
                        # Update order status
                        order.status = 'inventory_failed'
                        order.error_message = str(e)
                        order.save()
                        
                        raise
                        
                except PaymentError as e:
                    # Rollback to validation
                    tx.rollback_to_savepoint('validated')
                    
                    # Update order status
                    order.status = 'payment_failed'
                    order.error_message = str(e)
                    order.save()
                    
                    raise
                    
        except RecordNotFound:
            self.logger.error(f"Order {self.order_id} not found")
            return False
        except ValidationError as e:
            self.logger.error(f"Validation failed: {e}")
            return False
        except PaymentError as e:
            self.logger.error(f"Payment failed: {e}")
            return False
        except InventoryError as e:
            self.logger.error(f"Inventory update failed: {e}")
            return False
        except TransactionError as e:
            self.logger.error(f"Transaction failed: {e}")
            return False
        except DatabaseError as e:
            self.logger.error(f"Database error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
    
    def _load_order(self) -> Order:
        """Load order with retry."""
        return with_retry(
            lambda: Order.find_one_or_fail(self.order_id)
        )
    
    def _validate_order(self, order: Order):
        """Validate order status and items."""
        if order.status != 'pending':
            raise ValidationError("Invalid order status")
        
        if not order.items:
            raise ValidationError("Order has no items")
    
    def _process_payment(self, order: Order):
        """Process payment with retry."""
        def _process():
            payment = process_payment(order)
            order.payment_id = payment.id
            order.save()
        
        with_retry(_process, exceptions=(PaymentError,))
    
    def _update_inventory(self, order: Order):
        """Update inventory for order items."""
        for item in order.items:
            product = Product.find_one_or_fail(item.product_id)
            if product.stock < item.quantity:
                raise InventoryError(
                    f"Insufficient stock for {product.name}"
                )
            
            product.stock -= item.quantity
            product.save()
    
    def _refund_payment(self, order: Order):
        """Refund payment if needed."""
        if order.payment_id:
            with_retry(
                lambda: process_refund(order.payment_id)
            )

# Usage
processor = OrderProcessor(order_id=123)
success = processor.process()
```

## Error Handling Best Practices

1. **Use Specific Exceptions**: Catch specific exceptions rather than generic ones
2. **Implement Retry Logic**: For transient failures
3. **Log Errors**: Maintain comprehensive error logs
4. **Transaction Management**: Use transactions and savepoints
5. **Graceful Degradation**: Handle partial failures appropriately
6. **Clean Up**: Properly clean up resources in error cases

## Next Steps

1. Study [Transactions](transactions.md) for transaction-related error handling
2. Learn about logging in [Practices](../6.practices/error_handling.md)
3. Explore backend-specific errors in [Backends](../3.backends/index.md)