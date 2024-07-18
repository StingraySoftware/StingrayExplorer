import panel as pn
import importlib
from modules.QuickLook.LightCurve import QuickLook_lightcurve_header
from modules.Home.HomeContent import create_home_bokeh_plots_container, create_home_footer, create_home_header, create_home_help_box, create_home_main_area, create_home_output_box, create_home_warning_box

def create_sidebar(main_area, header, footer, output_box, warning_box, help_box):
    menu_items_quicklook_stingray = [
        ("Light Curve", "QuickLookLightCurve"),
        ("Power spectra", "QuickLookPowerspectra"),
        ("CrossCorrelation", "QuickLookCrossCorrelation"),
    ]

    # Home Button
    home_button = pn.widgets.Button(
        name="Home", button_type="primary", styles={"width": "100%"}
    )

    # Load Button
    load_data_button = pn.widgets.Button(
        name="Load Data", button_type="warning", styles={"width": "100%"}
    )

    # Create MenuButtons
    quicklook_stingray_button = pn.widgets.MenuButton(
        name="Quicklook",
        items=menu_items_quicklook_stingray,
        button_type="primary",
        styles={"width": "100%"},
    )

    def handle_home_button_selection(event):
        a = create_home_header()
        header.heading = a.heading
    home_button.on_click(handle_home_button_selection)

    # Load Button changing main content
    def load_data(event):
        pass
    load_data_button.on_click(load_data)

    # Quicklook Button changing main content
    def handle_quicklook_button_selection(event):   
        clicked = event.new
        if clicked == "QuickLookLightCurve":
            header.heading = QuickLook_lightcurve_header.heading

    quicklook_stingray_button.on_click(handle_quicklook_button_selection)

    sidebar = pn.Column(
        pn.pane.Markdown("# Navigation"),
        home_button,
        load_data_button,
        quicklook_stingray_button,
    )

    return sidebar
