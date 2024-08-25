import panel as pn
import holoviews as hv
from utils.globals import loaded_event_data
import pandas as pd
import warnings
import hvplot.pandas
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    Footer,
    WarningHandler,
    FloatingPlot,
    PlotsContainer,
)


# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
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
    float_panel_container,
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


""" Float Panel """


def create_floatpanel_area(content, title):
    return FloatingPlot(content, title)


""" Main Area Section """


def create_lightcurve_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container
):

    event_list_dropdown = pn.widgets.Select(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
    )

    dt_slider = pn.widgets.FloatSlider(
        name="Select dt",
        start=0.1,
        end=1000,
        step=0.1,
        value=1,
    )

    # tstart_input = pn.widgets.FloatInput(
    #     name="Start Time (tstart)",
    #     value=None,
    #     step=0.1,
    # )

    combine_plots_checkbox = pn.widgets.Checkbox(
        name="Combine with Existing Plot", value=False
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(name="Add Plot to FloatingPanel", value=False)

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    def create_holoviews_panes():
        return pn.pane.HoloViews(width=600, height=600)

    def create_holoviews_plots(df):
        return df.hvplot.line(x="Time", y="Counts")

    def create_dataframe_panes():
        return pn.pane.DataFrame(width=600, height=600)

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
            dataframe_output = create_dataframe_panes()
            dataframe_output.object = df

            if dataframe_checkbox.value:
                float_panel_container.append(
                    pn.layout.FloatPanel(
                        dataframe_output,
                        contained=False,
                        position="center",
                        height=600,
                        width=600,
                        theme="primary",
                    )
                )
            else:
                plots_container.append(dataframe_output)
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

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
            plot_hv = create_holoviews_plots(df)
            holoviews_output = pn.pane.HoloViews(plot_hv, width=500, height=500)

            if not combine_plots_checkbox.value:
                # Handle case when plots are not combined
                if floatpanel_plots_checkbox.value:
                    # Create a new FloatPanel for each independent plot
                    new_floatpanel = pn.layout.FloatPanel(
                        holoviews_output,
                        contained=False,
                        position="center",
                        height=350,
                        width=500,
                        theme="primary",
                    )
                    float_panel_container.append(new_floatpanel)
                else:
                    plots_container.append(holoviews_output)
            else:
                # Handle case when plots are combined
                existing_plots = [
                    p.object
                    for p in plots_container
                    if isinstance(p, pn.pane.HoloViews)
                ]
                combined_plot = hv.Overlay(existing_plots + [plot_hv])
                combined_pane = pn.pane.HoloViews(combined_plot, width=500, height=500)

                if floatpanel_plots_checkbox.value:
                    new_floatpanel = pn.layout.FloatPanel(
                        combined_pane,
                        contained=False,
                        position="center",
                        height=350,
                        width=500,
                        theme="primary",
                    )
                    float_panel_container.append(new_floatpanel)
                else:
                    plots_container.append(combined_pane)
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
        combine_plots_checkbox,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_lightcurve_button, show_dataframe_button),
    )
    return tab1_content


def create_quicklook_lightcurve_main_area(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
    float_panel_container,
):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Light Curve": create_lightcurve_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container
        ),
    }

    return MainArea(tabs_content=tabs_content)


def create_quicklook_lightcurve_plots_area():
    """
    Create the plots area for the quicklook lightcurve tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the quicklook lightcurve tab.
    """
    return PlotsContainer()