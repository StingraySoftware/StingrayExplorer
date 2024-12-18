import panel as pn
import importlib

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

from modules.Home.HomeContent import (
    create_home_header,
    create_home_main_area,
    create_home_output_box,
    create_home_warning_box,
    create_home_help_area,
    create_home_footer,
    create_home_plots_area,
)
from modules.DataLoading.DataIngestion import (
    create_loadingdata_header,
    create_loadingdata_main_area,
    create_loadingdata_output_box,
    create_loadingdata_warning_box,
    create_loadingdata_help_area,
    create_loadingdata_plots_area,
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
from assets.icons.svg import HOME_ICON_SVG, LOAD_DATA_ICON_SVG

def create_sidebar(
    main_area, header, footer, output_box, warning_box, help_box, plots_container, float_panel_container
):
    menu_items_quicklook_stingray = [
        ("Light Curve", "QuickLookLightCurve"),
        ("Power Spectrum", "QuickLookPowerspectra"),
        ("Averaged Power Spectrum", "QuickLookAvgPowerspectra"),
        ("Cross Spectrum", "QuickLookCrossSpectrum"),
        ("Averaged Cross Spectrum", "QuickLookAvgCrossSpectrum"),
        ("Bispectrum", "QuickLookBispectrum"),
        ("Power Colors", "QuickLookPowerColors"),  # New menu item for Power Colors
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

    # Create MenuButtons
    quicklook_stingray_button = pn.widgets.MenuButton(
        name="Quicklook",
        items=menu_items_quicklook_stingray,
        button_type="primary",
        styles={"width": "90%"},
    )

    def handle_home_button_selection(event):
        header[:] = [create_home_header()]
        main_area[:] = [create_home_main_area()]
        output_box[:] = [create_home_output_box()]
        warning_box[:] = [create_home_warning_box()]
        help_box[:] = [create_home_help_area()]
        footer[:] = [create_home_footer()]
        plots_container[:] = [create_home_plots_area()]

    home_button.on_click(handle_home_button_selection)

    # Load Button changing main content
    def load_data(event):
        header[:] = [
            create_loadingdata_header(
                header_container=header,
                main_area_container=main_area,
                output_box_container=output_box,
                warning_box_container=warning_box,
                plots_container=plots_container,
                help_box_container=help_box,
                footer_container=footer,
            )
        ]
        main_area[:] = [
            create_loadingdata_main_area(
                header_container=header,
                main_area_container=main_area,
                output_box_container=output_box,
                warning_box_container=warning_box,
                plots_container=plots_container,
                help_box_container=help_box,
                footer_container=footer,
            )
        ]
        output_box[:] = [create_home_output_box()]
        warning_box[:] = [create_home_warning_box()]
        help_box[:] = [create_loadingdata_help_area()]
        plots_container[:] = [create_loadingdata_plots_area()]

    load_data_button.on_click(load_data)

    # Quicklook Button changing main content
    def handle_quicklook_button_selection(event):
        clicked = event.new
        if clicked == "QuickLookLightCurve":
            header[:] = [
                create_quicklook_lightcurve_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            main_area[:] = [
                create_quicklook_lightcurve_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_lightcurve_plots_area()]

        elif clicked == "QuickLookPowerspectra":
            header[:] = [
                create_quicklook_powerspectrum_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                )
            ]
            main_area[:] = [
                create_quicklook_powerspectrum_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_powerspectrum_area()]

        elif clicked == "QuickLookAvgPowerspectra":
            header[:] = [
                create_quicklook_avg_powerspectrum_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                )
            ]
            main_area[:] = [
                create_quicklook_avg_powerspectrum_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_avg_powerspectrum_area()]

        elif clicked == "QuickLookCrossSpectrum":
            header[:] = [
                create_quicklook_cross_spectrum_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                )
            ]
            main_area[:] = [
                create_quicklook_cross_spectrum_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_cross_spectrum_area()]

        elif clicked == "QuickLookAvgCrossSpectrum":
            header[:] = [
                create_quicklook_avg_cross_spectrum_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                )
            ]
            main_area[:] = [
                create_quicklook_avg_cross_spectrum_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_avg_cross_spectrum_area()]

        elif clicked == "QuickLookBispectrum":
            header[:] = [
                create_quicklook_bispectrum_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                )
            ]
            main_area[:] = [
                create_quicklook_bispectrum_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,
                )
            ]
            plots_container[:] = [create_quicklook_bispectrum_area()]

        elif clicked == "QuickLookPowerColors":
            header[:] = [
                create_quicklook_powercolors_header(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,  # Ensure this is passed
                )
            ]
            main_area[:] = [
                create_quicklook_powercolors_main_area(
                    header_container=header,
                    main_area_container=main_area,
                    output_box_container=output_box,
                    warning_box_container=warning_box,
                    plots_container=plots_container,
                    help_box_container=help_box,
                    footer_container=footer,
                    float_panel_container=float_panel_container,  # Ensure this is passed
                )
            ]
            plots_container[:] = [create_quicklook_powercolors_area()]


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
        flex_direction="column",
        align_items="flex-start",
        justify_content="flex-start",
    )

    return sidebar
