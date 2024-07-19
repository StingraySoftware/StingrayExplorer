# homecontent.py

import panel as pn
from utils.DashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer
from bokeh.plotting import figure
from utils.strings import HOME_HEADER_STRING, WELCOME_MESSAGE_STRING, FOOTER_STRING, STINGRAY_TAB_STRING, HOLOVIZ_TAB_STRING, DASHBOARD_TAB_STRING, OUTPUT_BOX_STRING, WARNING_BOX_STRING, HELP_BOX_STRING

def create_home_header():
    home_heading_input = pn.widgets.TextInput(name="Heading", value="Welcome to Stingray Explorer")
    home_subheading_input = pn.widgets.TextInput(name="Subheading", value="Stingray GUI using HoloViz")

    button = pn.widgets.Button(name="Change Heading", button_type="primary")
    def change_heading(event):
        home_heading_input.value = "New Heading"
        home_subheading_input.value = "New Subheading"
    button.on_click(change_heading)

    
    return MainHeader(heading=home_heading_input, subheading=home_subheading_input, button_1_name="button", button_1_action=change_heading)

def create_home_main_area():
    tab1_content = pn.pane.Markdown(STINGRAY_TAB_STRING)
    tab2_content = pn.pane.Markdown(HOLOVIZ_TAB_STRING)
    tab3_content = pn.pane.Markdown(DASHBOARD_TAB_STRING)
    
    tabs_content = {"What's Stingray?": tab1_content, "What's HoloViz?": tab2_content, "Dashboard": tab3_content}
    
    return MainArea(tabs_content=tabs_content)

def create_home_output_box():
    return OutputBox(output_content=OUTPUT_BOX_STRING)

def create_home_warning_box():
    return WarningBox(warning_content=WARNING_BOX_STRING)

def create_home_bokeh_plots_container():
    p1 = pn.pane.Markdown(" Plot 1")
    p2 = pn.pane.Markdown(" Plot 2")
    p3 = pn.pane.Markdown(" Plot 3")
    p4 = pn.pane.Markdown("Plot 4")
    p5 = pn.pane.Markdown("Plot 5")
    return BokehPlotsContainer(flexbox_contents=[p1, p2, p3, p4, p5], titles=["Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5"], sizes=[(300, 300), (300, 300), (300, 300), (300, 300), (300, 300)])

def create_home_help_box():
    help_content = HELP_BOX_STRING
    return HelpBox(help_content=help_content, title="Help Section")

def create_home_footer():
    icon_buttons = [pn.widgets.Button(name="Icon 1", button_type="default"), pn.widgets.Button(name="Icon 2", button_type="default"), pn.widgets.Button(name="Icon 3", button_type="default"), pn.widgets.Button(name="Icon 4", button_type="default"), pn.widgets.Button(name="Icon 5", button_type="default")]
    footer_content = "© 2024 Stingray. All rights reserved."
    additional_links = ["[Privacy Policy](https://example.com)", "[Terms of Service](https://example.com)", "[Contact Us](https://example.com)", "[Support](https://example.com)", "[About Us](https://example.com)"]
    return Footer(main_content=footer_content, additional_links=additional_links, icons=icon_buttons)
