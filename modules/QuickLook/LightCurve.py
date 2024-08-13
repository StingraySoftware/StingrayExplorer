import panel as pn
import holoviews as hv
from utils.globals import loaded_event_data
import numpy as np
import pandas as pd
import warnings
import hvplot.pandas
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    PlotsContainer,
    HelpBox,
    Footer,
    WarningHandler,
)


floatpanel_config = {"headerControls": {"close": "remove"}}


# Create a warning handler
def create_warning_handler():
    # Create an instance of the warning handler
    warning_handler = WarningHandler()

    # Redirect warnings to the custom handler
    warnings.showwarning = warning_handler.warn

    return warning_handler


""" Header Section """


def create_quicklook_lightcurve_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Light Curve"
    )
    home_subheading_input = pn.widgets.TextInput(name="Subheading", value="")

    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)


""" Output Box Section """


def create_loadingdata_output_box(content):
    return OutputBox(output_content=content)


""" Warning Box Section """


def create_loadingdata_warning_box(content):
    return WarningBox(warning_content=content)


""" Plots Area """


def create_lightcurve_plots_area():
    return PlotsContainer()


""" Main Area Section """


def create_lightcurve_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
):
    line_output_hv = pn.pane.HoloViews(width=500, height=300)
    dataframe_output = pn.pane.DataFrame(width=500, height=300)

    event_list_dropdown = pn.widgets.Select(
        name="Select Event List",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
    )

    dt_slider = pn.widgets.FloatSlider(
        name="Select dt",
        start=0.1,
        end=100,
        step=0.1,
        value=1,
    )

    def create_dataframe(selected_event_list_index, dt):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]
            lc_new = event_list.to_lc(dt=dt)

            df = pd.DataFrame(
                {
                    "Time": lc_new.time,
                    "Counts": lc_new.counts,
                }
            )
            return df
        return None

    def generate_lightcurve(event=None):
        if not loaded_event_data:
            output_box_container[:] = [
                create_loadingdata_output_box("No loaded event data available.")
            ]
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            output_box_container[:] = [
                create_loadingdata_output_box("No event list selected.")
            ]
            return

        dt = dt_slider.value
        df = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            line_plot_hv = df.hvplot.line(x="Time", y="Counts")
            line_output_hv.object = line_plot_hv

        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

    def show_dataframe(event=None):
        if not loaded_event_data:
            output_box_container[:] = [
                create_loadingdata_output_box("No loaded event data available.")
            ]
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            output_box_container[:] = [
                create_loadingdata_output_box("No event list selected.")
            ]
            return

        dt = dt_slider.value
        df = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            dataframe_output.object = df
            plots_container[:] = [line_output_hv, dataframe_output]
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

    generate_lightcurve_button = pn.widgets.Button(
        name="Generate Light Curve", button_type="primary"
    )
    generate_lightcurve_button.on_click(generate_lightcurve)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab1_content = pn.Column(
        event_list_dropdown,
        dt_slider,
        pn.Row(generate_lightcurve_button, show_dataframe_button),
    )

    # tab1_content.append(
    #     pn.layout.FloatPanel(
    #         "Try dragging me around.",
    #         name="Free Floating FloatPanel",
    #         contained=False,
    #         position="center",
    #     )
    #     )
    return tab1_content


def create_quicklook_lightcurve_main_area(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Light Curve": create_lightcurve_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)
