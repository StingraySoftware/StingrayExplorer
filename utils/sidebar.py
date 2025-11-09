import panel as pn

from modules.QuickLook.Bispectrum import (
    create_quicklook_bispectrum_header,
    create_quicklook_bispectrum_main_area,
    create_quicklook_bispectrum_area,
)
from modules.QuickLook.PowerColors import (
    create_quicklook_powercolors_header,
    create_quicklook_powercolors_main_area,
    create_quicklook_powercolors_area,
)

from modules.QuickLook.DynamicalPowerSpectrum import (
    create_quicklook_dynamicalpowerspectrum_header,
    create_quicklook_dynamicalpowerspectrum_main_area,
    create_quicklook_dynamicalpowerspectrum_area,
)

from modules.Home.HomeContent import (
    create_home_header,
    create_home_main_area,
    create_home_output_box,
    create_home_warning_box,
    create_home_help_area,
    create_home_footer,
    create_home_plots_area,
    create_home_resource_monitor,
)
from modules.DataLoading.DataIngestion import (
    create_loadingdata_header,
    create_loadingdata_main_area,
    create_loadingdata_output_box,
    create_loadingdata_warning_box,
    create_loadingdata_help_area,
    create_loadingdata_plots_area,
)

from modules.QuickLook.EventList import (
    create_eventlist_header,
    create_eventlist_main_area,
    create_eventlist_output_box,
    create_eventlist_warning_box,
    create_eventlist_help_area,
    create_eventlist_plots_area,
)

from modules.QuickLook.LightCurve import (
    create_quicklook_lightcurve_header,
    create_quicklook_lightcurve_main_area,
    create_quicklook_lightcurve_plots_area,
)
from modules.QuickLook.PowerSpectrum import (
    create_quicklook_powerspectrum_header,
    create_quicklook_powerspectrum_main_area,
    create_quicklook_powerspectrum_area,
)
from modules.QuickLook.AveragePowerSpectrum import (
    create_quicklook_avg_powerspectrum_header,
    create_quicklook_avg_powerspectrum_main_area,
    create_quicklook_avg_powerspectrum_area,
)
from modules.QuickLook.CrossSpectrum import (
    create_quicklook_cross_spectrum_header,
    create_quicklook_cross_spectrum_main_area,
    create_quicklook_cross_spectrum_area,
)
from modules.QuickLook.AverageCrossSpectrum import (
    create_quicklook_avg_cross_spectrum_header,
    create_quicklook_avg_cross_spectrum_main_area,
    create_quicklook_avg_cross_spectrum_area,
)
from modules.Monitoring import create_stats_dashboard
from assets.icons.svg import HOME_ICON_SVG, LOAD_DATA_ICON_SVG
from utils.app_context import AppContext
from utils.DashboardClasses import MainHeader


def create_sidebar(context: AppContext):
    menu_items_quicklook_stingray = [
        ("Event List", "QuickLookEventList"),
        ("Light Curve", "QuickLookLightCurve"),
        ("Power Spectrum", "QuickLookPowerspectra"),
        ("Averaged Power Spectrum", "QuickLookAvgPowerspectra"),
        ("Cross Spectrum", "QuickLookCrossSpectrum"),
        ("Averaged Cross Spectrum", "QuickLookAvgCrossSpectrum"),
        ("Bispectrum", "QuickLookBispectrum"),
        ("Dynamical Power Spectrum", "QuickLookDynamicalPowerspectrum"),
        ("Power Colors", "QuickLookPowerColors"),  
    ]

    # Home Button
    home_button = pn.widgets.Button(
        icon=HOME_ICON_SVG,
        icon_size="20px",
        name="",
        button_type="default",
        styles={"width": "50"},
        description="Back to Home",
    )

    # Load Button
    load_data_button = pn.widgets.Button(
        icon=LOAD_DATA_ICON_SVG,
        icon_size="20px",
        name="Read Data",
        button_type="warning",
        styles={"width": "100"},
        description="Loading EventList",
    )

    # Stats/Monitoring Button
    stats_button = pn.widgets.Button(
        name="Monitoring",
        button_type="primary",
        styles={"width": "90%"},
        description="View application statistics and performance metrics",
    )

    # Create MenuButtons
    quicklook_stingray_button = pn.widgets.MenuButton(
        name="Quicklook",
        items=menu_items_quicklook_stingray,
        button_type="primary",
        styles={"width": "90%"},
    )

    def handle_home_button_selection(event):
        context.update_container('header', create_home_header())
        context.update_container('main_area', create_home_main_area())
        context.update_container('output_box', create_home_output_box())
        context.update_container('warning_box', create_home_warning_box())
        context.update_container('help_box', create_home_help_area())
        context.update_container('footer', create_home_footer())
        context.update_container('plots', create_home_plots_area())
        context.update_container('resource_monitor', create_home_resource_monitor())

    home_button.on_click(handle_home_button_selection)

    # Load Button changing main content
    def load_data(event):
        context.update_container('header', create_loadingdata_header(context))
        context.update_container('main_area', create_loadingdata_main_area(context))
        context.update_container('output_box', create_home_output_box())
        context.update_container('warning_box', create_home_warning_box())
        context.update_container('help_box', create_loadingdata_help_area())
        context.update_container('plots', create_loadingdata_plots_area())

    load_data_button.on_click(load_data)

    # Stats Button changing main content
    def handle_stats_button(event):
        # Create standard header using MainHeader component
        stats_heading = pn.widgets.TextInput(name="Heading", value="Application Statistics")
        stats_header = MainHeader(heading=stats_heading)

        context.update_container('header', stats_header)
        context.update_container('main_area', create_stats_dashboard(context))
        context.update_container('output_box', pn.pane.Markdown(""))
        context.update_container('warning_box', pn.pane.Markdown(""))
        context.update_container('help_box', pn.pane.Markdown(""))
        context.update_container('plots', pn.pane.Markdown(""))

    stats_button.on_click(handle_stats_button)

    # Quicklook Button changing main content
    def handle_quicklook_button_selection(event):
        clicked = event.new

        if clicked == "QuickLookEventList":
            context.update_container('header', create_eventlist_header(context))
            context.update_container('main_area', create_eventlist_main_area(context))
            context.update_container('plots', create_eventlist_plots_area())

        elif clicked == "QuickLookLightCurve":
            context.update_container('header', create_quicklook_lightcurve_header(context))
            context.update_container('main_area', create_quicklook_lightcurve_main_area(context))
            context.update_container('plots', create_quicklook_lightcurve_plots_area())

        elif clicked == "QuickLookPowerspectra":
            context.update_container('header', create_quicklook_powerspectrum_header(context))
            context.update_container('main_area', create_quicklook_powerspectrum_main_area(context))
            context.update_container('plots', create_quicklook_powerspectrum_area())

        elif clicked == "QuickLookAvgPowerspectra":
            context.update_container('header', create_quicklook_avg_powerspectrum_header(context))
            context.update_container('main_area', create_quicklook_avg_powerspectrum_main_area(context))
            context.update_container('plots', create_quicklook_avg_powerspectrum_area())

        elif clicked == "QuickLookCrossSpectrum":
            context.update_container('header', create_quicklook_cross_spectrum_header(context))
            context.update_container('main_area', create_quicklook_cross_spectrum_main_area(context))
            context.update_container('plots', create_quicklook_cross_spectrum_area())

        elif clicked == "QuickLookAvgCrossSpectrum":
            context.update_container('header', create_quicklook_avg_cross_spectrum_header(context))
            context.update_container('main_area', create_quicklook_avg_cross_spectrum_main_area(context))
            context.update_container('plots', create_quicklook_avg_cross_spectrum_area())

        elif clicked == "QuickLookBispectrum":
            context.update_container('header', create_quicklook_bispectrum_header(context))
            context.update_container('main_area', create_quicklook_bispectrum_main_area(context))
            context.update_container('plots', create_quicklook_bispectrum_area())

        elif clicked == "QuickLookDynamicalPowerspectrum":
            context.update_container('header', create_quicklook_dynamicalpowerspectrum_header(context))
            context.update_container('main_area', create_quicklook_dynamicalpowerspectrum_main_area(context))
            context.update_container('plots', create_quicklook_dynamicalpowerspectrum_area())

        elif clicked == "QuickLookPowerColors":
            context.update_container('header', create_quicklook_powercolors_header(context))
            context.update_container('main_area', create_quicklook_powercolors_main_area(context))
            context.update_container('plots', create_quicklook_powercolors_area())

    quicklook_stingray_button.on_click(handle_quicklook_button_selection)

    sidebar = pn.FlexBox(
        pn.pane.Markdown("<h1> Navigation </h1>"),
        pn.FlexBox(
            home_button,
            load_data_button,
            flex_direction="row",
            justify_content="center",
            align_items="center",
        ),
        quicklook_stingray_button,
        stats_button,
        flex_direction="column",
        align_items="flex-start",
        justify_content="flex-start",
    )

    return sidebar
