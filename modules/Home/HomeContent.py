# homecontent.py

import panel as pn
from utils.dashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer
from bokeh.plotting import figure

def create_home_header():
    home_heading_input = pn.widgets.TextInput(name="Heading", value="Welcome to Stingray Explorer")
    home_subheading_input = pn.widgets.TextInput(name="Subheading", value="Where power meets comfort")
    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)

def create_home_main_area():
    tab1_content = pn.pane.Markdown("# Example Tab 1\nThis is the content for Tab 1.")
    tab2_content = pn.pane.HTML("<h1>Welcome to Tab 2</h1><p>This is some HTML content.</p>")
    p = figure(width=400, height=400)
    p.circle([1, 2, 3, 4, 5], [6, 7, 2, 4, 5], size=15, color="navy", alpha=0.5)
    tab3_content = pn.pane.Bokeh(p)
    tab4_content = pn.Column(pn.widgets.FloatSlider(name='Slider', start=0, end=10, value=5), pn.widgets.Checkbox(name='Checkbox', value=True))

    tabs_content = {"hi": tab1_content, "Tab 2": tab2_content, "Tab 3": tab3_content, "Tab 4": tab4_content, "alflakj": tab3_content}
    return MainArea(tabs_content=tabs_content)

def create_home_output_box():
    return OutputBox(output_content="This is the output content")

def create_home_warning_box():
    return WarningBox(warning_content="This is the warning content")

def create_home_bokeh_plots_container():
    p1 = figure(title="Scatter Plot")
    p1.scatter([1, 2, 3], [4, 5, 6])
    p2 = figure(title="Line Plot")
    p2.line([1, 2, 3], [4, 5, 6])
    p3 = figure(title="Bar Plot")
    p3.vbar(x=[1, 2, 3], top=[4, 5, 6], width=0.5)
    return BokehPlotsContainer(flexbox_contents=[p1, p2, p3], titles=["Scatter Plot", "Line Plot", "Bar Plot"], sizes=[(200, 200), (200, 200), (300, 300)])

def create_home_help_box():
    help_content = """## Help Section\nThis section provides help and documentation for using the dashboard."""
    return HelpBox(help_content=help_content, title="Help Section")

def create_home_footer():
    icon_buttons = [pn.widgets.Button(name="Icon 1", button_type="default"), pn.widgets.Button(name="Icon 2", button_type="default"), pn.widgets.Button(name="Icon 3", button_type="default"), pn.widgets.Button(name="Icon 4", button_type="default"), pn.widgets.Button(name="Icon 5", button_type="default")]
    footer_content = "© 2024 Stingray. All rights reserved."
    additional_links = ["[Privacy Policy](https://example.com)", "[Terms of Service](https://example.com)", "[Contact Us](https://example.com)", "[Support](https://example.com)", "[About Us](https://example.com)"]
    return Footer(main_content=footer_content, additional_links=additional_links, icons=icon_buttons)
