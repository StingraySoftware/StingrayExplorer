import panel as pn

from utils.dashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer

# Create a text input widget for the header
heading_input = pn.widgets.TextInput(
    name="Heading", value="QuickLook Light Curve"
)

QuickLook_lightcurve_header = MainHeader(heading = heading_input)

