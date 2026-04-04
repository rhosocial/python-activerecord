# tests/providers/worker_tasks.py
"""
Worker task functions for SQLite backend.

Features:
1. Module-level functions (pickle-able)
2. Fully serializable parameters
3. Self-configured model connections inside functions
4. Disconnect after use
"""
from typing import Dict, Any, Optional
import importlib


def _configure_model_from_params(params: dict, model_class) -> None:
    """
    Configure model from connection parameters.

    Args:
        params: Connection parameters provided by worker_connection_params fixture
        model_class: Model class to configure
    """
    # Dynamically import backend class
    backend_module = importlib.import_module(params['backend_module'])
    backend_class = getattr(backend_module, params['backend_class_name'])

    # Dynamically import config class
    config_module = importlib.import_module(params['config_module'])
    config_class = getattr(config_module, params['config_class_name'])

    # Extract config parameters (exclude business parameters)
    config_keys = {
        'database', 'delete_on_close', 'pragmas', 'uri', 'timeout',
        'isolation_level', 'detect_types', 'check_same_thread',
        'host', 'port', 'username', 'password', 'driver_type', 'options'
    }
    config_dict = {k: v for k, v in params['config_dict'].items() if k in config_keys}

    # Disable delete_on_close in Worker process to avoid deleting database on disconnect
    # Database cleanup is handled by the main process Provider
    if 'delete_on_close' in config_dict:
        config_dict['delete_on_close'] = False

    config = config_class(**config_dict)

    # Configure model
    model_class.configure(config, backend_class)


def create_user_task(params: dict) -> Dict[str, Any]:
    """
    Create user task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - backend_module, backend_class_name, config_module, config_class_name, config_dict
            - username, email, age (optional)

    Returns:
        {'id': user_id, 'success': True} or {'error': str, 'success': False}
    """
    # Copy params to avoid modifying original dict
    params = params.copy()

    # Extract business parameters
    username = params.pop('username')
    email = params.pop('email')
    age = params.pop('age', None)

    # Import model class
    from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import User

    # Configure model (connect to prepared database)
    _configure_model_from_params(params, User)

    try:
        user = User(username=username, email=email, age=age)
        user.save()
        return {'id': user.id, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def read_user_task(params: dict) -> Dict[str, Any]:
    """
    Read user task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - backend_module, backend_class_name, config_module, config_class_name, config_dict
            - user_id

    Returns:
        {'id': ..., 'username': ..., 'email': ..., 'success': True}
        or {'error': str, 'success': False}
    """
    params = params.copy()

    # Extract business parameters
    user_id = params.pop('user_id')

    from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import User

    _configure_model_from_params(params, User)

    try:
        user = User.find_one({'id': user_id})
        if user:
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'age': user.age,
                'success': True
            }
        else:
            return {'error': 'User not found', 'success': False}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def update_user_task(params: dict) -> Dict[str, Any]:
    """
    Update user task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - backend_module, backend_class_name, config_module, config_class_name, config_dict
            - user_id
            - age, username, email etc. (optional update fields)

    Returns:
        {'id': ..., 'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()

    # Extract business parameters
    user_id = params.pop('user_id')

    from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import User

    _configure_model_from_params(params, User)

    try:
        user = User.find_one({'id': user_id})
        if not user:
            return {'error': 'User not found', 'success': False}

        # Update provided fields
        if 'age' in params:
            user.age = params['age']
        if 'username' in params:
            user.username = params['username']
        if 'email' in params:
            user.email = params['email']

        user.save()
        return {'id': user.id, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()


def delete_user_task(params: dict) -> Dict[str, Any]:
    """
    Delete user task.

    Args:
        params: Dictionary containing connection parameters + business parameters
            - backend_module, backend_class_name, config_module, config_class_name, config_dict
            - user_id

    Returns:
        {'success': True} or {'error': str, 'success': False}
    """
    params = params.copy()

    # Extract business parameters
    user_id = params.pop('user_id')

    from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import User

    _configure_model_from_params(params, User)

    try:
        user = User.find_one({'id': user_id})
        if not user:
            return {'error': 'User not found', 'success': False}

        user.delete()
        return {'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}
    finally:
        User.backend().disconnect()
