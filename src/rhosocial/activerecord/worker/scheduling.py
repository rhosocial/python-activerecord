# src/rhosocial/activerecord/worker/scheduling.py
"""
Worker Scheduling Strategies.

Provides pluggable scheduling strategies for WorkerPool task distribution.
Each strategy selects which Worker should receive the next task.

Available Strategies:
- LEAST_TASKS: Select Worker with fewest current tasks (default, best load balancing)
- ROUND_ROBIN: Rotate through Workers in order
- RANDOM: Randomly select a ready Worker
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional


class SchedulePolicy(Enum):
    """
    Scheduling policy enumeration.

    Used to specify which scheduling strategy the WorkerPool should use
    for task distribution.
    """
    LEAST_TASKS = "least_tasks"  # Select Worker with fewest tasks
    ROUND_ROBIN = "round_robin"  # Rotate through Workers
    RANDOM = "random"            # Random selection


class SchedulingStrategy(ABC):
    """
    Abstract base class for Worker scheduling strategies.

    All strategies must implement select_worker() which chooses
    which Worker should receive the next task.
    """

    @abstractmethod
    def select_worker(
        self,
        worker_task_count: Dict[int, int],
        worker_ready: Dict[int, bool],
    ) -> Optional[int]:
        """
        Select a Worker to receive the next task.

        Args:
            worker_task_count: Mapping of Worker ID to current task count
            worker_ready: Mapping of Worker ID to ready status

        Returns:
            Selected Worker ID, or None if no Workers are ready
        """
        pass


class LeastTasksStrategy(SchedulingStrategy):
    """
    Least tasks first scheduling strategy.

    Selects the Worker with the fewest current tasks among ready Workers.
    This provides the best load balancing for variable-duration tasks.

    When multiple Workers have the same minimum task count, the one
    with the lowest Worker ID is selected (deterministic tie-breaking).
    """

    def select_worker(
        self,
        worker_task_count: Dict[int, int],
        worker_ready: Dict[int, bool],
    ) -> Optional[int]:
        """
        Select Worker with fewest current tasks.

        Args:
            worker_task_count: Mapping of Worker ID to current task count
            worker_ready: Mapping of Worker ID to ready status

        Returns:
            Worker ID with fewest tasks, or None if no Workers ready
        """
        # Get list of ready Workers
        ready_workers = [w for w, r in worker_ready.items() if r]
        if not ready_workers:
            return None

        # Find Worker with minimum task count
        return min(ready_workers, key=lambda w: worker_task_count.get(w, 0))


class RoundRobinStrategy(SchedulingStrategy):
    """
    Round-robin scheduling strategy.

    Rotates through Workers in order, distributing tasks evenly.
    Best suited for tasks with uniform execution duration.

    The internal index wraps around when reaching the end of
    the Worker list, ensuring continuous rotation.
    """

    def __init__(self) -> None:
        self._index: int = 0

    def select_worker(
        self,
        worker_task_count: Dict[int, int],
        worker_ready: Dict[int, bool],
    ) -> Optional[int]:
        """
        Select next Worker in rotation order.

        Args:
            worker_task_count: Mapping of Worker ID to current task count
                               (not used in round-robin, included for interface consistency)
            worker_ready: Mapping of Worker ID to ready status

        Returns:
            Next Worker ID in rotation, or None if no Workers ready
        """
        # Get sorted list of ready Workers for deterministic ordering
        ready_workers = sorted(w for w, r in worker_ready.items() if r)
        if not ready_workers:
            return None

        # Select Worker at current index and advance
        wid = ready_workers[self._index % len(ready_workers)]
        self._index += 1
        return wid


class RandomStrategy(SchedulingStrategy):
    """
    Random scheduling strategy.

    Randomly selects a ready Worker for each task.
    Simple strategy that avoids systematic biases but may
    result in uneven distribution with few tasks.
    """

    def select_worker(
        self,
        worker_task_count: Dict[int, int],
        worker_ready: Dict[int, bool],
    ) -> Optional[int]:
        """
        Select a random ready Worker.

        Args:
            worker_task_count: Mapping of Worker ID to current task count
                               (not used in random, included for interface consistency)
            worker_ready: Mapping of Worker ID to ready status

        Returns:
            Randomly selected Worker ID, or None if no Workers ready
        """
        ready_workers = [w for w, r in worker_ready.items() if r]
        if not ready_workers:
            return None

        return random.choice(ready_workers)


def create_scheduler(policy: SchedulePolicy) -> SchedulingStrategy:
    """
    Factory function to create a scheduling strategy.

    Args:
        policy: The scheduling policy to create

    Returns:
        A new SchedulingStrategy instance

    Raises:
        ValueError: If policy is not recognized
    """
    if policy == SchedulePolicy.LEAST_TASKS:
        return LeastTasksStrategy()
    elif policy == SchedulePolicy.ROUND_ROBIN:
        return RoundRobinStrategy()
    elif policy == SchedulePolicy.RANDOM:
        return RandomStrategy()
    else:
        raise ValueError(f"Unknown scheduling policy: {policy}")
