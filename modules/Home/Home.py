import panel as pn
from utils.dashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer
from bokeh.plotting import figure  # Importing figure from Bokeh

# Create a text input widget for the header
home_heading_input = pn.widgets.TextInput(
    name="Heading", value="Welcome to Stingray Explorer"
)

home_subheading_input = pn.widgets.TextInput(
    name="Subheading", value="Next-Generation Spectral Timing Made Easy"
)

# Create header
home_header = MainHeader(
    heading=home_heading_input,
    subheading=home_subheading_input,
)

# Create different types of content for the tabs
tab1_content = pn.pane.Markdown("# Welcome to Tab 1\nThis is the content for Tab 1.")
tab2_content = pn.pane.HTML("<h1>Welcome to Tab 2</h1><p>This is some HTML content.</p>")

# Example plot using Bokeh
p = figure(width=400, height=400)
p.circle([1, 2, 3, 4, 5], [6, 7, 2, 4, 5], size=15, color="navy", alpha=0.5)
tab3_content = pn.pane.Bokeh(p)

# Example with widgets
tab4_content = pn.Column(
    pn.widgets.FloatSlider(name='Slider', start=0, end=10, value=5),
    pn.widgets.Checkbox(name='Checkbox', value=True),
)

tabs_content = {
    "hi": tab1_content,
    "Tab 2": tab2_content,
    "Tab 3": tab3_content,
    "Tab 4": tab4_content,
    "alflakj": tab3_content,
}

home_main_area = MainArea(tabs_content=tabs_content)

