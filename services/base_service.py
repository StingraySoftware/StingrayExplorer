"""
Base service class for StingrayExplorer service layer.

This module provides the base class that all services inherit from,
providing common functionality like result creation and error handling integration.
"""

from typing import Any, Dict, Optional
from utils.state_manager import StateManager
from utils.error_handler import ErrorHandler
from utils.performance_monitor import performance_monitor


class BaseService:
    """
    Base class for all services in the StingrayExplorer application.

    Provides:
    - Access to StateManager for data persistence
    - Access to ErrorHandler for consistent error handling
    - Standard result format for all service methods

    All services should inherit from this class and implement their
    domain-specific business logic.
    """

    def __init__(self, state_manager: StateManager):
        """
        Initialize the base service.

        Args:
            state_manager: The application state manager instance
        """
        self.state = state_manager
        self.error_handler = ErrorHandler
        self.performance_monitor = performance_monitor

    def create_result(
        self,
        success: bool,
        data: Any = None,
        message: str = "",
        error: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a standardized result dictionary.

        All service methods should return results in this format for consistency.

        Args:
            success: Whether the operation succeeded
            data: The result data (e.g., EventList, Lightcurve, DataFrame, etc.)
            message: User-friendly message describing the result
            error: Technical error message (if applicable)
            **kwargs: Additional fields to include in the result (e.g., metadata)

        Returns:
            Dictionary with keys: success, data, message, error, plus any kwargs

        Example:
            >>> return self.create_result(
            ...     success=True,
            ...     data=event_list,
            ...     message="EventList loaded successfully",
            ...     metadata={'method': 'lazy'}
            ... )
        """
        result = {
            "success": success,
            "data": data,
            "message": message,
            "error": error
        }
        # Add any additional fields
        result.update(kwargs)
        return result

    def handle_error(
        self,
        exception: Exception,
        context: str,
        **context_data
    ) -> Dict[str, Any]:
        """
        Handle an exception and return a standardized error result.

        Uses the centralized ErrorHandler to log the error and generate
        user-friendly and technical messages.

        Args:
            exception: The exception that occurred
            context: Description of the operation that failed
            **context_data: Additional context data to log (e.g., parameters)

        Returns:
            Error result dictionary with success=False

        Example:
            >>> try:
            ...     event_list = EventList.read(file_path, fmt=fmt)
            ... except Exception as e:
            ...     return self.handle_error(
            ...         e,
            ...         "Loading event list",
            ...         file_path=file_path,
            ...         fmt=fmt
            ...     )
        """
        user_msg, tech_msg = self.error_handler.handle_error(
            exception,
            context=context,
            **context_data
        )

        return self.create_result(
            success=False,
            data=None,
            message=user_msg,
            error=tech_msg
        )
