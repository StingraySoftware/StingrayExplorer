import panel as pn
from modules.Home.HomeContent import (
    create_home_header,
    create_home_main_area,
    create_home_output_box,
    create_home_warning_box,
    create_home_help_area,
    create_home_footer,
    create_home_plots_area,
)
from utils.sidebar import create_sidebar


# Initialize panel extension
pn.extension('floatpanel')

# Create a boolean status indicator
busy_indicator = pn.indicators.BooleanStatus(
    value=True, color="warning", width=30, height=30
)

# Create the header
header = create_home_header()

# Create the main area
main_area = create_home_main_area()

# Create the output box
output_box = create_home_output_box()

# Create the warning box
warning_box = create_home_warning_box()

# Create the help box
help_box = create_home_help_area()

# Create the footer
footer = create_home_footer()

# Plots Area 
plots_container = create_home_plots_area()


# Containers for changing the layouts dynamically
header_container = pn.Column(header)
main_area_container = pn.Column(main_area)
output_box_container = pn.Column(output_box)
warning_box_container = pn.Column(warning_box)
plots_container = pn.FlexBox(plots_container, flex_direction='row', align_content='space-evenly', align_items="center", justify_content="center", flex_wrap="wrap")
help_box_container = pn.Column(help_box)
footer_container = pn.Column(footer)
floating_panel_container = pn.Column(pn.pane.Markdown("This is not a bug that this container is scrolling, it's a container to hold Floating Plots. You can ignore it completely."))

sidebar = create_sidebar(
    main_area=main_area_container,
    header=header_container,
    footer=footer_container,
    output_box=output_box_container,
    warning_box=warning_box_container,
    help_box=help_box_container,
    plots_area=plots_container,
    floating_panel=floating_panel_container
)


# Create a FastGridTemplate layout
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

layout.main[0:10, 0:12] = header_container
layout.main[10:55, 0:8] = main_area_container
layout.main[10:33, 8:12] = output_box_container
layout.main[33:55, 8:12] = warning_box_container
layout.main[55:100, 0:12] = plots_container
layout.main[100:140, 0:12] = help_box_container
layout.main[140:170, 0:12] = footer_container
layout.main[170:170, 0:12] = floating_panel_container


# Serve the layout
layout.servable()
