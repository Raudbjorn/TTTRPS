"""
Statistics and reporting system for MBED processing operations
"""

import time
import json
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from ..core.result import Result

import logging
logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for a single processing operation."""
    operation_id: str
    operation_type: str  # 'chunk', 'embed', 'store', 'batch'
    start_time: float
    end_time: float
    duration: float
    success: bool
    items_processed: int = 0
    bytes_processed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def processing_rate(self) -> float:
        """Items processed per second."""
        if self.duration > 0:
            return self.items_processed / self.duration
        return 0.0

    @property
    def throughput_mbps(self) -> float:
        """Megabytes processed per second."""
        if self.duration > 0:
            return (self.bytes_processed / (1024 * 1024)) / self.duration
        return 0.0


@dataclass
class ComponentStats:
    """Statistics for a specific component."""
    component_name: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration: float = 0.0
    total_items_processed: int = 0
    total_bytes_processed: int = 0
    error_count_by_type: Dict[str, int] = field(default_factory=dict)
    recent_metrics: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_operations > 0:
            return (self.successful_operations / self.total_operations) * 100
        return 0.0

    @property
    def average_duration(self) -> float:
        """Average operation duration."""
        if self.total_operations > 0:
            return self.total_duration / self.total_operations
        return 0.0

    @property
    def average_processing_rate(self) -> float:
        """Average items processed per second."""
        if self.total_duration > 0:
            return self.total_items_processed / self.total_duration
        return 0.0


@dataclass
class SessionStats:
    """Statistics for an entire processing session."""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    total_bytes: int = 0
    component_stats: Dict[str, ComponentStats] = field(default_factory=dict)
    file_type_counts: Dict[str, int] = field(default_factory=dict)
    chunking_strategy_usage: Dict[str, int] = field(default_factory=dict)
    error_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Session duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def files_per_hour(self) -> float:
        """Files processed per hour."""
        duration_hours = self.duration / 3600
        if duration_hours > 0:
            return self.processed_files / duration_hours
        return 0.0

    @property
    def overall_success_rate(self) -> float:
        """Overall file processing success rate."""
        if self.total_files > 0:
            return (self.processed_files / self.total_files) * 100
        return 0.0


class StatisticsCollector:
    """Collects and aggregates processing statistics."""

    def __init__(self):
        self.current_session: Optional[SessionStats] = None
        self.completed_sessions: List[SessionStats] = []
        self.metrics_history: 'collections.deque[ProcessingMetrics]' = __import__('collections').deque(maxlen=self.max_history_size)
        self.component_stats: Dict[str, ComponentStats] = defaultdict(ComponentStats)
        self.global_counters: Dict[str, int] = defaultdict(int)

        # Performance tracking
        self.performance_buckets: Dict[str, List[float]] = defaultdict(list)
        self.max_history_size = 10000

    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new processing session."""
        if session_id is None:
            session_id = f"session_{int(time.time())}_{id(self) % 10000}"

        # End current session if active
        if self.current_session:
            self.end_session()

        self.current_session = SessionStats(
            session_id=session_id,
            start_time=time.time()
        )

        logger.info(f"Started statistics session: {session_id}")
        return session_id

    def end_session(self) -> Optional[SessionStats]:
        """End the current processing session."""
        if not self.current_session:
            return None

        self.current_session.end_time = time.time()
        completed_session = self.current_session

        # Archive session
        self.completed_sessions.append(completed_session)
        self.current_session = None

        logger.info(f"Ended statistics session: {completed_session.session_id}")
        return completed_session

    def record_operation(
        self,
        operation_type: str,
        component: str,
        duration: float,
        success: bool,
        items_processed: int = 0,
        bytes_processed: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a processing operation."""
        operation_id = f"{operation_type}_{component}_{int(time.time())}_{len(self.metrics_history)}"

        # Create metrics record
        metrics = ProcessingMetrics(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=time.time() - duration,
            end_time=time.time(),
            duration=duration,
            success=success,
            items_processed=items_processed,
            bytes_processed=bytes_processed,
            error_message=error_message,
            metadata=metadata or {}
        )

        # Add to history
        self.metrics_history.append(metrics)

        # Update component stats
        if component not in self.component_stats:
            self.component_stats[component] = ComponentStats(component_name=component)

        comp_stats = self.component_stats[component]
        comp_stats.total_operations += 1
        comp_stats.total_duration += duration
        comp_stats.total_items_processed += items_processed
        comp_stats.total_bytes_processed += bytes_processed

        if success:
            comp_stats.successful_operations += 1
        else:
            comp_stats.failed_operations += 1
            if error_message:
                error_type = self._categorize_error(error_message)
                comp_stats.error_count_by_type[error_type] = comp_stats.error_count_by_type.get(error_type, 0) + 1

        comp_stats.recent_metrics.append(metrics)

        # Update session stats
        if self.current_session:
            self._update_session_stats(metrics, component)

        # Update performance buckets
        self.performance_buckets[f"{operation_type}_{component}"].append(duration)

        # Maintain history size
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

        return operation_id

    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into type."""
        error_lower = error_message.lower()

        if 'memory' in error_lower or 'oom' in error_lower:
            return 'memory_error'
        elif 'file' in error_lower or 'permission' in error_lower:
            return 'file_error'
        elif 'network' in error_lower or 'timeout' in error_lower:
            return 'network_error'
        elif 'parse' in error_lower or 'syntax' in error_lower:
            return 'parsing_error'
        elif 'model' in error_lower or 'embedding' in error_lower:
            return 'model_error'
        else:
            return 'unknown_error'

    def _update_session_stats(self, metrics: ProcessingMetrics, component: str):
        """Update current session statistics."""
        if not self.current_session:
            return

        session = self.current_session

        # Update component stats within session
        if component not in session.component_stats:
            session.component_stats[component] = ComponentStats(component_name=component)

        comp_stats = session.component_stats[component]
        comp_stats.total_operations += 1
        comp_stats.total_duration += metrics.duration
        comp_stats.total_items_processed += metrics.items_processed
        comp_stats.total_bytes_processed += metrics.bytes_processed

        if metrics.success:
            comp_stats.successful_operations += 1
        else:
            comp_stats.failed_operations += 1

    def record_file_processed(
        self,
        file_path: str,
        file_type: str,
        success: bool,
        chunks_generated: int = 0,
        embeddings_generated: int = 0,
        file_size_bytes: int = 0,
        chunking_strategy: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Record file processing results."""
        if not self.current_session:
            self.start_session()

        session = self.current_session

        # Update file counts
        session.total_files += 1
        if success:
            session.processed_files += 1
            session.total_chunks += chunks_generated
            session.total_embeddings += embeddings_generated
        else:
            session.failed_files += 1
            if error_message:
                error_type = self._categorize_error(error_message)
                session.error_summary[error_type] = session.error_summary.get(error_type, 0) + 1

        # Update type counts
        session.file_type_counts[file_type] = session.file_type_counts.get(file_type, 0) + 1
        session.total_bytes += file_size_bytes

        # Update chunking strategy usage
        if chunking_strategy:
            session.chunking_strategy_usage[chunking_strategy] = \
                session.chunking_strategy_usage.get(chunking_strategy, 0) + 1

        # Update global counters
        self.global_counters['total_files_processed'] += 1
        self.global_counters[f'files_{file_type}'] += 1

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'session_overview': self._get_session_overview(),
            'component_performance': self._get_component_performance(),
            'operation_percentiles': self._get_operation_percentiles(),
            'error_analysis': self._get_error_analysis(),
            'throughput_analysis': self._get_throughput_analysis(),
            'recent_performance': self._get_recent_performance()
        }

        return summary

    def _get_session_overview(self) -> Dict[str, Any]:
        """Get overview of current and recent sessions."""
        overview = {
            'current_session': None,
            'completed_sessions': len(self.completed_sessions),
            'total_operations': len(self.metrics_history)
        }

        if self.current_session:
            session = self.current_session
            overview['current_session'] = {
                'session_id': session.session_id,
                'duration_minutes': session.duration / 60,
                'files_processed': session.processed_files,
                'success_rate': session.overall_success_rate,
                'files_per_hour': session.files_per_hour,
                'total_chunks': session.total_chunks,
                'total_embeddings': session.total_embeddings
            }

        # Recent sessions summary
        if self.completed_sessions:
            recent_sessions = self.completed_sessions[-5:]
            overview['recent_sessions'] = [
                {
                    'session_id': s.session_id,
                    'duration_minutes': s.duration / 60,
                    'files_processed': s.processed_files,
                    'success_rate': s.overall_success_rate
                }
                for s in recent_sessions
            ]

        return overview

    def _get_component_performance(self) -> Dict[str, Any]:
        """Get performance metrics for each component."""
        component_perf = {}

        for component_name, stats in self.component_stats.items():
            component_perf[component_name] = {
                'total_operations': stats.total_operations,
                'success_rate': stats.success_rate,
                'average_duration': stats.average_duration,
                'processing_rate': stats.average_processing_rate,
                'error_breakdown': dict(stats.error_count_by_type)
            }

        return component_perf

    def _get_operation_percentiles(self) -> Dict[str, Any]:
        """Get percentile analysis of operation durations."""
        percentiles = {}

        for operation_key, durations in self.performance_buckets.items():
            if durations:
                try:
                    percentiles[operation_key] = {
                        'count': len(durations),
                        'p50': self._safe_percentile(durations, 50),
                        'p90': self._safe_percentile(durations, 90),
                        'p95': self._safe_percentile(durations, 95),
                        'p99': self._safe_percentile(durations, 99),
                        'mean': statistics.mean(durations),
                        'min': min(durations),
                        'max': max(durations)
                    }
                except statistics.StatisticsError:
                    percentiles[operation_key] = {'count': len(durations), 'error': 'insufficient_data'}

        return percentiles

    def _safe_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile with proper fallbacks for edge cases."""
        if not values:
            return 0.0

        if len(values) == 1:
            return values[0]

        # For small datasets, use simple percentile calculation
        if len(values) < 10:
            sorted_values = sorted(values)
            index = (percentile / 100.0) * (len(sorted_values) - 1)
            if index.is_integer():
                return sorted_values[int(index)]
            else:
                lower = sorted_values[int(index)]
                upper = sorted_values[int(index) + 1]
                return lower + (upper - lower) * (index - int(index))

        # For larger datasets, use statistics module with fallbacks
        try:
            if percentile == 50:
                return statistics.median(values)
            elif percentile == 90:
                quantiles = statistics.quantiles(values, n=10)
                return quantiles[8] if len(quantiles) > 8 else max(values)
            elif percentile == 95:
                quantiles = statistics.quantiles(values, n=20)
                return quantiles[18] if len(quantiles) > 18 else max(values)
            elif percentile == 99:
                quantiles = statistics.quantiles(values, n=100)
                return quantiles[98] if len(quantiles) > 98 else max(values)
            else:
                # Generic percentile calculation
                sorted_values = sorted(values)
                index = (percentile / 100.0) * (len(sorted_values) - 1)
                if index.is_integer():
                    return sorted_values[int(index)]
                else:
                    lower = sorted_values[int(index)]
                    upper = sorted_values[int(index) + 1]
                    return lower + (upper - lower) * (index - int(index))
        except (statistics.StatisticsError, IndexError, ZeroDivisionError):
            # Fallback to max/min for edge cases
            if percentile >= 95:
                return max(values)
            elif percentile <= 5:
                return min(values)
            else:
                return statistics.median(values)

    def _get_error_analysis(self) -> Dict[str, Any]:
        """Get comprehensive error analysis."""
        error_analysis = {
            'total_errors': 0,
            'error_rate': 0.0,
            'error_categories': defaultdict(int),
            'frequent_errors': [],
            'error_trends': []
        }

        # Count errors in metrics history
        failed_operations = [m for m in self.metrics_history if not m.success]
        error_analysis['total_errors'] = len(failed_operations)

        if self.metrics_history:
            error_analysis['error_rate'] = (len(failed_operations) / len(self.metrics_history)) * 100

        # Categorize errors
        for metrics in failed_operations:
            if metrics.error_message:
                error_type = self._categorize_error(metrics.error_message)
                error_analysis['error_categories'][error_type] += 1

        # Convert defaultdict to regular dict
        error_analysis['error_categories'] = dict(error_analysis['error_categories'])

        return error_analysis

    def _get_throughput_analysis(self) -> Dict[str, Any]:
        """Get throughput analysis across different metrics."""
        throughput = {
            'items_per_second': 0.0,
            'bytes_per_second': 0.0,
            'operations_per_minute': 0.0,
            'peak_throughput': 0.0
        }

        if self.metrics_history:
            # Calculate overall throughput
            total_items = sum(m.items_processed for m in self.metrics_history)
            total_bytes = sum(m.bytes_processed for m in self.metrics_history)
            total_duration = sum(m.duration for m in self.metrics_history)

            if total_duration > 0:
                throughput['items_per_second'] = total_items / total_duration
                throughput['bytes_per_second'] = total_bytes / total_duration

            # Operations per minute
            if self.metrics_history:
                time_span = self.metrics_history[-1].end_time - self.metrics_history[0].start_time
                if time_span > 0:
                    throughput['operations_per_minute'] = len(self.metrics_history) / (time_span / 60)

            # Peak throughput (highest rate in any single operation)
            peak_rates = [m.processing_rate for m in self.metrics_history if m.processing_rate > 0]
            if peak_rates:
                throughput['peak_throughput'] = max(peak_rates)

        return throughput

    def _get_recent_performance(self) -> Dict[str, Any]:
        """Get recent performance trends."""
        recent_metrics = self.metrics_history[-50:] if len(self.metrics_history) >= 50 else self.metrics_history

        if not recent_metrics:
            return {'no_data': True}

        # Calculate recent trends
        recent_success_rate = (sum(1 for m in recent_metrics if m.success) / len(recent_metrics)) * 100
        recent_avg_duration = sum(m.duration for m in recent_metrics) / len(recent_metrics)

        return {
            'operations_count': len(recent_metrics),
            'success_rate': recent_success_rate,
            'average_duration': recent_avg_duration,
            'time_span_minutes': (recent_metrics[-1].end_time - recent_metrics[0].start_time) / 60
        }

    def export_statistics(self, file_path: Path, format: str = 'json') -> Result[None, str]:
        """Export statistics to file."""
        try:
            stats_data = {
                'export_timestamp': time.time(),
                'current_session': self.current_session.__dict__ if self.current_session else None,
                'completed_sessions': [s.__dict__ for s in self.completed_sessions],
                'component_stats': {name: stats.__dict__ for name, stats in self.component_stats.items()},
                'global_counters': dict(self.global_counters),
                'performance_summary': self.get_performance_summary()
            }

            if format == 'json':
                with open(file_path, 'w') as f:
                    json.dump(stats_data, f, indent=2, default=str)
            else:
                return Result.Err(f"Unsupported export format: {format}")

            logger.info(f"Statistics exported to: {file_path}")
            return Result.Ok(None)

        except Exception as e:
            return Result.Err(f"Failed to export statistics: {str(e)}")

    def reset_statistics(self, keep_sessions: bool = True):
        """Reset collected statistics."""
        if not keep_sessions:
            self.completed_sessions.clear()
            self.current_session = None

        self.metrics_history.clear()
        self.component_stats.clear()
        self.global_counters.clear()
        self.performance_buckets.clear()

        logger.info("Statistics reset")

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time processing metrics."""
        current_time = time.time()
        recent_window = 60  # Last 60 seconds

        recent_metrics = [
            m for m in self.metrics_history
            if current_time - m.end_time <= recent_window
        ]

        if not recent_metrics:
            return {'no_recent_data': True}

        return {
            'operations_last_minute': len(recent_metrics),
            'success_rate_last_minute': (sum(1 for m in recent_metrics if m.success) / len(recent_metrics)) * 100,
            'average_duration_last_minute': sum(m.duration for m in recent_metrics) / len(recent_metrics),
            'items_processed_last_minute': sum(m.items_processed for m in recent_metrics),
            'current_session_active': self.current_session is not None
        }


# Global statistics collector instance
global_stats_collector: Optional[StatisticsCollector] = None


def get_stats_collector() -> StatisticsCollector:
    """Get or create global statistics collector."""
    global global_stats_collector

    if global_stats_collector is None:
        global_stats_collector = StatisticsCollector()

    return global_stats_collector


def record_operation(operation_type: str, component: str, **kwargs) -> str:
    """Convenience function for recording operations."""
    return get_stats_collector().record_operation(operation_type, component, **kwargs)


def start_session(session_id: Optional[str] = None) -> str:
    """Convenience function for starting a session."""
    return get_stats_collector().start_session(session_id)


def end_session() -> Optional[SessionStats]:
    """Convenience function for ending a session."""
    return get_stats_collector().end_session()