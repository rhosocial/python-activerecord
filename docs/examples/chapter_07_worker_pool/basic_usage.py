# docs/examples/worker_pool/basic_usage.py
"""
Basic WorkerPool usage examples.

This module demonstrates:
- Simple task submission
- Batch processing
- Result collection with Future
- Error handling
"""

from rhosocial.activerecord.worker import WorkerPool, TaskContext


# Task functions MUST accept ctx as the first argument
def double(ctx: TaskContext, n: int) -> int:
    """Simple task that doubles a number."""
    return n * 2


def compute_sum(ctx: TaskContext, numbers: list) -> int:
    """Task that computes sum of a list."""
    return sum(numbers)


def failing_task(ctx: TaskContext, value: int) -> int:
    """Task that fails for demonstration."""
    if value < 0:
        raise ValueError("Value cannot be negative")
    return value * 2


def main():
    """Run basic usage examples."""
    print("=== Basic WorkerPool Usage ===\n")

    # Example 1: Single task submission
    print("1. Single task submission:")
    with WorkerPool(n_workers=2) as pool:
        future = pool.submit(double, 5)
        result = future.result(timeout=10)
        print(f"   double(5) = {result}")

    # Example 2: Multiple tasks
    print("\n2. Multiple tasks:")
    with WorkerPool(n_workers=4) as pool:
        futures = [pool.submit(double, i) for i in range(10)]
        results = [f.result(timeout=10) for f in futures]
        print(f"   Results: {results}")

    # Example 3: Using map for batch processing
    print("\n3. Using map() for batch processing:")
    with WorkerPool(n_workers=4) as pool:
        # map() automatically distributes work and collects results in order
        results = pool.map(double, range(10), timeout=10)
        print(f"   map(double, 0-9) = {results}")

    # Example 4: Error handling
    print("\n4. Error handling:")
    with WorkerPool(n_workers=2) as pool:
        # Successful task
        future1 = pool.submit(failing_task, 5)
        try:
            result = future1.result(timeout=10)
            print(f"   Task with value=5: {result}")
        except Exception as e:
            print(f"   Error: {e}")

        # Failing task
        future2 = pool.submit(failing_task, -1)
        try:
            result = future2.result(timeout=10)
            print(f"   Task with value=-1: {result}")
        except Exception as e:
            print(f"   Task with value=-1 failed: {e}")

    # Example 5: Task with complex arguments
    print("\n5. Task with complex arguments:")
    with WorkerPool(n_workers=2) as pool:
        future = pool.submit(compute_sum, [1, 2, 3, 4, 5])
        result = future.result(timeout=10)
        print(f"   sum([1,2,3,4,5]) = {result}")

    # Example 6: Accessing execution metadata
    print("\n6. Execution metadata:")
    with WorkerPool(n_workers=2) as pool:
        future = pool.submit(double, 100)
        result = future.result(timeout=10)
        print(f"   Result: {result}")
        print(f"   Worker ID: {future.worker_id}")
        print(f"   Duration: {future.duration:.4f}s")
        print(f"   Memory delta: {future.memory_delta_mb:.4f}MB")

    print("\n=== All examples completed ===")


if __name__ == '__main__':
    main()
