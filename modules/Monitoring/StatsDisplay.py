"""
Statistics and Monitoring Display Module

This module provides a visual dashboard for viewing application statistics,
performance metrics, and system information.
"""

import panel as pn
import param
from utils.app_context import AppContext
from utils.performance_monitor import performance_monitor


class StatsDisplay(param.Parameterized):
    """
    Reactive statistics dashboard that displays real-time application metrics.

    Uses Panel's param.depends to automatically update when state changes.
    """

    # Refresh trigger
    refresh_trigger = param.Integer(default=0)

    def __init__(self, context: AppContext, **params):
        super().__init__(**params)
        self.context = context

    @param.depends('refresh_trigger')
    def _state_stats_panel(self):
        """Display state statistics (reactive to refresh trigger)."""
        stats = self.context.state.get_stats()

        html_content = f"""
        <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">State Statistics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Event Lists:</td>
                    <td style="padding: 8px;">{self.context.state.event_data_count}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Light Curves:</td>
                    <td style="padding: 8px;">{self.context.state.light_curve_count}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Timeseries:</td>
                    <td style="padding: 8px;">{self.context.state.timeseries_count}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Total Additions:</td>
                    <td style="padding: 8px;">{stats.get('total_additions', 0)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Total Removals:</td>
                    <td style="padding: 8px;">{stats.get('total_removals', 0)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Evictions (LRU):</td>
                    <td style="padding: 8px;">{stats.get('total_evictions', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Last Operation:</td>
                    <td style="padding: 8px; font-style: italic; color: #6c757d;">
                        {self.context.state.last_operation or 'None'}
                    </td>
                </tr>
            </table>
        </div>
        """
        return pn.pane.HTML(html_content, sizing_mode='stretch_width')

    @param.depends('refresh_trigger')
    def _memory_stats_panel(self):
        """Display memory statistics (reactive to refresh trigger)."""
        mem_info = self.context.state.get_system_memory_info()

        if not mem_info:
            return pn.pane.Markdown("*Memory information unavailable*")

        # Convert MB to GB
        total_gb = mem_info.get('total_mb', 0) / 1024
        available_gb = mem_info.get('available_mb', 0) / 1024
        limit_gb = mem_info.get('allocated_limit_mb', 0) / 1024
        app_usage_gb = self.context.state.memory_usage_mb / 1024

        html_content = f"""
        <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Memory Usage</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Total System RAM:</td>
                    <td style="padding: 8px;">{total_gb:.2f} GB</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Available:</td>
                    <td style="padding: 8px;">{available_gb:.2f} GB</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">App Limit (80%):</td>
                    <td style="padding: 8px;">{limit_gb:.2f} GB</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Current App Usage:</td>
                    <td style="padding: 8px;">{app_usage_gb:.3f} GB</td>
                </tr>
            </table>
        </div>
        """
        return pn.pane.HTML(html_content, sizing_mode='stretch_width')

    @param.depends('refresh_trigger')
    def _performance_stats_panel(self):
        """Display performance statistics (reactive to refresh trigger)."""
        summary = performance_monitor.get_summary()

        html_content = f"""
        <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Performance Metrics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Total Operations:</td>
                    <td style="padding: 8px;">{summary.get('total_operations', 0)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Unique Operations:</td>
                    <td style="padding: 8px;">{summary.get('unique_operations', 0)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Avg Duration:</td>
                    <td style="padding: 8px;">{summary.get('avg_duration_ms', 0):.2f} ms</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Success Rate:</td>
                    <td style="padding: 8px;">{summary.get('success_rate', 0):.1f}%</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; font-weight: bold;">Most Frequent:</td>
                    <td style="padding: 8px; font-style: italic;">{summary.get('most_frequent') or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Slowest Operation:</td>
                    <td style="padding: 8px; font-style: italic; color: #e74c3c;">
                        {summary.get('slowest') or 'N/A'}
                    </td>
                </tr>
            </table>
        </div>
        """
        return pn.pane.HTML(html_content, sizing_mode='stretch_width')

    @param.depends('refresh_trigger')
    def _recent_operations_panel(self):
        """Display recent operations list (reactive to refresh trigger)."""
        recent = performance_monitor.get_recent_operations(limit=10)

        if not recent:
            return pn.pane.Markdown("*No recent operations*")

        rows = ""
        for op in reversed(recent):  # Most recent first
            status_icon = "[OK]" if op.success else "[X]"
            status_color = "#28a745" if op.success else "#dc3545"
            time_str = op.start_time.strftime("%H:%M:%S")

            rows += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 6px; font-size: 20px;">{status_icon}</td>
                <td style="padding: 6px;">{time_str}</td>
                <td style="padding: 6px;">{op.operation_name}</td>
                <td style="padding: 6px; text-align: right;">{op.duration_ms:.2f} ms</td>
            </tr>
            """

        html_content = f"""
        <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Recent Operations</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #e9ecef; border-bottom: 2px solid #dee2e6;">
                        <th style="padding: 8px; text-align: left;">Status</th>
                        <th style="padding: 8px; text-align: left;">Time</th>
                        <th style="padding: 8px; text-align: left;">Operation</th>
                        <th style="padding: 8px; text-align: right;">Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
        return pn.pane.HTML(html_content, sizing_mode='stretch_width')

    def view(self):
        """Create the complete stats dashboard view."""
        # Refresh button
        refresh_button = pn.widgets.Button(
            name="Refresh Stats",
            button_type="primary",
            width=200
        )

        def on_refresh(event):
            self.refresh_trigger += 1

        refresh_button.on_click(on_refresh)

        # Create layout (no duplicate header - header is set in sidebar.py)
        dashboard = pn.Column(
            pn.Row(refresh_button, align='center'),
            pn.layout.Divider(),
            self._state_stats_panel,
            self._memory_stats_panel,
            self._performance_stats_panel,
            self._recent_operations_panel,
            sizing_mode='stretch_width'
        )

        return dashboard


def create_stats_dashboard(context: AppContext):
    """
    Factory function to create the stats dashboard.

    Args:
        context: Application context

    Returns:
        Panel dashboard component
    """
    stats_display = StatsDisplay(context)
    return stats_display.view()
