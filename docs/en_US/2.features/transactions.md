# Transaction Management

This guide covers transaction management in RhoSocial ActiveRecord. Transactions ensure data consistency by grouping multiple database operations into atomic units.

## Basic Transactions

### Simple Transaction

```python
# Basic transaction usage
with Order.transaction():
    order.status = 'completed'
    order.save()
    
    product.stock -= 1
    product.save()
```

### Transaction Properties

Transactions in RhoSocial ActiveRecord ensure ACID properties:

- **Atomicity**: All operations succeed or all fail
- **Consistency**: Database remains in valid state
- **Isolation**: Transactions don't interfere
- **Durability**: Committed changes persist

## Transaction Scopes

### Nested Transactions

```python
# Social Media Example
with User.transaction():  # Outer transaction
    user.status = 'active'
    user.save()
    
    with Post.transaction():  # Nested transaction
        post = Post(user_id=user.id, content="Hello")
        post.save()
        
        with Comment.transaction():  # Further nesting
            comment = Comment(post_id=post.id, content="First!")
            comment.save()

# E-commerce Example
with Order.transaction():  # Main order transaction
    order = Order(user_id=1, status='pending')
    order.save()
    
    with Product.transaction():  # Stock management
        for item in cart_items:
            product = Product.find_one_or_fail(item.product_id)
            product.stock -= item.quantity
            product.save()
            
            with OrderItem.transaction():  # Order items
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity
                ).save()
```

### Savepoints

```python
# Transaction with savepoints
with Order.transaction() as tx:
    order.status = 'processing'
    order.save()
    
    # Create savepoint
    tx.create_savepoint('after_status')
    
    try:
        # Risky operations
        process_payment(order)
        ship_order(order)
    except PaymentError:
        # Rollback to savepoint
        tx.rollback_to_savepoint('after_status')
        order.status = 'payment_failed'
        order.save()
    except ShippingError:
        tx.rollback_to_savepoint('after_status')
        order.status = 'shipping_failed'
        order.save()
```

## Isolation Levels

RhoSocial ActiveRecord supports different isolation levels:

```python
from rhosocial.activerecord.transaction import IsolationLevel

# Set isolation level
with Order.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
    order.process()

# Different isolation levels
with Order.transaction(isolation_level=IsolationLevel.READ_COMMITTED):
    # Read committed transaction
    pass

with Order.transaction(isolation_level=IsolationLevel.REPEATABLE_READ):
    # Repeatable read transaction
    pass
```

## Complex Examples

### Social Media Post Creation

```python
def create_post_with_mentions(user_id: int, content: str, mentioned_users: List[str]):
    """Create post and handle user mentions."""
    with Post.transaction():
        # Create post
        post = Post(
            user_id=user_id,
            content=content,
            created_at=datetime.now()
        )
        post.save()
        
        # Process mentions
        for username in mentioned_users:
            try:
                mentioned_user = User.find_one({'username': username})
                if mentioned_user:
                    # Create mention
                    Mention(
                        post_id=post.id,
                        user_id=mentioned_user.id
                    ).save()
                    
                    # Create notification
                    Notification(
                        user_id=mentioned_user.id,
                        type='mention',
                        reference_id=post.id
                    ).save()
            except DatabaseError:
                # Log error but continue
                continue
        
        return post

# Usage
post = create_post_with_mentions(
    user_id=1,
    content="Hello @jane and @john!",
    mentioned_users=['jane', 'john']
)
```

### E-commerce Order Processing

```python
def process_order(cart_id: int) -> Order:
    """Process order with inventory check and payment."""
    with Order.transaction() as tx:
        # Load cart
        cart = Cart.find_one_or_fail(cart_id)
        user = User.find_one_or_fail(cart.user_id)
        
        # Create order
        order = Order(
            user_id=user.id,
            status='pending',
            created_at=datetime.now()
        )
        order.save()
        
        # Savepoint after order creation
        tx.create_savepoint('order_created')
        
        try:
            total = Decimal('0')
            
            # Process items
            for cart_item in cart.items:
                product = Product.find_one_or_fail(cart_item.product_id)
                
                # Check stock
                if product.stock < cart_item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")
                
                # Create order item
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=cart_item.quantity,
                    price=product.price
                )
                order_item.save()
                
                # Update stock
                product.stock -= cart_item.quantity
                product.save()
                
                # Update total
                total += product.price * cart_item.quantity
            
            # Savepoint before payment
            tx.create_savepoint('before_payment')
            
            # Process payment
            try:
                payment = process_payment(user, total)
                
                # Update order
                order.total = total
                order.payment_id = payment.id
                order.status = 'paid'
                order.save()
                
                # Clear cart
                cart.delete()
                
            except PaymentError:
                # Rollback to before payment
                tx.rollback_to_savepoint('before_payment')
                order.status = 'payment_failed'
                order.save()
                raise
                
        except ValueError as e:
            # Rollback to order creation
            tx.rollback_to_savepoint('order_created')
            order.status = 'failed'
            order.error_message = str(e)
            order.save()
            raise
            
        return order

# Usage
try:
    order = process_order(cart_id=123)
    print(f"Order {order.id} processed successfully")
except ValueError as e:
    print(f"Order failed: {e}")
except PaymentError as e:
    print(f"Payment failed: {e}")
```

## Best Practices

1. **Use Context Managers**: Always use `with` statement for transactions
2. **Keep Transactions Short**: Minimize transaction duration
3. **Handle Errors**: Implement proper error handling in transactions
4. **Use Savepoints**: For complex transactions with potential partial failures
5. **Choose Isolation Levels**: Select appropriate isolation level for requirements

## Next Steps

1. Learn about [Error Handling](error_handling.md)
2. Study backend-specific transaction details in [Backends](../3.backends/index.md)
3. Understand performance implications in [Performance](../5.performance/index.md)