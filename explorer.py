import panel as pn
from utils.strings import HOME_HEADING_STRING, WELCOME_MESSAGE_STRING, FOOTER_STRING


# Initialize panel extension
pn.extension()

# Create a boolean status indicator
busy_indicator = pn.indicators.BooleanStatus(
    value=True, color="warning", width=30, height=30
)

# Create header
home_heading = pn.pane.HTML(
    HOME_HEADING_STRING,
    stylesheets=["../assets/stylesheets/explorer.css"],
    css_classes=["home-heading"],
)

# Create a welcome message
welcome_message = pn.pane.HTML(
    WELCOME_MESSAGE_STRING,
    stylesheets=["../assets/stylesheets/explorer.css"],
)

# Create main content layout
main = pn.Column(home_heading, welcome_message, height=800)

# Create a sidebar
sidebar = pn.pane.Markdown("Sidebar")

# Create a footer
footer = pn.pane.Markdown(FOOTER_STRING)

# Create a FastGridTemplate layout
layout = pn.template.FastGridTemplate(
    # Basic Panel layout components
    header="Next-Generation Spectral Timing Made Easy",
    sidebar=[sidebar],
    modal=True,
    # Parameters for the FastGridTemplate
    site="",  # Not shown as already doing in title
    site_url="StingrayExplorer",
    logo="./assets/images/stingray_explorer.png",
    title="Stingray Explorer",
    favicon="./assets/images/stingray_explorer.png",
    sidebar_footer="Sidebar Footer",
    # config= (TemplateConfig): Contains configuration options similar to pn.config but applied to the current Template only. (Currently only css_files is supported) But css_files are now deprecated.
    busy_indicator=busy_indicator,
    # For configuring the grid
    cols={"lg": 20, "md": 20, "sm": 20, "xs": 20, "xxs": 20},
    breakpoints={"lg": 1200, "md": 996, "sm": 768, "xs": 480, "xxs": 0},
    row_height=100,
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

# Serve the layout
layout.servable()
