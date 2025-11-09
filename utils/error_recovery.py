"""
Error Recovery UI Components

This module provides user-facing error recovery options and UI components
for handling errors gracefully with actionable recovery paths.
"""

import panel as pn
from typing import Callable, Optional, Dict, Any


class ErrorRecoveryPanel:
    """
    Creates user-friendly error panels with recovery options.

    Provides standardized error UI with:
    - Clear error messages
    - Suggested actions
    - Retry buttons
    - Clear/reset options
    - Help links
    """

    @staticmethod
    def create_error_panel(
        error_message: str,
        error_type: str = "error",
        retry_callback: Optional[Callable] = None,
        clear_callback: Optional[Callable] = None,
        help_text: Optional[str] = None,
        technical_details: Optional[str] = None,
        show_technical: bool = False
    ) -> pn.Column:
        """
        Create a comprehensive error panel with recovery options.

        Args:
            error_message: User-friendly error message
            error_type: Type of error ("error", "warning", "info")
            retry_callback: Function to call when user clicks "Retry"
            clear_callback: Function to call when user clicks "Clear and Start Over"
            help_text: Additional help text or suggestions
            technical_details: Technical error details (for debugging)
            show_technical: Whether to show technical details by default

        Returns:
            Panel Column with error display and recovery options

        Example:
            >>> def retry_load():
            ...     # Retry loading the file
            ...     load_file(file_path)
            >>>
            >>> panel = ErrorRecoveryPanel.create_error_panel(
            ...     error_message="Failed to load event list",
            ...     retry_callback=retry_load,
            ...     help_text="Check that the file is in OGIP format"
            ... )
        """
        # Color scheme based on error type
        colors = {
            "error": {"bg": "#fee", "border": "#dc3545", "icon": "[X]"},
            "warning": {"bg": "#fff3cd", "border": "#ffc107", "icon": "[!]"},
            "info": {"bg": "#d1ecf1", "border": "#17a2b8", "icon": "[i]"}
        }

        color_scheme = colors.get(error_type, colors["error"])

        # Error icon and message
        error_display = pn.pane.HTML(
            f"""
            <div style="
                background: {color_scheme['bg']};
                border: 2px solid {color_scheme['border']};
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
            ">
                <div style="display: flex; align-items: start; gap: 10px;">
                    <div style="font-size: 24px;">{color_scheme['icon']}</div>
                    <div style="flex: 1;">
                        <h4 style="margin: 0 0 10px 0; color: #333;">
                            {error_type.title()}
                        </h4>
                        <p style="margin: 0; color: #555; line-height: 1.5;">
                            {error_message}
                        </p>
                    </div>
                </div>
            </div>
            """,
            sizing_mode='stretch_width'
        )

        components = [error_display]

        # Help text section
        if help_text:
            help_panel = pn.pane.HTML(
                f"""
                <div style="
                    background: #f8f9fa;
                    border-left: 4px solid #28a745;
                    padding: 12px;
                    margin: 10px 0;
                    border-radius: 4px;
                ">
                    <strong>Suggestion:</strong> {help_text}
                </div>
                """,
                sizing_mode='stretch_width'
            )
            components.append(help_panel)

        # Action buttons
        buttons = []

        if retry_callback:
            retry_button = pn.widgets.Button(
                name="Retry",
                button_type="primary",
                width=150
            )
            retry_button.on_click(lambda e: retry_callback())
            buttons.append(retry_button)

        if clear_callback:
            clear_button = pn.widgets.Button(
                name="Clear and Start Over",
                button_type="warning",
                width=180
            )
            clear_button.on_click(lambda e: clear_callback())
            buttons.append(clear_button)

        if buttons:
            button_row = pn.Row(*buttons, align='center')
            components.append(button_row)

        # Technical details (collapsible)
        if technical_details:
            details_toggle = pn.widgets.Toggle(
                name="Show Technical Details",
                value=show_technical,
                button_type="light",
                width=200
            )

            # Replace newlines with HTML breaks outside the f-string
            formatted_details = technical_details.replace('\n', '<br>')

            details_panel = pn.pane.HTML(
                f"""
                <div style="
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 12px;
                    overflow-x: auto;
                ">
                    <strong>Technical Details:</strong><br><br>
                    {formatted_details}
                </div>
                """,
                sizing_mode='stretch_width',
                visible=show_technical
            )

            def toggle_details(event):
                details_panel.visible = event.new

            details_toggle.param.watch(toggle_details, 'value')

            components.extend([details_toggle, details_panel])

        return pn.Column(*components, sizing_mode='stretch_width')

    @staticmethod
    def create_validation_error(
        field_name: str,
        invalid_value: Any,
        expected: str,
        retry_callback: Optional[Callable] = None
    ) -> pn.Column:
        """
        Create a validation error panel.

        Args:
            field_name: Name of the field that failed validation
            invalid_value: The invalid value provided
            expected: Description of what was expected
            retry_callback: Optional retry function

        Returns:
            Panel Column with validation error display
        """
        error_msg = f"Invalid value for **{field_name}**"
        help_text = f"Expected: {expected}<br>Received: '{invalid_value}'"

        return ErrorRecoveryPanel.create_error_panel(
            error_message=error_msg,
            error_type="warning",
            retry_callback=retry_callback,
            help_text=help_text
        )

    @staticmethod
    def create_file_not_found_error(
        file_path: str,
        retry_callback: Optional[Callable] = None,
        clear_callback: Optional[Callable] = None
    ) -> pn.Column:
        """
        Create a file not found error panel.

        Args:
            file_path: Path to the file that wasn't found
            retry_callback: Function to retry loading
            clear_callback: Function to clear and start over

        Returns:
            Panel Column with file not found error
        """
        error_msg = f"File not found: **{file_path}**"
        help_text = (
            "Please check that:<br>"
            "• The file path is correct<br>"
            "• The file exists in the specified location<br>"
            "• You have permission to read the file"
        )

        return ErrorRecoveryPanel.create_error_panel(
            error_message=error_msg,
            error_type="error",
            retry_callback=retry_callback,
            clear_callback=clear_callback,
            help_text=help_text
        )

    @staticmethod
    def create_memory_error(
        clear_callback: Optional[Callable] = None
    ) -> pn.Column:
        """
        Create a memory error panel.

        Args:
            clear_callback: Function to clear data and free memory

        Returns:
            Panel Column with memory error display
        """
        error_msg = "Memory limit exceeded!"
        help_text = (
            "The application has reached its memory limit.<br>"
            "Try:<br>"
            "• Clearing some loaded data<br>"
            "• Processing smaller datasets<br>"
            "• Closing other applications to free system memory"
        )

        return ErrorRecoveryPanel.create_error_panel(
            error_message=error_msg,
            error_type="warning",
            clear_callback=clear_callback,
            help_text=help_text
        )

    @staticmethod
    def create_success_panel(
        success_message: str,
        details: Optional[str] = None
    ) -> pn.Column:
        """
        Create a success notification panel.

        Args:
            success_message: Success message to display
            details: Optional additional details

        Returns:
            Panel Column with success display
        """
        html_content = f"""
        <div style="
            background: #d4edda;
            border: 2px solid #28a745;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        ">
            <div style="display: flex; align-items: start; gap: 10px;">
                <div style="font-size: 24px;">[OK]</div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 10px 0; color: #155724;">
                        Success!
                    </h4>
                    <p style="margin: 0; color: #155724; line-height: 1.5;">
                        {success_message}
                    </p>
                    {f'<p style="margin: 10px 0 0 0; color: #155724; font-size: 14px;">{details}</p>' if details else ''}
                </div>
            </div>
        </div>
        """

        return pn.Column(
            pn.pane.HTML(html_content, sizing_mode='stretch_width'),
            sizing_mode='stretch_width'
        )


# Convenience functions for common error scenarios

def show_file_error(
    context,
    container_name: str,
    file_path: str,
    retry_func: Optional[Callable] = None
):
    """
    Display a file not found error in a container.

    Args:
        context: Application context
        container_name: Name of container to update
        file_path: Path to the missing file
        retry_func: Optional retry function
    """
    def clear_error():
        context.update_container(container_name,
            pn.pane.Markdown("*Ready to load data*"))

    error_panel = ErrorRecoveryPanel.create_file_not_found_error(
        file_path=file_path,
        retry_callback=retry_func,
        clear_callback=clear_error
    )

    context.update_container(container_name, error_panel)


def show_validation_error(
    context,
    container_name: str,
    field_name: str,
    value: Any,
    expected: str,
    retry_func: Optional[Callable] = None
):
    """
    Display a validation error in a container.

    Args:
        context: Application context
        container_name: Name of container to update
        field_name: Name of the field
        value: Invalid value
        expected: Expected value description
        retry_func: Optional retry function
    """
    error_panel = ErrorRecoveryPanel.create_validation_error(
        field_name=field_name,
        invalid_value=value,
        expected=expected,
        retry_callback=retry_func
    )

    context.update_container(container_name, error_panel)


def show_success(
    context,
    container_name: str,
    message: str,
    details: Optional[str] = None
):
    """
    Display a success message in a container.

    Args:
        context: Application context
        container_name: Name of container to update
        message: Success message
        details: Optional details
    """
    success_panel = ErrorRecoveryPanel.create_success_panel(
        success_message=message,
        details=details
    )

    context.update_container(container_name, success_panel)
