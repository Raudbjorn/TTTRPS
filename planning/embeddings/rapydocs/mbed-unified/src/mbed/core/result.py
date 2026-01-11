"""
Result type for error-as-values pattern
"""

from typing import TypeVar, Generic, Union, Callable, Optional
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E')
U = TypeVar('U')
F = TypeVar('F')


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """Result type that encapsulates success or error values."""

    _value: Optional[T] = None
    _error: Optional[E] = None
    _is_ok: bool = False

    def __init__(self, value: Optional[T] = None, error: Optional[E] = None, is_ok: bool = False):
        object.__setattr__(self, '_value', value)
        object.__setattr__(self, '_error', error)
        object.__setattr__(self, '_is_ok', is_ok)

    @classmethod
    def Ok(cls, value: T) -> 'Result[T, E]':
        """Create a successful result."""
        return cls(value=value, is_ok=True)

    @classmethod
    def Err(cls, error: E) -> 'Result[T, E]':
        """Create an error result."""
        return cls(error=error, is_ok=False)

    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self._is_ok

    def is_err(self) -> bool:
        """Check if result is an error."""
        return not self._is_ok

    def unwrap(self) -> T:
        """Get the success value or raise exception."""
        if not self._is_ok:
            raise RuntimeError(f"Called unwrap() on Error result: {self._error}")
        return self._value

    def unwrap_err(self) -> E:
        """Get the error value or raise exception."""
        if self._is_ok:
            raise RuntimeError("Called unwrap_err() on Ok result")
        return self._error

    def unwrap_or(self, default: T) -> T:
        """Get the success value or return default."""
        return self._value if self._is_ok else default

    def map(self, func: Callable[[T], 'U']) -> 'Result[U, E]':
        """Transform the success value if Ok."""
        if self._is_ok:
            try:
                return Result.Ok(func(self._value))
            except Exception as e:
                return Result.Err(e)
        return Result.Err(self._error)

    def map_err(self, func: Callable[[E], 'F']) -> 'Result[T, F]':
        """Transform the error value if Err."""
        if self._is_ok:
            return Result.Ok(self._value)
        return Result.Err(func(self._error))

    def and_then(self, func: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        """Chain operations that may fail."""
        if self._is_ok:
            try:
                return func(self._value)
            except Exception as e:
                return Result.Err(e)
        return Result.Err(self._error)

    def __repr__(self) -> str:
        if self._is_ok:
            return f"Result.Ok({self._value})"
        else:
            return f"Result.Err({self._error})"