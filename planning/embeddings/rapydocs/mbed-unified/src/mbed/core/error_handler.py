"""
Unified error handling system for the MBED pipeline
"""

import logging
import traceback
import json
from typing import Dict, Any, Optional, List, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import deque
from .result import Result

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    FILE_ACCESS = "file_access"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORAGE = "storage"
    NETWORK = "network"
    MEMORY = "memory"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    file_path: Optional[str] = None
    chunk_index: Optional[int] = None
    batch_index: Optional[int] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MBEDError:
    """Structured error representation."""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: Optional[ErrorContext] = None
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    error_id: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
            import hashlib
            msg_hash = hashlib.sha256(self.message.encode()).hexdigest()[:8]
            self.error_id = f"mbed_{int(self.timestamp)}_{msg_hash}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            'error_id': self.error_id,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp,
            'context': self.context.__dict__ if self.context else None,
            'stack_trace': self.stack_trace,
            'recovery_suggestions': self.recovery_suggestions
        }


class ErrorHandler:
    """Unified error handling and recovery system."""

    def __init__(self):
        self.error_history: deque = deque(maxlen=1000)
        self.error_callbacks: List[Callable[[MBEDError], None]] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.error_patterns: Dict[str, ErrorCategory] = self._initialize_error_patterns()
        self.max_history_size = 1000

    def _initialize_error_patterns(self) -> Dict[str, ErrorCategory]:
        """Initialize common error patterns for automatic categorization."""
        return {
            # File access patterns
            'permission denied': ErrorCategory.FILE_ACCESS,
            'file not found': ErrorCategory.FILE_ACCESS,
            'no such file': ErrorCategory.FILE_ACCESS,
            'access denied': ErrorCategory.FILE_ACCESS,
            'directory not found': ErrorCategory.FILE_ACCESS,

            # Parsing patterns
            'syntax error': ErrorCategory.PARSING,
            'parse error': ErrorCategory.PARSING,
            'invalid json': ErrorCategory.PARSING,
            'decode error': ErrorCategory.PARSING,
            'encoding error': ErrorCategory.PARSING,

            # Chunking patterns
            'chunk': ErrorCategory.CHUNKING,
            'boundary': ErrorCategory.CHUNKING,
            'tokenize': ErrorCategory.CHUNKING,

            # Embedding patterns
            'embedding': ErrorCategory.EMBEDDING,
            'model': ErrorCategory.EMBEDDING,
            'tensor': ErrorCategory.EMBEDDING,
            'cuda': ErrorCategory.EMBEDDING,

            # Storage patterns
            'database': ErrorCategory.STORAGE,
            'connection': ErrorCategory.STORAGE,
            'insert': ErrorCategory.STORAGE,
            'query': ErrorCategory.STORAGE,

            # Network patterns
            'timeout': ErrorCategory.NETWORK,
            'connection refused': ErrorCategory.NETWORK,
            'network': ErrorCategory.NETWORK,
            'http': ErrorCategory.NETWORK,

            # Memory patterns
            'out of memory': ErrorCategory.MEMORY,
            'memory': ErrorCategory.MEMORY,
            'allocation': ErrorCategory.MEMORY,

            # Configuration patterns
            'config': ErrorCategory.CONFIGURATION,
            'setting': ErrorCategory.CONFIGURATION,
            'environment': ErrorCategory.CONFIGURATION,

            # Validation patterns
            'validation': ErrorCategory.VALIDATION,
            'invalid': ErrorCategory.VALIDATION,
            'missing': ErrorCategory.VALIDATION,
        }

    def handle_error(
        self,
        error: Union[Exception, str],
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        context: Optional[ErrorContext] = None,
        auto_recover: bool = True
    ) -> MBEDError:
        """Handle an error with automatic categorization and optional recovery."""

        # Convert to MBEDError
        if isinstance(error, Exception):
            message = str(error)
            original_exception = error
            stack_trace = traceback.format_exc()
        else:
            message = error
            original_exception = None
            stack_trace = None

        # Auto-categorize if not provided
        if category is None:
            category = self._categorize_error(message)

        # Auto-determine severity if not provided
        if severity is None:
            severity = self._determine_severity(message, category, original_exception)

        # Add recovery suggestions
        recovery_suggestions = self._get_recovery_suggestions(category, message)

        # Create error object
        mbed_error = MBEDError(
            message=message,
            category=category,
            severity=severity,
            context=context,
            original_exception=original_exception,
            stack_trace=stack_trace,
            recovery_suggestions=recovery_suggestions
        )

        # Store in history
        self._add_to_history(mbed_error)

        # Log error
        self._log_error(mbed_error)

        # Notify callbacks
        self._notify_callbacks(mbed_error)

        # Attempt recovery if enabled
        if auto_recover and category in self.recovery_strategies:
            self._attempt_recovery(mbed_error)

        return mbed_error

    def _categorize_error(self, message: str) -> ErrorCategory:
        """Automatically categorize error based on message content."""
        message_lower = message.lower()

        for pattern, category in self.error_patterns.items():
            if pattern in message_lower:
                return category

        return ErrorCategory.UNKNOWN

    def _determine_severity(
        self, message: str, category: ErrorCategory, exception: Optional[Exception]
    ) -> ErrorSeverity:
        """Automatically determine error severity."""
        message_lower = message.lower()

        # Critical severity indicators
        critical_patterns = [
            'critical', 'fatal', 'corrupt', 'out of memory',
            'disk full', 'system error', 'segmentation fault'
        ]

        # High severity indicators
        high_patterns = [
            'failed', 'error', 'exception', 'crash',
            'timeout', 'connection refused', 'permission denied'
        ]

        # Medium severity indicators
        medium_patterns = [
            'warning', 'retry', 'skip', 'fallback'
        ]

        if any(pattern in message_lower for pattern in critical_patterns):
            return ErrorSeverity.CRITICAL
        elif any(pattern in message_lower for pattern in high_patterns):
            return ErrorSeverity.HIGH
        elif any(pattern in message_lower for pattern in medium_patterns):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _get_recovery_suggestions(self, category: ErrorCategory, message: str) -> List[str]:
        """Get recovery suggestions based on error category and message."""
        suggestions = []

        if category == ErrorCategory.FILE_ACCESS:
            suggestions.extend([
                "Check file permissions and ensure the file exists",
                "Verify the file path is correct",
                "Ensure sufficient disk space is available"
            ])
        elif category == ErrorCategory.PARSING:
            suggestions.extend([
                "Verify file format and encoding",
                "Check for file corruption",
                "Try alternative parser or encoding"
            ])
        elif category == ErrorCategory.CHUNKING:
            suggestions.extend([
                "Adjust chunk size parameters",
                "Try different chunking strategy",
                "Check text preprocessing settings"
            ])
        elif category == ErrorCategory.EMBEDDING:
            suggestions.extend([
                "Check model availability and configuration",
                "Verify GPU/hardware compatibility",
                "Try alternative embedding backend"
            ])
        elif category == ErrorCategory.STORAGE:
            suggestions.extend([
                "Check database connection and credentials",
                "Verify storage system availability",
                "Ensure sufficient storage space"
            ])
        elif category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check network connectivity",
                "Verify service endpoints and credentials",
                "Retry with exponential backoff"
            ])
        elif category == ErrorCategory.MEMORY:
            suggestions.extend([
                "Reduce batch size or chunk size",
                "Enable memory-efficient processing modes",
                "Close unused resources and clear caches"
            ])
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.extend([
                "Check configuration file syntax",
                "Verify all required settings are provided",
                "Reset to default configuration if needed"
            ])

        return suggestions

    def _add_to_history(self, error: MBEDError):
        """Add error to history with size limit."""
        self.error_history.append(error)

        # History size is automatically managed by deque maxlen

    def _log_error(self, error: MBEDError):
        """Log error with appropriate level."""
        log_message = f"[{error.error_id}] {error.message}"

        if error.context:
            context_info = f" | Component: {error.context.component}, Operation: {error.context.operation}"
            if error.context.file_path:
                context_info += f", File: {error.context.file_path}"
            log_message += context_info

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Log stack trace for exceptions
        if error.stack_trace and error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Stack trace for {error.error_id}:\n{error.stack_trace}")

    def _notify_callbacks(self, error: MBEDError):
        """Notify registered error callbacks."""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.warning(f"Error callback failed: {e}")

    def _attempt_recovery(self, error: MBEDError):
        """Attempt automatic recovery based on error category."""
        category = error.category

        if category in self.recovery_strategies:
            for strategy in self.recovery_strategies[category]:
                try:
                    recovery_result = strategy(error)
                    if recovery_result:
                        logger.info(f"Recovery successful for error {error.error_id}")
                        return True
                except Exception as e:
                    logger.warning(f"Recovery strategy failed: {e}")

        return False

    def add_error_callback(self, callback: Callable[[MBEDError], None]):
        """Add error notification callback."""
        self.error_callbacks.append(callback)

    def add_recovery_strategy(self, category: ErrorCategory, strategy: Callable[[MBEDError], bool]):
        """Add recovery strategy for specific error category."""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error history."""
        if not self.error_history:
            return {'total_errors': 0}

        # Count by category
        category_counts = {}
        severity_counts = {}

        for error in self.error_history:
            category = error.category.value
            severity = error.severity.value

            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Recent errors (last 10)
        recent_errors = [error.to_dict() for error in list(self.error_history)[-10:]]

        return {
            'total_errors': len(self.error_history),
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'recent_errors': recent_errors,
            'most_common_category': max(category_counts.items(), key=lambda x: x[1]) if category_counts else None,
            'critical_errors': severity_counts.get('critical', 0),
            'high_severity_errors': severity_counts.get('high', 0)
        }

    def export_errors(self, file_path: Path, format: str = 'json') -> Result[None, str]:
        """Export error history to file."""
        try:
            error_data = [error.to_dict() for error in self.error_history]

            if format == 'json':
                with open(file_path, 'w') as f:
                    json.dump(error_data, f, indent=2, default=str)
            else:
                return Result.Err(f"Unsupported export format: {format}")

            return Result.Ok(None)

        except Exception as e:
            return Result.Err(f"Failed to export errors: {str(e)}")

    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()
        logger.info("Error history cleared")

    def get_errors_by_category(self, category: ErrorCategory) -> List[MBEDError]:
        """Get all errors of specific category."""
        return [error for error in self.error_history if error.category == category]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[MBEDError]:
        """Get all errors of specific severity."""
        return [error for error in self.error_history if error.severity == severity]


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_error(
    error: Union[Exception, str],
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    context: Optional[ErrorContext] = None,
    auto_recover: bool = True
) -> MBEDError:
    """Convenience function for global error handling."""
    return global_error_handler.handle_error(error, category, severity, context, auto_recover)


def create_error_context(
    component: str,
    operation: str,
    file_path: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """Convenience function for creating error context."""
    return ErrorContext(
        component=component,
        operation=operation,
        file_path=file_path,
        additional_data=kwargs
    )


# Common recovery strategies
def retry_with_backoff(error: MBEDError) -> bool:
    """Generic retry strategy with exponential backoff."""
    import time
    import random

    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)

            # This would need to be customized for specific operations
            # For now, just return False to indicate no recovery
            return False

        except Exception:
            continue

    return False


def fallback_to_default(error: MBEDError) -> bool:
    """Fallback to default configuration or behavior."""
    # This would need specific implementation based on the error context
    return False


# Register common recovery strategies
global_error_handler.add_recovery_strategy(ErrorCategory.NETWORK, retry_with_backoff)
global_error_handler.add_recovery_strategy(ErrorCategory.CONFIGURATION, fallback_to_default)