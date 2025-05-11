"""Test cases for ThreadSafeDict implementation."""
import pytest
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.rhosocial.activerecord.interface.query import ThreadSafeDict


def test_basic_operations():
    """Test basic dictionary operations."""
    # Initialize with different methods
    empty_dict = ThreadSafeDict()
    assert len(empty_dict) == 0

    dict_from_dict = ThreadSafeDict({'a': 1, 'b': 2})
    assert dict_from_dict['a'] == 1
    assert dict_from_dict['b'] == 2

    dict_from_items = ThreadSafeDict([('c', 3), ('d', 4)])
    assert dict_from_items['c'] == 3
    assert dict_from_items['d'] == 4

    dict_from_kwargs = ThreadSafeDict(e=5, f=6)
    assert dict_from_kwargs['e'] == 5
    assert dict_from_kwargs['f'] == 6

    # Test setting and getting items
    test_dict = ThreadSafeDict()
    test_dict['key'] = 'value'
    assert test_dict['key'] == 'value'

    # Test updating with another dict
    test_dict.update({'another_key': 'another_value'})
    assert test_dict['another_key'] == 'another_value'

    # Test deleting items
    del test_dict['key']
    assert 'key' not in test_dict

    # Test len and contains
    assert len(test_dict) == 1
    assert 'another_key' in test_dict

    # Test get with default
    assert test_dict.get('nonexistent', 'default') == 'default'
    assert test_dict.get('another_key', 'default') == 'another_value'

    # Test clear
    test_dict.clear()
    assert len(test_dict) == 0


def test_copy_and_equality():
    """Test copy operation and equality comparison."""
    original = ThreadSafeDict({'a': 1, 'b': 2})
    copy = original.copy()

    # Copy should equal original
    assert original == copy
    assert copy == original

    # Modifying copy shouldn't affect original
    copy['c'] = 3
    assert 'c' not in original
    assert 'c' in copy

    # Thread-safe dicts are compared based on their internal data
    # which is thread-local, so we need to check content equality manually
    assert sorted(list(original.keys())) != sorted(list(copy.keys()))
    assert len(original) != len(copy)

    # For additional clarity, verify exact contents
    assert set(original.keys()) == {'a', 'b'}
    assert set(copy.keys()) == {'a', 'b', 'c'}

    # Test comparison with regular dict - this should work normally
    assert original.to_dict() == {'a': 1, 'b': 2}
    assert copy.to_dict() == {'a': 1, 'b': 2, 'c': 3}


def test_items_keys_values():
    """Test items(), keys(), and values() view methods."""
    test_dict = ThreadSafeDict({'a': 1, 'b': 2, 'c': 3})

    # Test keys
    keys = list(test_dict.keys())
    assert sorted(keys) == ['a', 'b', 'c']

    # Test values
    values = list(test_dict.values())
    assert sorted(values) == [1, 2, 3]

    # Test items
    items = list(test_dict.items())
    assert sorted(items) == [('a', 1), ('b', 2), ('c', 3)]

    # Test iteration
    keys_from_iter = []
    for key in test_dict:
        keys_from_iter.append(key)
    assert sorted(keys_from_iter) == ['a', 'b', 'c']


def test_pop_and_popitem():
    """Test pop() and popitem() methods."""
    test_dict = ThreadSafeDict({'a': 1, 'b': 2, 'c': 3})

    # Test pop with existing key
    value = test_dict.pop('a')
    assert value == 1
    assert 'a' not in test_dict
    assert len(test_dict) == 2

    # Test pop with default value
    value = test_dict.pop('nonexistent', 'default')
    assert value == 'default'
    assert len(test_dict) == 2

    # Test pop without default (should raise KeyError)
    with pytest.raises(KeyError):
        test_dict.pop('nonexistent')

    # Test popitem
    item = test_dict.popitem()
    assert item in [('b', 2), ('c', 3)]
    assert len(test_dict) == 1

    # Test popitem on empty dict
    test_dict.clear()
    with pytest.raises(KeyError):
        test_dict.popitem()


def test_setdefault():
    """Test setdefault() method."""
    test_dict = ThreadSafeDict()

    # When key doesn't exist
    value = test_dict.setdefault('key', 'default')
    assert value == 'default'
    assert test_dict['key'] == 'default'

    # When key already exists
    value = test_dict.setdefault('key', 'new_default')
    assert value == 'default'  # Returns existing value, not new default
    assert test_dict['key'] == 'default'  # Value remains unchanged


def test_additional_methods():
    """Test additional methods specific to ThreadSafeDict."""
    test_dict = ThreadSafeDict({'a': 1, 'b': 2})

    # Test to_dict
    regular_dict = test_dict.to_dict()
    assert isinstance(regular_dict, dict)
    assert regular_dict == {'a': 1, 'b': 2}

    # Test set_many
    test_dict.set_many([('c', 3), ('d', 4)])
    assert test_dict['c'] == 3
    assert test_dict['d'] == 4

    # Test get_many
    values = test_dict.get_many(['a', 'nonexistent', 'c'], 'default')
    assert values == [1, 'default', 3]


def test_thread_isolation():
    """Test that different threads have isolated data."""
    test_dict = ThreadSafeDict()

    def thread_a():
        test_dict['key'] = 'value_a'
        time.sleep(0.1)  # Give thread_b time to run
        assert test_dict['key'] == 'value_a'
        return True

    def thread_b():
        assert 'key' not in test_dict
        test_dict['key'] = 'value_b'
        assert test_dict['key'] == 'value_b'
        return True

    thread1 = threading.Thread(target=thread_a)
    thread2 = threading.Thread(target=thread_b)

    thread1.start()
    time.sleep(0.05)  # Give thread_a time to set its value
    thread2.start()

    thread1.join()
    thread2.join()

    # Main thread should still have empty dict
    assert 'key' not in test_dict


def test_concurrent_operations():
    """Test concurrent operations on ThreadSafeDict."""
    test_dict = ThreadSafeDict()

    def worker(worker_id):
        # Each worker will set its ID as both key and value
        test_dict[f'worker_{worker_id}'] = worker_id
        time.sleep(0.01)  # Small delay to increase chance of thread interaction

        # Check that our key persists for this thread
        assert test_dict[f'worker_{worker_id}'] == worker_id

        # Each worker will also read and update a common counter
        current = test_dict.get('counter', 0)
        test_dict['counter'] = current + 1

        return worker_id

    # Run multiple workers concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [future.result() for future in as_completed(futures)]

    # Verify that each worker added its own key
    assert sorted(results) == list(range(10))

    # Main thread should still have empty dict
    assert len(test_dict) == 0


def test_stress_isolation():
    """Stress test for thread isolation."""
    shared_dict = ThreadSafeDict()
    num_threads = 5
    operations_per_thread = 1000

    # Random operations to perform
    def thread_work(thread_id):
        # Each thread gets its own counter
        local_counter = 0

        # Each thread has its own namespace
        key_prefix = f"thread_{thread_id}_"

        for i in range(operations_per_thread):
            op = random.randint(0, 5)
            key = f"{key_prefix}{i % 100}"  # Use a subset of keys to encourage collisions

            if op == 0:  # set
                shared_dict[key] = i
                local_counter += 1
            elif op == 1:  # get
                try:
                    value = shared_dict[key]
                    # If we retrieved a value, it must be from this thread's namespace
                    assert key.startswith(key_prefix)
                except KeyError:
                    pass
            elif op == 2:  # delete
                if key in shared_dict:
                    del shared_dict[key]
                    local_counter -= 1
            elif op == 3:  # update
                shared_dict.update({key: i})
                local_counter += 1
            elif op == 4:  # clear (but only our namespace)
                for k in list(shared_dict.keys()):
                    if k.startswith(key_prefix):
                        del shared_dict[k]
                local_counter = 0
            elif op == 5:  # iterate
                count = 0
                for k in shared_dict:
                    if k.startswith(key_prefix):
                        count += 1
                assert count <= local_counter  # May be less due to concurrent ops

        return thread_id

    # Run threads
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(thread_work, i) for i in range(num_threads)]
        results = [future.result() for future in as_completed(futures)]

    # Verify all threads completed
    assert sorted(results) == list(range(num_threads))

    # Main thread should still have empty dict
    assert len(shared_dict) == 0