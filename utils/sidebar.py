import panel as pn
import importlib
from modules.QuickLook.LightCurve import create_quicklook_lightcurve_header
from modules.Home.HomeContent import create_home_bokeh_plots_container, create_home_footer, create_home_header, create_home_help_box, create_home_main_area, create_home_output_box, create_home_warning_box
from assets.icons.svg import HOME_ICON_SVG, LOAD_DATA_ICON_SVG

def create_sidebar(main_area, header, footer, output_box, warning_box, help_box):
    menu_items_quicklook_stingray = [
        ("Light Curve", "QuickLookLightCurve"),
        ("Power spectra", "QuickLookPowerspectra"),
        ("Cross Correlation", "QuickLookCrossCorrelation"),
    ]

    
    # Home Button
    home_button = pn.widgets.Button(
        icon=HOME_ICON_SVG, icon_size="20px", name="", button_type="default", styles={"width": "50"}, description="Back to Home"
    )

    # Load Button
    load_data_button = pn.widgets.Button(
        icon=LOAD_DATA_ICON_SVG, icon_size="20px",name="Load Data", button_type="warning", styles={"width": "100"},
        description="Loading EventList"
    )

    # Create MenuButtons
    quicklook_stingray_button = pn.widgets.MenuButton(
        name="Quicklook",
        items=menu_items_quicklook_stingray,
        button_type="primary",
        styles={"width": "90%"},
    )

    def handle_home_button_selection(event):
        header[:]=[create_home_header()]
    
    home_button.on_click(handle_home_button_selection)

    # Load Button changing main content
    def load_data(event):
        pass
        
    load_data_button.on_click(load_data)

    # Quicklook Button changing main content
    def handle_quicklook_button_selection(event):   
        clicked = event.new
        if clicked == "QuickLookLightCurve":
            header[:]=[create_quicklook_lightcurve_header()]


    quicklook_stingray_button.on_click(handle_quicklook_button_selection)

    sidebar = pn.FlexBox(
        
        pn.pane.Markdown("# Navigation"),
        pn.FlexBox(home_button,
        load_data_button, flex_direction="row", justify_content="center", align_items="center"),
        
        quicklook_stingray_button,

        flex_direction="column",
        align_items="flex-start",
        justify_content="flex-start",
    )

    return sidebar
