"""
Stingray Explorer Main Application File

This module serves as the entry point for the Stingray Explorer dashboard application.
It handles the initialization of the Panel/Holoviews environment and sets up the 
dashboard layout and components.

The dashboard provides an interactive interface for analyzing X-ray astronomy data
using the Stingray library, with various visualization and analysis tools.

Key Components:
- Header: Main navigation and branding
- Sidebar: Control panel for data loading and analysis
- Main Area: Primary workspace for data visualization
- Plots Area: Container for generated plots and charts
- Resource Monitor: System resource usage display
- Help/Info Sections: Documentation and support resources
"""

import panel as pn
import holoviews as hv
from modules.Home.HomeContent import (
    create_home_header,
    create_home_main_area,
    create_home_output_box,
    create_home_warning_box,
    create_home_help_area,
    create_home_footer,
    create_home_plots_area_initial,
    create_home_resource_monitor,
)

from utils.sidebar import create_sidebar


# Initialize Panel and Holoviews extensions with required features
pn.extension('floatpanel', 'mathjax')
pn.extension('filedropper')
pn.extension('echarts')
pn.extension(nthreads=0)
hv.extension('bokeh')

# Create a boolean status indicator to show system activity
busy_indicator = pn.indicators.BooleanStatus(
    value=True, color="warning", width=30, height=30
)

# Create the main dashboard header with branding and navigation
header = create_home_header()

# Create resource monitor to display system usage statistics
resource_monitor = create_home_resource_monitor()

# Create the main workspace area for data visualization and analysis
main_area = create_home_main_area()

# Create the output console for displaying analysis results and messages
output_box = create_home_output_box()

# Create the warning box for displaying important alerts and notifications
warning_box = create_home_warning_box()

# Create the help box containing documentation and support resources
help_box = create_home_help_area()

# Create the footer with copyright and additional information
footer = create_home_footer()

# Create the plots area container for visualization outputs
plots_area = create_home_plots_area_initial()


# Create containers for each section to enable dynamic layout management
header_container = pn.Column(header)
resource_monitor_container = pn.Column(resource_monitor)
main_area_container = pn.Column(main_area)
output_box_container = pn.Column(output_box)
warning_box_container = pn.Column(warning_box)
plots_container = pn.FlexBox(plots_area, flex_direction='row', align_content='space-evenly', align_items="center", justify_content="center", flex_wrap="wrap")
help_box_container = pn.Column(help_box)
footer_container = pn.Column(footer)
float_panel_container = pn.Column(pn.pane.Markdown("This is not a bug that this container is scrolling, it's a container to hold Floating Plots. You can ignore it completely."))

# Floating plot container for additional visualization options
# floating_plot_demo = create_floating_plot_demo(floating_panel_container)

# Create the sidebar with navigation and control elements
sidebar = create_sidebar(
    main_area=main_area_container,
    resource_usage=resource_monitor_container,
    header=header_container,
    footer=footer_container,
    output_box=output_box_container,
    warning_box=warning_box_container,
    help_box=help_box_container,
    plots_container=plots_container,
    float_panel_container=float_panel_container,
)


"""
Create the main dashboard layout using Panel's FastGridTemplate

The layout organizes all components into a responsive grid system with:
- Header at the top
- Sidebar on the left
- Main content area in the center
- Plots and output sections below
- Footer at the bottom

The grid is fully responsive and adapts to different screen sizes.
"""
layout = pn.template.FastGridTemplate(
    # Basic Panel layout components
    main=[],
    header="Next-Generation Spectral Timing Made Easy",
    sidebar=[sidebar],
    modal=True,
    # Parameters for the FastGridTemplate
    site="",  # Not shown as already doing in title
    site_url="StingrayExplorer",
    logo="./assets/images/stingray_explorer.png",
    title="Stingray Explorer",
    favicon="./assets/images/stingray_explorer.png",
    # sidebar_footer="Sidebar Footer",
    # config= (TemplateConfig): Contains configuration options similar to pn.config but applied to the current Template only. (Currently only css_files is supported) But css_files are now deprecated.
    busy_indicator=busy_indicator,
    # For configuring the grid
    cols={"lg": 12, "md": 12, "sm": 12, "xs": 4, "xxs": 2},
    breakpoints={"lg": 1200, "md": 996, "sm": 768, "xs": 480, "xxs": 0},
    row_height=10,
    dimensions={"minW": 0, "maxW": float("inf"), "minH": 0, "maxH": float("inf")},
    prevent_collision=False,
    save_layout=True,
    # Styling parameter
    theme="default",
    theme_toggle=False,
    background_color="#FFFFFF",
    neutral_color="#D3D3D3",
    accent_base_color="#5ead61",
    header_background="#000000",
    header_color="#c4e1c5",
    header_neutral_color="#D3D3D3",
    header_accent_base_color="#c4e1c5",
    corner_radius=7,
    # font="",
    # font_url="",
    shadow=True,
    main_layout="card",
    # Layout parameters
    collapsed_sidebar=False,
    sidebar_width=250,
    main_max_width="100%",
    # Meta data
    meta_description="Stingray Explorer Dashboard",
    meta_keywords="Stingray, Explorer, Dashboard, Astronomy, Stingray Explorer, X-ray Astronomy, X-ray Data Analysis",
    meta_author="Kartik Mandar",
    meta_refresh="",
    meta_viewport="width=device-width, initial-scale=1",
    base_url="/",
    base_target="_self",
)

layout.main[0:10, 0:6] = header_container
layout.main[0:10, 6:12] = resource_monitor_container
layout.main[10:55, 0:8] = main_area_container
layout.main[10:33, 8:12] = output_box_container
layout.main[33:55, 8:12] = warning_box_container
layout.main[55:100, 0:12] = plots_container
layout.main[100:140, 0:12] = help_box_container
layout.main[140:170, 0:12] = footer_container
layout.main[170:170, 0:12] = float_panel_container


# Make the layout available for serving
layout.servable()
