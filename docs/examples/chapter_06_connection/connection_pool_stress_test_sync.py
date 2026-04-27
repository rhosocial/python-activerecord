#!/usr/bin/env python3
"""
Example: SQLite Connection Pool Stress Test (Synchronous)

This example demonstrates a stress test for the connection pool by having multiple
threads repeatedly acquire and release connections from the same pool.
It verifies the reliability of PooledBackend under concurrent usage.

The test controls thread execution timing to ensure sequential usage as much as possible.

Run with: python connection_pool_stress_test_sync.py
Or: .venv310\Scripts\python connection_pool_stress_test_sync.py

Requirements:
    pip install aiosqlite
    # Or use the virtual environment: .venv*
"""

import sys
import os
import threading
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def worker_thread(pool: BackendPool, worker_id: int, iterations: int, lock: threading.Lock):
    """Worker function that repeatedly acquires and releases connections."""
    success_count = 0
    error_count = 0
    
    for i in range(iterations):
        backend = None
        try:
            # Acquire connection from pool
            backend = pool.acquire(timeout=10.0)
            
            # Output backend info for verification
            with lock:
                print(f"  [Worker {worker_id}] Iteration {i + 1}/{iterations}")
                print(f"    threadsafety: {backend.threadsafety}")
                print(f"    mode: {pool.connection_mode}")
            
            # Execute a simple query to verify connection works
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT 1 AS test", [], options=options)
            
            if result.data and result.data[0]["test"] == 1:
                success_count += 1
                with lock:
                    print(f"    [Worker {worker_id}] Query OK")
            else:
                error_count += 1
                with lock:
                    print(f"    [Worker {worker_id}] Query failed: unexpected result")
            
            # Small delay to simulate work (sequential as much as possible)
            time.sleep(0.01)
            
        except Exception as e:
            error_count += 1
            with lock:
                print(f"    [Worker {worker_id}] Error: {e}")
        finally:
            if backend is not None:
                pool.release(backend)
    
    return worker_id, success_count, error_count


def main():
    print("=" * 70)
    print("SQLite Connection Pool Stress Test (Synchronous)")
    print("=" * 70)
    
    # Use a temporary file database so all connections share the same data
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name
    
    try:
        # Create backend to get threadsafety info
        test_backend = SQLiteBackend(database=db_path)
        test_backend.connect()
        print(f"Backend threadsafety: {test_backend.threadsafety}")
        print(f"  0 = None (not thread-safe)")
        print(f"  1 = sqlite3 (only supports SQL)")
        print(f"  2 = Full thread-safe")
        test_backend.disconnect()
        
        # Create connection pool
        config = PoolConfig(
            min_size=5,
            max_size=20,
            connection_mode="auto",  # auto-detect based on threadsafety
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=db_path)
        )
        
        print(f"\nPool configuration:")
        print(f"  min_size: {config.min_size}")
        print(f"  max_size: {config.max_size}")
        print(f"  connection_mode: {config.connection_mode}")
        print(f"  validate_on_borrow: {config.validate_on_borrow}")
        print(f"  validation_query: {config.validation_query}")
        
        pool = BackendPool.create(config)
        
        print(f"\nEffective connection mode: {pool.connection_mode}")
        
        print(f"\nPool initial stats: {pool.get_stats()}")
        
        # -----------------------------------------------------------
        # Stress test with multiple threads
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Starting stress test with 10 workers, 20 iterations each")
        print("-" * 50)
        
        num_workers = 10
        iterations = 20
        lock = threading.Lock()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_thread, pool, i, iterations, lock)
                for i in range(num_workers)
            ]
            
            for future in as_completed(futures):
                worker_id, success, errors = future.result()
                print(f"Worker {worker_id} completed: {success} success, {errors} errors")
        
        elapsed = time.time() - start_time
        
        # -----------------------------------------------------------
        # Results
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Stress test results")
        print("-" * 50)
        
        stats = pool.get_stats()
        print(f"Total connections created: {stats.total_created}")
        print(f"Total acquired: {stats.total_acquired}")
        print(f"Total released: {stats.total_released}")
        print(f"Current available: {stats.current_available}")
        print(f"Current in use: {stats.current_in_use}")
        print(f"Elapsed time: {elapsed:.2f}s")
        
        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Cleanup")
        print("-" * 50)
        
        pool.close()
        print(f"Pool closed: {pool.is_closed}")
        
        print("\n" + "=" * 70)
        print("Stress test completed!")
        print("=" * 70)
        
    finally:
        # Clean up temporary database file
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()