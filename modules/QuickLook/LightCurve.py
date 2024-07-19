import panel as pn

from utils.DashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer


def create_quicklook_lightcurve_header():
    # Create a text input widget for the header
    heading_input = pn.widgets.TextInput(
    name="Heading", value="QuickLook Light Curve")
    return MainHeader(heading = heading_input)

