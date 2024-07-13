import panel as pn
from utils.strings import HOME_HEADING_STRING, WELCOME_MESSAGE


# Initialize panel extension
pn.extension()

# Create a boolean status indicator
busy_indicator = pn.indicators.BooleanStatus(value=True, color='warning', width=30, height=30)

# Create header
HOME_HEADING = pn.pane.Markdown(HOME_HEADING_STRING, stylesheets=['../assets/stylesheets/explorer.css'])

# Create a welcome message
welcome_message = pn.pane.Markdown(WELCOME_MESSAGE)

# Create main content layout
main = pn.Column(HOME_HEADING, welcome_message)

# Create sidebar using the create_sidebar function and pass the main content layout
sidebar = pn.pane.Markdown("Sidebar")

# Create a footer
footer = pn.pane.Markdown(
    """
    <div style='text-align: center;'>
        <p>Stingray Explorer Dashboard</p>
        <p>&copy; 2021 Kartik Mandar</p>
    </div>
    """,
    width=200,
)

# Create a FastGridTemplate layout
layout = pn.template.FastGridTemplate(

    # Basic Panel layout components
    header="Next-Generation Spectral Timing Made Easy",
    sidebar=[sidebar],
    main=[main, footer],
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
    cols={'lg': 12, 'md': 10, 'sm': 6, 'xs': 4, 'xxs': 2},
    breakpoints={'lg': 1200, 'md': 996, 'sm': 768, 'xs': 480, 'xxs': 0},
    row_height=150,
    dimensions={'minW': 0, 'maxW': float('inf'), 'minH': 0, 'maxH': float('inf')},
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
    meta_description='Stingray Explorer Dashboard',
    meta_keywords='Stingray, Explorer, Dashboard, Astronomy, Stingray Explorer, X-ray Astronomy, X-ray Data Analysis',
    meta_author='Kartik Mandar',
    meta_refresh='', 
    meta_viewport='width=device-width, initial-scale=1',
    base_url='/',
    base_target='_self',
)

# Serve the layout
layout.servable()
