"""
Centralized error handling for StingrayExplorer.

This module provides a unified approach to handling exceptions across the application,
ensuring consistent error messages, proper logging, and better debugging capabilities.

Design Philosophy (Data Engineering Approach):
- Errors should be easily traceable with full stack traces
- Avoid hiding errors with excessive try/except logic
- Use centralized logging with rich metadata
- Support Panel's built-in logging (pn.state.log)
"""

import logging
import traceback
from typing import Dict, Type, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime


class ErrorHandler:
    """
    Centralized error handler for the StingrayExplorer application.

    Provides:
    - Consistent error message formatting
    - Automatic logging with stack traces
    - Exception type mapping to user-friendly messages
    - Context tracking for better debugging
    - Integration with Panel's logging system
    """

    # Exception to user-friendly message mapping
    ERROR_MESSAGES: Dict[Type[Exception], str] = {
        FileNotFoundError: "The specified file could not be found. Please check the file path.",
        PermissionError: "Permission denied. Please check file permissions.",
        ValueError: "Invalid input provided. Please check your parameters.",
        KeyError: "Required data not found. The file may be corrupted or in an unexpected format.",
        IndexError: "Index out of range. Please check your data selection.",
        TypeError: "Invalid data type encountered. Please check your input.",
        OSError: "System error occurred. Please check file system access.",
        MemoryError: "Insufficient memory. Try processing smaller datasets.",
        AssertionError: "Data validation failed. Please check your input parameters.",
    }

    # Stingray-specific error patterns
    STINGRAY_ERROR_PATTERNS = {
        "No GTIs are equal to or longer than segment_size":
            "No Good Time Intervals (GTIs) are long enough for the specified segment size. Please reduce the segment size or check your GTIs.",
        "requested segment size":
            "Invalid segment size. The dt value may be too large or segment size too small for the available data.",
        "cannot convert":
            "Data conversion failed. The file format may be incompatible or corrupted.",
        "not enough values":
            "Insufficient data points. The dataset may be too small or improperly formatted.",
        "ConcurrentAppendException":
            "Concurrent data access detected. This is usually temporary - please try again.",
    }

    @classmethod
    def setup_logging(
        cls,
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        app_name: str = "stingray_explorer"
    ):
        """
        Configure logging for the application.

        Args:
            log_dir: Directory to store log files
            log_level: Logging level (default: INFO)
            app_name: Application name for log files
        """
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_path / f"{app_name}_{timestamp}.log"

        # Configure logging format with rich metadata
        log_format = (
            "%(asctime)s [%(levelname)s] %(name)s - "
            "%(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
        )

        # Setup file handler with detailed logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Setup console handler for warnings and errors only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

        # Get root logger
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logging.info(f"=== StingrayExplorer Logging Initialized ===")
        logging.info(f"Log file: {log_file}")
        logging.info(f"Log level: {logging.getLevelName(log_level)}")

    @classmethod
    def handle_error(
        cls,
        error: Exception,
        context: str,
        user_message: Optional[str] = None,
        log_level: int = logging.ERROR,
        log_to_panel: bool = True,
        **context_data: Any
    ) -> Tuple[str, str]:
        """
        Handle an exception with logging and user-friendly message generation.

        This method logs the full stack trace for debugging while providing
        user-friendly messages. Following data engineering best practices,
        we preserve the full stack trace rather than hiding it.

        Args:
            error: The exception that was raised
            context: String describing where the error occurred (e.g., "Loading event list")
            user_message: Optional custom user-facing message
            log_level: Logging level for this error (default: ERROR)
            log_to_panel: Whether to also log to Panel's state.log (default: True)
            **context_data: Additional context data to log (e.g., file_path="...", dt=1.0)

        Returns:
            Tuple of (user_message, technical_message)
        """
        # Get the exception type
        error_type = type(error)
        error_str = str(error)

        # Build context info string with metadata
        context_info = f"Context: {context}"
        if context_data:
            context_details = ", ".join(f"{k}={v}" for k, v in context_data.items())
            context_info += f" | Parameters: {context_details}"

        # Get full stack trace
        stack_trace = traceback.format_exc()

        # Log the error with full details
        logger = logging.getLogger(__name__)
        log_message = (
            f"\n{'='*80}\n"
            f"{context_info}\n"
            f"Exception Type: {error_type.__name__}\n"
            f"Exception Message: {error_str}\n"
            f"{'='*80}\n"
            f"{stack_trace}"
            f"{'='*80}"
        )
        logger.log(log_level, log_message)

        # Also log to Panel's logging system if requested
        if log_to_panel:
            try:
                import panel as pn
                if pn.state.curdoc:
                    pn.state.log(f"{context}: {error_type.__name__} - {error_str}")
            except (ImportError, AttributeError):
                pass  # Panel not available or not in a session

        # Generate user-friendly message
        if user_message:
            final_message = user_message
        else:
            # Check for Stingray-specific error patterns first
            final_message = None
            for pattern, message in cls.STINGRAY_ERROR_PATTERNS.items():
                if pattern in error_str:
                    final_message = message
                    break

            # If no pattern match, use exception type mapping
            if not final_message:
                final_message = cls.ERROR_MESSAGES.get(
                    error_type,
                    f"An unexpected error occurred: {error_str}"
                )

        # Create technical message for advanced users/debugging
        technical_message = f"{error_type.__name__}: {error_str}"

        return final_message, technical_message

    @classmethod
    def handle_validation_error(
        cls,
        field_name: str,
        value: Any,
        expected: str,
        context: str = "Input validation"
    ) -> Tuple[str, str]:
        """
        Handle validation errors with specific field information.

        Args:
            field_name: Name of the field that failed validation
            value: The invalid value
            expected: Description of expected value
            context: Context where validation occurred

        Returns:
            Tuple of (user_message, technical_message)
        """
        user_message = f"Invalid {field_name}: Expected {expected}, got '{value}'"
        technical_message = f"Validation failed for {field_name} in {context}"

        logger = logging.getLogger(__name__)
        logger.warning(
            f"{context}: {technical_message}\n"
            f"Field: {field_name}\n"
            f"Value: {value}\n"
            f"Expected: {expected}"
        )

        return user_message, technical_message

    @classmethod
    def handle_warning(
        cls,
        message: str,
        context: str,
        log_to_panel: bool = True,
        **context_data: Any
    ) -> str:
        """
        Handle warnings with logging.

        Args:
            message: Warning message
            context: Context where warning occurred
            log_to_panel: Whether to also log to Panel's state.log
            **context_data: Additional context data

        Returns:
            User-facing warning message
        """
        logger = logging.getLogger(__name__)

        context_info = f"Context: {context}"
        if context_data:
            context_details = ", ".join(f"{k}={v}" for k, v in context_data.items())
            context_info += f" | Parameters: {context_details}"

        logger.warning(f"{context_info}\n{message}")

        # Also log to Panel if requested
        if log_to_panel:
            try:
                import panel as pn
                if pn.state.curdoc:
                    pn.state.log(f"WARNING - {context}: {message}", level='warning')
            except (ImportError, AttributeError):
                pass

        return f"Warning: {message}"

    @classmethod
    def log_info(
        cls,
        message: str,
        context: str,
        log_to_panel: bool = False,
        **context_data: Any
    ):
        """
        Log informational messages.

        Args:
            message: Info message
            context: Context where this occurred
            log_to_panel: Whether to also log to Panel's state.log
            **context_data: Additional context data
        """
        logger = logging.getLogger(__name__)

        context_info = f"{context}"
        if context_data:
            context_details = ", ".join(f"{k}={v}" for k, v in context_data.items())
            context_info += f" | {context_details}"

        logger.info(f"{context_info}: {message}")

        # Also log to Panel if requested
        if log_to_panel:
            try:
                import panel as pn
                if pn.state.curdoc:
                    pn.state.log(f"{context}: {message}", level='info')
            except (ImportError, AttributeError):
                pass


# Initialize logging when module is imported
ErrorHandler.setup_logging()
