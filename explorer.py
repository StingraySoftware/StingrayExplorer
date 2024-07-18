import panel as pn
from utils.strings import HOME_HEADING_STRING, WELCOME_MESSAGE_STRING, FOOTER_STRING
from modules.Home.HomeContent import create_home_bokeh_plots_container, create_home_footer, create_home_header, create_home_help_box, create_home_main_area, create_home_output_box, create_home_warning_box
from utils.sidebar import create_sidebar


# Initialize panel extension
pn.extension()

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

# Create the plots container
bokeh_plots_container = create_home_bokeh_plots_container()

# Create the help box
help_box = create_home_help_box()

# Create the footer
footer = create_home_footer()

sidebar = create_sidebar(main_area, header, footer, output_box, warning_box, help_box)


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
    theme_toggle=True,
    # background_color="#FFFFFF", # The toggle button choses it according to the theme
    neutral_color="#D3D3D3",
    accent_base_color="#c4e1c5",
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

layout.main[0:10, 0:12] = header
layout.main[10:45, 0:8] = main_area
layout.main[10:26, 8:12] = output_box
layout.main[26:45, 8:12] = warning_box
layout.main[45:85, 0:12] = bokeh_plots_container
layout.main[85:120, 0:12] = help_box
layout.main[120:150, 0:12] = footer

# Serve the layout
layout.servable()
