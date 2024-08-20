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
)
from stingray import Powerspectrum

# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler

""" Header Section """

def create_quicklook_powerspectrum_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Power Spectrum"
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

def create_powerspectrum_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
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

    combine_plots_checkbox = pn.widgets.Checkbox(
        name="Combine with Existing Plot", value=False
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(name="Add Plot to FloatingPanel", value=False)

    def create_holoviews_panes():
        return pn.pane.HoloViews(width=600, height=500)

    def create_holoviews_plots(ps):
        return hv.Curve((ps.freq, ps.power)).opts(
            xlabel='Frequency (Hz)', ylabel='Power',
            title='Power Spectrum',
            width=600, height=500
        )

    def create_dataframe_panes():
        return pn.pane.DataFrame(width=600, height=500)

    def create_dataframe(selected_event_list_index, dt):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]
            lc_new = event_list.to_lc(dt=dt)

            # Create a PowerSpectrum object
            ps = Powerspectrum.from_lightcurve(lc_new, norm="leahy")

            df = pd.DataFrame(
                {
                    "Frequency": ps.freq,
                    "Power": ps.power,
                }
            )
            return df, ps
        return None, None

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
        df, ps = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            dataframe_output = create_dataframe_panes()
            dataframe_output.object = df

            if floatpanel_plots_checkbox.value:
                header_container.append(
                    pn.layout.FloatPanel(
                        dataframe_output,
                        contained=False,
                        position="center",
                        height=350,
                        width=500,
                        theme="primary",
                    )
                )
            else:
                plots_container.append(dataframe_output)
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

    def generate_powerspectrum(event=None):
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
        df, ps = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            holoviews_output = create_holoviews_panes()
            plot_hv = create_holoviews_plots(ps)
            holoviews_output.object = plot_hv

            if combine_plots_checkbox.value:
                # If combining, we need to get all existing plots and combine with the new one
                existing_plots = [
                    p.object
                    for p in plots_container
                    if isinstance(p, pn.pane.HoloViews)
                ]
                combined_plot = hv.Overlay(existing_plots + [plot_hv])
                combined_pane = pn.pane.HoloViews(combined_plot, width=500, height=500)

                if floatpanel_plots_checkbox.value:
                    header_container.append(
                        pn.layout.FloatPanel(
                            combined_pane,
                            contained=False,
                            position="center",
                            height=350,
                            theme="primary",
                        )
                    )
                else:
                    plots_container.append(combined_pane)
            else:
                if floatpanel_plots_checkbox.value:
                    header_container.append(
                        pn.layout.FloatPanel(
                            holoviews_output,
                            contained=False,
                            position="center",
                            height=350,
                            theme="primary",
                        )
                    )
                else:
                    plots_container.append(holoviews_output)
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create power spectrum.")
            ]

    generate_powerspectrum_button = pn.widgets.Button(
        name="Generate Power Spectrum", button_type="primary"
    )
    generate_powerspectrum_button.on_click(generate_powerspectrum)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab1_content = pn.Column(
        event_list_dropdown,
        dt_slider,
        combine_plots_checkbox,
        floatpanel_plots_checkbox,
        pn.Row(generate_powerspectrum_button, show_dataframe_button),
    )
    return tab1_content

def create_quicklook_powerspectrum_main_area(
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
        "Power Spectrum": create_powerspectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)
