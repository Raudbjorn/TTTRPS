"""
Parallel processing coordinator for optimal multi-threading and multi-processing
"""

import os
import threading
import multiprocessing as mp
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Union, Iterator, TypeVar, Generic
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, Future
from queue import Queue, Empty
from threading import Lock, Event
from ..core.result import Result

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ProcessingTask(Generic[T]):
    """A task to be processed."""
    data: T
    task_id: str
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult(Generic[R]):
    """Result of processing a task."""
    task_id: str
    result: Union[R, Exception]
    processing_time: float
    worker_id: str
    success: bool = True


@dataclass
class WorkerStats:
    """Statistics for a worker process/thread."""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    last_activity: float = field(default_factory=time.time)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    def update_stats(self, processing_time: float, success: bool):
        """Update worker statistics."""
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1

        self.total_processing_time += processing_time
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks > 0:
            self.average_processing_time = self.total_processing_time / total_tasks

        self.last_activity = time.time()


@dataclass
class CoordinatorConfig:
    """Configuration for parallel processing coordinator."""
    max_threads: Optional[int] = None
    max_processes: Optional[int] = None
    use_processes: bool = False
    task_queue_size: int = 1000
    result_queue_size: int = 1000
    worker_timeout: float = 300.0  # 5 minutes
    enable_monitoring: bool = True
    monitoring_interval: float = 5.0
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None
    auto_scale: bool = True
    min_workers: int = 1
    max_workers: Optional[int] = None


class ParallelCoordinator:
    """Coordinates parallel processing with optimal resource management."""

    def __init__(self, config: CoordinatorConfig):
        self.config = config
        self.task_queue = Queue(maxsize=config.task_queue_size)
        self.result_queue = Queue(maxsize=config.result_queue_size)
        self.worker_stats: Dict[str, WorkerStats] = {}
        self.active_workers: List[str] = []
        self.shutdown_event = Event()
        self.stats_lock = Lock()

        # Auto-detect optimal worker counts if not specified
        if self.config.max_threads is None:
            self.config.max_threads = min(32, (os.cpu_count() or 1) + 4)

        if self.config.max_processes is None:
            self.config.max_processes = os.cpu_count() or 1

        if self.config.max_workers is None:
            self.config.max_workers = self.config.max_processes if config.use_processes else self.config.max_threads

        # Initialize monitoring thread
        self.monitor_thread = None
        if config.enable_monitoring:
            self.monitor_thread = threading.Thread(target=self._monitor_workers, daemon=True)

        logger.info(f"ParallelCoordinator initialized with {self.config.max_workers} max workers")

    def process_tasks(
        self,
        tasks: List[ProcessingTask[T]],
        processor_func: Callable[[T], R],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Result[List[ProcessingResult[R]], str]:
        """Process tasks in parallel with optimal resource allocation."""
        try:
            if not tasks:
                return Result.Ok([])

            # Start monitoring if enabled
            if self.monitor_thread and not self.monitor_thread.is_alive():
                self.monitor_thread.start()

            # Determine optimal number of workers
            num_workers = min(len(tasks), self.config.max_workers)

            logger.info(f"Processing {len(tasks)} tasks with {num_workers} workers")

            if self.config.use_processes:
                return self._process_with_processes(tasks, processor_func, num_workers, progress_callback)
            else:
                return self._process_with_threads(tasks, processor_func, num_workers, progress_callback)

        except Exception as e:
            return Result.Err(f"Parallel processing failed: {str(e)}")

    def _process_with_threads(
        self,
        tasks: List[ProcessingTask[T]],
        processor_func: Callable[[T], R],
        num_workers: int,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> Result[List[ProcessingResult[R]], str]:
        """Process tasks using thread pool."""
        results = []

        try:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._execute_task, task, processor_func): task
                    for task in tasks
                }

                # Collect results
                completed = 0
                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        result = future.result()
                        results.append(result)

                        # Update worker stats with thread safety
                        with self.stats_lock:
                            if result.worker_id in self.worker_stats:
                                self.worker_stats[result.worker_id].update_stats(
                                    result.processing_time, result.success
                                )

                    except Exception as e:
                        # Create error result
                        error_result = ProcessingResult(
                            task_id=task.task_id,
                            result=e,
                            processing_time=0.0,
                            worker_id="unknown",
                            success=False
                        )
                        results.append(error_result)

                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(tasks))

            return Result.Ok(results)

        except Exception as e:
            return Result.Err(f"Thread pool processing failed: {str(e)}")

    def _process_with_processes(
        self,
        tasks: List[ProcessingTask[T]],
        processor_func: Callable[[T], R],
        num_workers: int,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> Result[List[ProcessingResult[R]], str]:
        """Process tasks using process pool."""
        results = []

        try:
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._execute_task, task, processor_func): task
                    for task in tasks
                }

                # Collect results
                completed = 0
                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        result = future.result(timeout=self.config.worker_timeout)
                        results.append(result)

                        # Update worker stats with thread safety
                        with self.stats_lock:
                            if result.worker_id in self.worker_stats:
                                self.worker_stats[result.worker_id].update_stats(
                                    result.processing_time, result.success
                                )

                    except Exception as e:
                        # Create error result
                        error_result = ProcessingResult(
                            task_id=task.task_id,
                            result=e,
                            processing_time=0.0,
                            worker_id="unknown",
                            success=False
                        )
                        results.append(error_result)

                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(tasks))

            return Result.Ok(results)

        except Exception as e:
            return Result.Err(f"Process pool processing failed: {str(e)}")

    def _execute_task(self, task: ProcessingTask[T], processor_func: Callable[[T], R]) -> ProcessingResult[R]:
        """Execute a single task and return result."""
        start_time = time.time()
        worker_id = f"{threading.current_thread().ident or os.getpid()}"

        # Initialize worker stats if needed
        if worker_id not in self.worker_stats:
            with self.stats_lock:
                if worker_id not in self.worker_stats:
                    self.worker_stats[worker_id] = WorkerStats(worker_id=worker_id)

        try:
            # Execute the processing function
            result = processor_func(task.data)
            processing_time = time.time() - start_time

            return ProcessingResult(
                task_id=task.task_id,
                result=result,
                processing_time=processing_time,
                worker_id=worker_id,
                success=True
            )

        except Exception as e:
            processing_time = time.time() - start_time

            return ProcessingResult(
                task_id=task.task_id,
                result=e,
                processing_time=processing_time,
                worker_id=worker_id,
                success=False
            )

    async def process_tasks_async(
        self,
        tasks: List[ProcessingTask[T]],
        processor_func: Callable[[T], R],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Result[List[ProcessingResult[R]], str]:
        """Process tasks asynchronously with optimal concurrency."""
        try:
            if not tasks:
                return Result.Ok([])

            # Determine optimal concurrency level
            max_concurrency = min(len(tasks), self.config.max_workers)

            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrency)

            async def process_task_async(task: ProcessingTask[T]) -> ProcessingResult[R]:
                async with semaphore:
                    loop = asyncio.get_event_loop()
                    # Run processor in thread pool to avoid blocking
                    return await loop.run_in_executor(None, self._execute_task, task, processor_func)

            # Create tasks for all items
            async_tasks = [process_task_async(task) for task in tasks]

            # Process with progress tracking
            results = []
            completed = 0

            for coro in asyncio.as_completed(async_tasks):
                result = await coro
                results.append(result)

                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tasks))

            return Result.Ok(results)

        except Exception as e:
            return Result.Err(f"Async processing failed: {str(e)}")

    def _monitor_workers(self):
        """Monitor worker performance and resource usage."""
        logger.info("Worker monitoring started")

        while not self.shutdown_event.is_set():
            try:
                # Update worker statistics
                self._update_worker_resources()

                # Check for performance issues
                self._check_worker_health()

                # Auto-scale if enabled
                if self.config.auto_scale:
                    self._auto_scale_workers()

                # Sleep until next monitoring cycle
                self.shutdown_event.wait(self.config.monitoring_interval)

            except Exception as e:
                logger.warning(f"Worker monitoring error: {e}")

    def _update_worker_resources(self):
        """Update resource usage for active workers."""
        try:
            import psutil

            current_process = psutil.Process()

            # Get memory usage for main process
            memory_usage = current_process.memory_info().rss / (1024 * 1024)  # MB
            # Use interval=0.1 to get non-zero CPU percentage on first call
            cpu_usage = current_process.cpu_percent(interval=0.1)

            # Update stats for current process
            main_worker_id = str(os.getpid())
            if main_worker_id in self.worker_stats:
                self.worker_stats[main_worker_id].memory_usage_mb = memory_usage
                self.worker_stats[main_worker_id].cpu_usage_percent = cpu_usage

            # Update child processes if using multiprocessing
            for child in current_process.children():
                try:
                    child_memory = child.memory_info().rss / (1024 * 1024)
                    child_cpu = child.cpu_percent()
                    child_id = str(child.pid)

                    if child_id in self.worker_stats:
                        self.worker_stats[child_id].memory_usage_mb = child_memory
                        self.worker_stats[child_id].cpu_usage_percent = child_cpu

                except psutil.NoSuchProcess:
                    pass  # Process may have finished

        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            logger.warning(f"Resource monitoring error: {e}")

    def _check_worker_health(self):
        """Check worker health and performance."""
        current_time = time.time()
        unhealthy_workers = []

        with self.stats_lock:
            for worker_id, stats in self.worker_stats.items():
                # Check for memory issues
                if (self.config.memory_limit_mb and
                    stats.memory_usage_mb > self.config.memory_limit_mb):
                    logger.warning(f"Worker {worker_id} exceeding memory limit: {stats.memory_usage_mb}MB")
                    unhealthy_workers.append(worker_id)

                # Check for CPU issues
                if (self.config.cpu_limit_percent and
                    stats.cpu_usage_percent > self.config.cpu_limit_percent):
                    logger.warning(f"Worker {worker_id} exceeding CPU limit: {stats.cpu_usage_percent}%")

                # Check for inactive workers
                time_since_activity = current_time - stats.last_activity
                if time_since_activity > self.config.worker_timeout:
                    logger.warning(f"Worker {worker_id} inactive for {time_since_activity:.1f}s")
                    unhealthy_workers.append(worker_id)

        # Remove unhealthy workers from active list
        for worker_id in unhealthy_workers:
            if worker_id in self.active_workers:
                self.active_workers.remove(worker_id)

    def _auto_scale_workers(self):
        """Automatically scale workers based on performance and queue size."""
        # This would implement dynamic scaling logic
        # For now, just log current status
        active_count = len(self.active_workers)
        queue_size = self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else 0

        if queue_size > active_count * 2:
            logger.info(f"High queue pressure: {queue_size} tasks, {active_count} workers")
        elif queue_size == 0 and active_count > self.config.min_workers:
            logger.info(f"Low queue pressure: {queue_size} tasks, {active_count} workers")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        with self.stats_lock:
            total_completed = sum(stats.tasks_completed for stats in self.worker_stats.values())
            total_failed = sum(stats.tasks_failed for stats in self.worker_stats.values())
            total_time = sum(stats.total_processing_time for stats in self.worker_stats.values())

            avg_processing_time = total_time / max(total_completed, 1)

            worker_summaries = {}
            for worker_id, stats in self.worker_stats.items():
                worker_summaries[worker_id] = {
                    'tasks_completed': stats.tasks_completed,
                    'tasks_failed': stats.tasks_failed,
                    'success_rate': stats.tasks_completed / max(stats.tasks_completed + stats.tasks_failed, 1),
                    'average_processing_time': stats.average_processing_time,
                    'memory_usage_mb': stats.memory_usage_mb,
                    'cpu_usage_percent': stats.cpu_usage_percent,
                    'last_activity': stats.last_activity
                }

            return {
                'total_workers': len(self.worker_stats),
                'active_workers': len(self.active_workers),
                'total_tasks_completed': total_completed,
                'total_tasks_failed': total_failed,
                'overall_success_rate': total_completed / max(total_completed + total_failed, 1),
                'average_processing_time': avg_processing_time,
                'worker_details': worker_summaries,
                'configuration': {
                    'max_workers': self.config.max_workers,
                    'use_processes': self.config.use_processes,
                    'auto_scale': self.config.auto_scale,
                    'monitoring_enabled': self.config.enable_monitoring
                }
            }

    def shutdown(self):
        """Shutdown the coordinator and cleanup resources."""
        logger.info("Shutting down ParallelCoordinator")

        # Signal shutdown
        self.shutdown_event.set()

        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        # Clear worker stats
        with self.stats_lock:
            self.worker_stats.clear()
            self.active_workers.clear()

        logger.info("ParallelCoordinator shutdown complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Utility functions for creating common task patterns

def create_file_processing_tasks(file_paths: List[str]) -> List[ProcessingTask[str]]:
    """Create processing tasks for file paths."""
    tasks = []
    for i, file_path in enumerate(file_paths):
        task = ProcessingTask(
            data=file_path,
            task_id=f"file_{i}_{hash(file_path) % 10000}",
            priority=0,
            metadata={'file_path': file_path, 'index': i}
        )
        tasks.append(task)
    return tasks


def create_batch_processing_tasks(items: List[T], batch_size: int = 100) -> List[ProcessingTask[List[T]]]:
    """Create processing tasks for batched items."""
    tasks = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        task = ProcessingTask(
            data=batch,
            task_id=f"batch_{i // batch_size}",
            priority=0,
            metadata={'batch_size': len(batch), 'start_index': i}
        )
        tasks.append(task)
    return tasks