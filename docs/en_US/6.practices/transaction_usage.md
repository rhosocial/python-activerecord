# Transaction Usage Best Practices

This guide covers best practices for using transactions in RhoSocial ActiveRecord applications, with practical examples from both social media and e-commerce domains.

## Basic Transaction Usage

### Simple Transactions

```python
# Basic transaction usage
with User.transaction():
    user.name = "New Name"
    user.save()

# E-commerce example
with Order.transaction():
    order.status = 'completed'
    order.save()
```

### Transaction Scope

```python
class User(ActiveRecord):
    def update_profile(self, profile_data: dict) -> None:
        """Update user profile with transaction."""
        with self.transaction():
            # Update user
            self.name = profile_data['name']
            self.email = profile_data['email']
            self.save()
            
            # Update related profile
            profile = self.profile
            profile.bio = profile_data['bio']
            profile.save()

class Order(ActiveRecord):
    def process(self) -> None:
        """Process order with transaction."""
        with self.transaction():
            # Update order status
            self.status = 'processing'
            self.save()
            
            # Update product inventory
            for item in self.items:
                product = item.product
                product.stock -= item.quantity
                product.save()
```

## Advanced Transaction Usage

### Nested Transactions

```python
def publish_post_with_notifications(post: Post) -> None:
    """Publish post and send notifications with nested transactions."""
    with Post.transaction() as tx1:  # Outer transaction
        # Update post
        post.status = 'published'
        post.published_at = datetime.now()
        post.save()
        
        with Post.transaction() as tx2:  # Nested transaction
            # Create notifications
            followers = post.author.followers
            for follower in followers:
                Notification(
                    user_id=follower.id,
                    type='new_post',
                    post_id=post.id
                ).save()

def process_order_with_payment(order: Order) -> None:
    """Process order with payment in nested transaction."""
    with Order.transaction() as tx1:
        # Process order
        order.status = 'processing'
        order.save()
        
        with Order.transaction() as tx2:
            try:
                # Process payment
                payment = process_payment(order)
                
                # Update order with payment
                order.payment_id = payment.id
                order.status = 'paid'
                order.save()
            except PaymentError:
                # Rollback payment transaction
                tx2.rollback()
                
                # Update order status
                order.status = 'payment_failed'
                order.save()
```

### Savepoints

```python
def process_post_with_media(post: Post, media_files: List[str]) -> None:
    """Process post with media using savepoints."""
    with Post.transaction() as tx:
        # Save post
        post.save()
        
        # Create savepoint after post creation
        tx.create_savepoint('post_created')
        
        try:
            # Process media files
            for file in media_files:
                media = MediaAttachment(
                    post_id=post.id,
                    file_path=file
                )
                media.save()
                
                # Create savepoint after each media
                tx.create_savepoint(f'media_{media.id}')
                
        except MediaProcessingError as e:
            # Rollback to last successful media
            last_media_id = e.last_successful_id
            if last_media_id:
                tx.rollback_to_savepoint(f'media_{last_media_id}')
            else:
                tx.rollback_to_savepoint('post_created')
            
            # Update post status
            post.status = 'media_failed'
            post.save()

def process_order_items(order: Order, items: List[dict]) -> None:
    """Process order items with savepoints."""
    with Order.transaction() as tx:
        # Create order
        order.save()
        tx.create_savepoint('order_created')
        
        try:
            # Process items
            for item in items:
                # Check inventory
                product = Product.find_one(item['product_id'])
                if product.stock < item['quantity']:
                    raise ValueError(f"Insufficient stock for {product.name}")
                
                # Create order item
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item['quantity'],
                    price=product.price
                )
                order_item.save()
                
                # Update inventory
                product.stock -= item['quantity']
                product.save()
                
                # Create savepoint after each item
                tx.create_savepoint(f'item_{order_item.id}')
                
        except ValueError as e:
            # Rollback to order creation
            tx.rollback_to_savepoint('order_created')
            
            # Update order status
            order.status = 'failed'
            order.error_message = str(e)
            order.save()
```

## Transaction Patterns

### Unit of Work

```python
class PostPublisher:
    """Unit of work pattern for publishing posts."""
    
    def __init__(self, post: Post):
        self.post = post
        self.notifications = []
        self.tags = []
    
    def add_notification(self, user_id: int):
        """Add notification to be created."""
        self.notifications.append({
            'user_id': user_id,
            'type': 'new_post'
        })
    
    def add_tag(self, name: str):
        """Add tag to be created."""
        self.tags.append(name)
    
    def commit(self):
        """Commit all changes in single transaction."""
        with Post.transaction():
            # Publish post
            self.post.status = 'published'
            self.post.published_at = datetime.now()
            self.post.save()
            
            # Create notifications
            for notification in self.notifications:
                Notification(
                    user_id=notification['user_id'],
                    type=notification['type'],
                    post_id=self.post.id
                ).save()
            
            # Create tags
            for tag_name in self.tags:
                tag = Tag.find_or_create(name=tag_name)
                PostTag(
                    post_id=self.post.id,
                    tag_id=tag.id
                ).save()

class OrderProcessor:
    """Unit of work pattern for processing orders."""
    
    def __init__(self, order: Order):
        self.order = order
        self.inventory_updates = []
        self.notifications = []
    
    def add_inventory_update(self, product_id: int, quantity: int):
        """Add inventory update to be processed."""
        self.inventory_updates.append({
            'product_id': product_id,
            'quantity': quantity
        })
    
    def add_notification(self, user_id: int, message: str):
        """Add notification to be sent."""
        self.notifications.append({
            'user_id': user_id,
            'message': message
        })
    
    def commit(self):
        """Commit all changes in single transaction."""
        with Order.transaction():
            # Update order
            self.order.status = 'processing'
            self.order.save()
            
            # Update inventory
            for update in self.inventory_updates:
                product = Product.find_one(update['product_id'])
                product.stock -= update['quantity']
                product.save()
            
            # Create notifications
            for notification in self.notifications:
                Notification(
                    user_id=notification['user_id'],
                    type='order_update',
                    message=notification['message'],
                    order_id=self.order.id
                ).save()
```

### Retry Logic

```python
from functools import wraps
from time import sleep

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DeadlockError) as e:
                    last_error = e
                    if attempt + 1 < max_attempts:
                        sleep(delay * (2 ** attempt))
                    continue
            
            raise last_error
        
        return wrapper
    return decorator

@with_retry(max_attempts=3, delay=1.0)
def process_order(order: Order) -> None:
    """Process order with retry logic."""
    with Order.transaction():
        # Update order
        order.status = 'processing'
        order.save()
        
        # Update inventory
        for item in order.items:
            product = item.product
            product.stock -= item.quantity
            product.save()
```

## Best Practices

1. **Transaction Scope**
   - Keep transactions as short as possible
   - Include only necessary operations
   - Use proper isolation levels
   - Handle errors appropriately

2. **Nested Transactions**
   - Use for complex operations
   - Handle rollbacks properly
   - Consider using savepoints
   - Maintain proper nesting levels

3. **Error Handling**
   - Catch specific exceptions
   - Implement retry logic
   - Log transaction errors
   - Clean up resources

4. **Resource Management**
   - Use context managers
   - Release resources properly
   - Handle connection pooling
   - Monitor transaction duration

5. **Design Patterns**
   - Use Unit of Work pattern
   - Implement retry mechanisms
   - Consider bulk operations
   - Maintain atomicity

## Common Pitfalls

1. **Long-Running Transactions**
   - Can cause deadlocks
   - Block other operations
   - Increase resource usage
   - Reduce concurrency

2. **Improper Error Handling**
   - Missing rollbacks
   - Unclear error states
   - Resource leaks
   - Inconsistent data

3. **Transaction Isolation**
   - Incorrect isolation levels
   - Phantom reads
   - Dirty reads
   - Lost updates

4. **Resource Management**
   - Connection leaks
   - Unclosed transactions
   - Memory leaks
   - Pool exhaustion

## Next Steps

1. Study [Error Handling](error_handling.md)
2. Learn about [Performance Optimization](performance_optimization.md)
3. Review [Testing Strategy](testing_strategy.md)