# tests/providers/query_worker_tasks.py
"""
Query Worker task functions for SQLite backend.

Features:
1. Module-level functions (pickle-able)
2. Fully serializable parameters
3. Self-configured model connections inside functions
4. Transaction support
5. Disconnect after use
6. Both sync and async task functions supported
"""
from typing import Dict, Any
import importlib


def _configure_models_from_params(params: dict) -> None:
    """
    Configure all models from connection parameters.

    Since all models share the same database connection,
    only the User model needs to be configured, and other models
    will automatically share the backend.

    Args:
        params: Connection parameters provided by worker_connection_params fixture
    """
    backend_module = importlib.import_module(params['backend_module'])
    backend_class = getattr(backend_module, params['backend_class_name'])

    config_module = importlib.import_module(params['config_module'])
    config_class = getattr(config_module, params['config_class_name'])

    config_keys = {
        'database', 'delete_on_close', 'pragmas', 'uri', 'timeout',
        'isolation_level', 'detect_types', 'check_same_thread',
        'host', 'port', 'username', 'password', 'driver_type', 'options'
    }
    config_dict = {k: v for k, v in params['config_dict'].items() if k in config_keys}

    # Disable delete_on_close in Worker process to avoid deleting database on disconnect
    if 'delete_on_close' in config_dict:
        config_dict['delete_on_close'] = False

    config = config_class(**config_dict)

    # Only need to import and configure User, other models will share the backend
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem
    User.configure(config, backend_class)
    # Ensure Order and OrderItem use the same backend
    Order.__backend__ = User.__backend__
    OrderItem.__backend__ = User.__backend__


async def _async_configure_models_from_params(params: dict) -> None:
    """
    Async configure all models from connection parameters.

    Since all models share the same database connection,
    only the User model needs to be configured, and other models
    will automatically share the backend.

    Args:
        params: Connection parameters provided by worker_connection_params fixture
    """
    backend_module = importlib.import_module(params['backend_module'])
    backend_class = getattr(backend_module, params['backend_class_name'])

    # Convert sync backend to async backend if needed
    # e.g., SQLiteBackend -> AsyncSQLiteBackend, PostgresBackend -> AsyncPostgresBackend
    if not backend_class.__name__.startswith('Async'):
        async_backend_class_name = f'Async{backend_class.__name__}'
        # Try to get from same module
        if hasattr(backend_module, async_backend_class_name):
            backend_class = getattr(backend_module, async_backend_class_name)
        else:
            # Try to get from parent module (e.g., postgres.backend.sync -> postgres.backend)
            parent_module_name = '.'.join(params['backend_module'].split('.')[:-1])
            parent_module = importlib.import_module(parent_module_name)
            if hasattr(parent_module, async_backend_class_name):
                backend_class = getattr(parent_module, async_backend_class_name)

    config_module = importlib.import_module(params['config_module'])
    config_class = getattr(config_module, params['config_class_name'])

    config_keys = {
        'database', 'delete_on_close', 'pragmas', 'uri', 'timeout',
        'isolation_level', 'detect_types', 'check_same_thread',
        'host', 'port', 'username', 'password', 'driver_type', 'options'
    }
    config_dict = {k: v for k, v in params['config_dict'].items() if k in config_keys}

    # Disable delete_on_close in Worker process to avoid deleting database on disconnect
    if 'delete_on_close' in config_dict:
        config_dict['delete_on_close'] = False

    config = config_class(**config_dict)

    # Import async models
    from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrder, AsyncOrderItem
    await AsyncUser.configure(config, backend_class)
    # Ensure Order and OrderItem use the same backend
    AsyncOrder.__backend__ = AsyncUser.__backend__
    AsyncOrderItem.__backend__ = AsyncUser.__backend__


def create_order_with_items_task(params: dict) -> Dict[str, Any]:
    """
    Create order and order items (transaction operation).

    Args:
        params: Dictionary containing connection parameters + business parameters
            - user_id: User ID
            - order_number: Order number
            - items: List of order items

    Returns:
        {'order_id': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    user_id = params.pop('user_id')
    order_number = params.pop('order_number')
    items = params.pop('items', [])

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem

    _configure_models_from_params(params)

    try:
        from decimal import Decimal

        # Begin transaction
        backend = Order.backend()
        backend.begin_transaction()

        try:
            # Create order
            order = Order(user_id=user_id, order_number=order_number, status='pending')
            order.save()

            # Create order items
            total_amount = Decimal('0')
            for item_data in items:
                subtotal = Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
                item = OrderItem(
                    order_id=order.id,
                    product_name=item_data['product_name'],
                    quantity=item_data['quantity'],
                    unit_price=Decimal(str(item_data['unit_price'])),
                    subtotal=subtotal
                )
                item.save()
                total_amount += subtotal

            # Update order total amount
            order.total_amount = total_amount
            order.save()

            # Commit transaction
            backend.commit_transaction()

            return {'order_id': order.id, 'success': True}
        except Exception as e:
            # Rollback transaction
            backend.rollback_transaction()
            raise e
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def transfer_balance_task(params: dict) -> Dict[str, Any]:
    """
    Balance transfer task (transaction operation).

    Args:
        params: Dictionary containing connection parameters + business parameters
            - from_user_id: Source user ID
            - to_user_id: Target user ID
            - amount: Transfer amount

    Returns:
        {'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    from_user_id = params.pop('from_user_id')
    to_user_id = params.pop('to_user_id')
    amount = params.pop('amount')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User

    _configure_models_from_params(params)

    try:
        backend = User.backend()
        backend.begin_transaction()

        try:
            # Query source user
            from_user = User.find_one({'id': from_user_id})
            if not from_user:
                raise ValueError(f"Source user {from_user_id} not found")

            # Check if balance is sufficient
            if from_user.balance < amount:
                raise ValueError(f"Insufficient balance: {from_user.balance} < {amount}")

            # Query target user
            to_user = User.find_one({'id': to_user_id})
            if not to_user:
                raise ValueError(f"Target user {to_user_id} not found")

            # Execute transfer
            from_user.balance -= amount
            from_user.save()

            to_user.balance += amount
            to_user.save()

            # Commit transaction
            backend.commit_transaction()

            return {
                'success': True,
                'from_balance': from_user.balance,
                'to_balance': to_user.balance
            }
        except Exception as e:
            backend.rollback_transaction()
            raise e
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def update_order_status_task(params: dict) -> Dict[str, Any]:
    """
    Update order status task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - order_id: Order ID
            - new_status: New status

    Returns:
        {'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    order_id = params.pop('order_id')
    new_status = params.pop('new_status')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order

    _configure_models_from_params(params)

    try:
        order = Order.find_one({'id': order_id})
        if not order:
            return {'error': 'Order not found', 'success': False}

        order.status = new_status
        order.save()

        return {'success': True, 'order_id': order.id, 'status': new_status}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def count_user_orders_task(params: dict) -> Dict[str, Any]:
    """
    Count user orders task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - user_id: User ID

    Returns:
        {'count': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    user_id = params.pop('user_id')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order

    _configure_models_from_params(params)

    try:
        count = Order.query().where(Order.c.user_id == user_id).count()
        return {'count': count, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def count_order_items_task(params: dict) -> Dict[str, Any]:
    """
    Count order items task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - order_id: Order ID

    Returns:
        {'count': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    order_id = params.pop('order_id')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, OrderItem

    _configure_models_from_params(params)

    try:
        count = OrderItem.query().where(OrderItem.c.order_id == order_id).count()
        return {'count': count, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def calculate_order_total_task(params: dict) -> Dict[str, Any]:
    """
    Calculate order total task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - order_id: Order ID

    Returns:
        {'total': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    order_id = params.pop('order_id')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, OrderItem

    _configure_models_from_params(params)

    try:
        items = OrderItem.query().where(OrderItem.c.order_id == order_id).all()
        total = sum(item.subtotal for item in items)
        return {'total': float(total), 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


# ── Async Query Task Functions ────────────────────────────────────────────────
# These async functions demonstrate AsyncActiveRecord usage in WorkerPool.
# WorkerPool automatically detects async functions and runs them with asyncio.run().


async def async_create_order_with_items_task(params: dict) -> Dict[str, Any]:
    """
    Async create order and order items (transaction operation).

    Args:
        params: Dictionary containing connection parameters + business parameters
            - user_id: User ID
            - order_number: Order number
            - items: List of order items

    Returns:
        {'order_id': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    user_id = params.pop('user_id')
    order_number = params.pop('order_number')
    items = params.pop('items', [])

    from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrder, AsyncOrderItem

    await _async_configure_models_from_params(params)

    try:
        from decimal import Decimal

        # Begin transaction
        backend = AsyncOrder.backend()
        await backend.begin_transaction()

        try:
            # Create order
            order = AsyncOrder(user_id=user_id, order_number=order_number, status='pending')
            await order.save()

            # Create order items
            total_amount = Decimal('0')
            for item_data in items:
                subtotal = Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
                item = AsyncOrderItem(
                    order_id=order.id,
                    product_name=item_data['product_name'],
                    quantity=item_data['quantity'],
                    unit_price=Decimal(str(item_data['unit_price'])),
                    subtotal=subtotal
                )
                await item.save()
                total_amount += subtotal

            # Update order total amount
            order.total_amount = total_amount
            await order.save()

            # Commit transaction
            await backend.commit_transaction()

            return {'order_id': order.id, 'success': True}
        except Exception as e:
            # Rollback transaction
            await backend.rollback_transaction()
            raise e
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        await AsyncUser.backend().disconnect()


async def async_transfer_balance_task(params: dict) -> Dict[str, Any]:
    """
    Async balance transfer task (transaction operation).

    Args:
        params: Dictionary containing connection parameters + business parameters
            - from_user_id: Source user ID
            - to_user_id: Target user ID
            - amount: Transfer amount

    Returns:
        {'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    from_user_id = params.pop('from_user_id')
    to_user_id = params.pop('to_user_id')
    amount = params.pop('amount')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser

    await _async_configure_models_from_params(params)

    try:
        backend = AsyncUser.backend()
        await backend.begin_transaction()

        try:
            # Query source user
            from_user = await AsyncUser.find_one({'id': from_user_id})
            if not from_user:
                raise ValueError(f"Source user {from_user_id} not found")

            # Check if balance is sufficient
            if from_user.balance < amount:
                raise ValueError(f"Insufficient balance: {from_user.balance} < {amount}")

            # Query target user
            to_user = await AsyncUser.find_one({'id': to_user_id})
            if not to_user:
                raise ValueError(f"Target user {to_user_id} not found")

            # Execute transfer
            from_user.balance -= amount
            await from_user.save()

            to_user.balance += amount
            await to_user.save()

            # Commit transaction
            await backend.commit_transaction()

            return {
                'success': True,
                'from_balance': from_user.balance,
                'to_balance': to_user.balance
            }
        except Exception as e:
            await backend.rollback_transaction()
            raise e
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        await AsyncUser.backend().disconnect()


async def async_count_user_orders_task(params: dict) -> Dict[str, Any]:
    """
    Async count user orders task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - user_id: User ID

    Returns:
        {'count': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    user_id = params.pop('user_id')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrder

    await _async_configure_models_from_params(params)

    try:
        count = await AsyncOrder.query().where(AsyncOrder.c.user_id == user_id).count()
        return {'count': count, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        await AsyncUser.backend().disconnect()


async def async_calculate_order_total_task(params: dict) -> Dict[str, Any]:
    """
    Async calculate order total task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - order_id: Order ID

    Returns:
        {'total': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()
    order_id = params.pop('order_id')

    from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrderItem

    await _async_configure_models_from_params(params)

    try:
        items = await AsyncOrderItem.query().where(AsyncOrderItem.c.order_id == order_id).all()
        total = sum(item.subtotal for item in items)
        return {'total': float(total), 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        await AsyncUser.backend().disconnect()
