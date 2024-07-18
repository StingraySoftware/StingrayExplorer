import panel as pn
import importlib
from modules.QuickLook.LightCurve import QuickLook_lightcurve_header

def create_sidebar(main_area, header, footer, output_box, warning_box, help_box):
    menu_items_quicklook_stingray = [
        ("Light Curve", "QuickLookLightCurve"),
        ("Power spectra", "QuickLookPowerspectra"),
        ("CrossCorrelation", "QuickLookCrossCorrelation"),
    ]

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
        load_data_button,
        quicklook_stingray_button,
    )

    return sidebar
