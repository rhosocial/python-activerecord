#!/usr/bin/env python3
"""
Example: SQLite Connection Pool Stress Test (Asynchronous)

This example demonstrates a stress test for the async connection pool by having
multiple async tasks repeatedly acquire and release connections from the same pool.
It verifies the reliability of PooledBackend under concurrent usage.

Run with: python connection_pool_stress_test_async.py
Or: .venv310\Scripts\python connection_pool_stress_test_async.py

Requirements:
    pip install aiosqlite
    # Or use the virtual environment: .venv*
"""

import asyncio
import tempfile
import os
import sys
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from rhosocial.activerecord.connection.pool import PoolConfig, AsyncBackendPool
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


async def worker_task(pool: AsyncBackendPool, worker_id: int, iterations: int):
    """Worker function that repeatedly acquires and releases connections."""
    success_count = 0
    error_count = 0
    
    for i in range(iterations):
        backend = None
        try:
            # Acquire connection from pool
            backend = await pool.acquire(timeout=10.0)
            
            # Output backend info for verification
            print(f"  [Worker {worker_id}] Iteration {i + 1}/{iterations}")
            print(f"    threadsafety: {backend.threadsafety}")
            print(f"    mode: {pool.connection_mode}")
            
            # Execute a simple query to verify connection works
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend.execute("SELECT 1 AS test", [], options=options)
            
            if result.data and result.data[0]["test"] == 1:
                success_count += 1
                print(f"    [Worker {worker_id}] Query OK")
            else:
                error_count += 1
                print(f"    [Worker {worker_id}] Query failed: unexpected result")
            
            # Small delay to simulate work
            await asyncio.sleep(0.01)
            
        except Exception as e:
            error_count += 1
            print(f"    [Worker {worker_id}] Error: {e}")
        finally:
            if backend is not None:
                await pool.release(backend)
    
    return worker_id, success_count, error_count


async def main():
    print("=" * 70)
    print("SQLite Connection Pool Stress Test (Asynchronous)")
    print("=" * 70)
    
    # Use a temporary file database so all connections share the same data
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name
    
    try:
        # Create backend to get threadsafety info
        test_backend = AsyncSQLiteBackend(database=db_path)
        await test_backend.connect()
        print(f"Backend threadsafety: {test_backend.threadsafety}")
        print(f"  0 = None (not thread-safe)")
        print(f"  1 = aiosqlite (only supports SQL)")
        print(f"  2 = Full thread-safe")
        await test_backend.disconnect()
        
        # Create connection pool
        config = PoolConfig(
            min_size=5,
            max_size=20,
            connection_mode="auto",  # auto-detect based on threadsafety
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
        )
        
        print(f"\nPool configuration:")
        print(f"  min_size: {config.min_size}")
        print(f"  max_size: {config.max_size}")
        print(f"  connection_mode: {config.connection_mode}")
        print(f"  validate_on_borrow: {config.validate_on_borrow}")
        print(f"  validation_query: {config.validation_query}")
        
        pool = await AsyncBackendPool.create(config)
        
        print(f"\nEffective connection mode: {pool.connection_mode}")
        
        print(f"\nPool initial stats: {pool.get_stats()}")
        
        # -----------------------------------------------------------
        # Stress test with multiple async tasks
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Starting stress test with 10 workers, 20 iterations each")
        print("-" * 50)
        
        num_workers = 10
        iterations = 20
        
        start_time = time.time()
        
        tasks = [
            worker_task(pool, i, iterations)
            for i in range(num_workers)
        ]
        
        results = await asyncio.gather(*tasks)
        
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
        
        for result in results:
            worker_id, success, errors = result
            print(f"Worker {worker_id} completed: {success} success, {errors} errors")
        
        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Cleanup")
        print("-" * 50)
        
        await pool.close()
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
    asyncio.run(main())