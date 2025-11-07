import panel as pn
import holoviews as hv
from utils.state_manager import state_manager
import pandas as pd
import numpy as np
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
from stingray import AveragedCrossspectrum

# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler

""" Header Section """
def create_quicklook_avg_cross_spectrum_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Averaged Cross Spectrum"
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
    return FloatingPlot(content=content, title=title)

""" Main Area Section """
def create_avg_cross_spectrum_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
):
    # Define Widgets
    event_list_dropdown_1 = pn.widgets.Select(
        name="Select Event List 1",
        options={name: i for i, (name, event) in enumerate(state_manager.get_event_data())},
    )

    event_list_dropdown_2 = pn.widgets.Select(
        name="Select Event List 2",
        options={name: i for i, (name, event) in enumerate(state_manager.get_event_data())},
    )

    dt_slider = pn.widgets.FloatSlider(
        name="Select dt",
        start=0.1,
        end=1000,
        step=0.1,
        value=1,
    )

    norm_select = pn.widgets.Select(
        name="Normalization",
        options=["frac", "leahy", "abs", "none"],
        value="leahy",
    )

    segment_size_input = pn.widgets.FloatInput(
        name="Segment Size", value=10, step=1
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=False
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    def create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm, segment_size):
        if selected_event_list_index_1 is not None and selected_event_list_index_2 is not None:
            event_list_1 = state_manager.get_event_data()[selected_event_list_index_1][1]
            event_list_2 = state_manager.get_event_data()[selected_event_list_index_2][1]

            # Create an AveragedCrossspectrum object using from_lightcurve
            try:
                lc1 = event_list_1.to_lc(dt=dt)
                lc2 = event_list_2.to_lc(dt=dt)
                cs = AveragedCrossspectrum.from_lightcurve(lc1, lc2, segment_size, norm=norm)

                df = pd.DataFrame(
                    {
                        "Frequency": cs.freq,
                        "Cross Power": np.abs(cs.power),
                    }
                )
                return df, cs

            except AssertionError as ae:
                if "No GTIs are equal to or longer than segment_size" in str(ae):
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Error: No GTIs are long enough to accommodate the segment size {segment_size}s. "
                            "Please reduce the segment size or check your GTIs."
                        )
                    ]
                else:
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Error generating Averaged Cross Spectrum: {ae}. "
                        )
                    ]
                return None, None

            except Exception as e:
                if "requested segment size" in str(e):
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Failed to create cross spectrum: dt is too large or the segment size is too small."
                        )
                    ]
                else:
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Error generating Averaged Cross Spectrum: {e}. "
                            "Try using a different segment size."
                        )]
                return None, None
        return None, None

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600)

    def create_holoviews_plots(cs, title, dt, norm, segment_size):
        label = f"{title} (dt={dt}, norm={norm}, segment={segment_size})"
        return hv.Curve((cs.freq, np.abs(cs.power)), label=label).opts(
            xlabel="Frequency (Hz)",
            ylabel="Cross Spectral Amplitude",
            title=f"{title} (dt={dt}, norm={norm}, segment={segment_size})",
            width=600,
            height=600,
            shared_axes=False,
        )

    def create_dataframe_panes(df, title, dt, norm, segment_size):
        return pn.FlexBox(
            pn.pane.Markdown(f"**{title} (dt={dt}, norm={norm}, segment={segment_size})**"),
            pn.pane.DataFrame(df, width=600, height=600),
            align_items="center",
            justify_content="center",
            flex_wrap="nowrap",
            flex_direction="column",
        )

    def generate_avg_cross_spectrum(event=None):
        if not state_manager.get_event_data():
            output_box_container[:] = [
                create_loadingdata_output_box("No loaded event data available.")
            ]
            return

        selected_event_list_index_1 = event_list_dropdown_1.value
        selected_event_list_index_2 = event_list_dropdown_2.value
        if selected_event_list_index_1 is None or selected_event_list_index_2 is None:
            output_box_container[:] = [
                create_loadingdata_output_box("Both event lists must be selected.")
            ]
            return

        dt = dt_slider.value
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm, segment_size)
        if df is not None:
            plot_title = f"Averaged Cross Spectrum for {state_manager.get_event_data()[selected_event_list_index_1][0]} vs {state_manager.get_event_data()[selected_event_list_index_2][0]}"
            plot_hv = create_holoviews_plots(cs, title=plot_title, dt=dt, norm=norm, segment_size=segment_size)
            holoviews_output = create_holoviews_panes(plot_hv)

            if floatpanel_plots_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=holoviews_output, title=plot_title
                    )
                )
            else:
                markdown_content = f"## {plot_title}"
                plots_container.append(
                    pn.FlexBox(
                        pn.pane.Markdown(markdown_content),
                        holoviews_output,
                        align_items="center",
                        justify_content="center",
                        flex_wrap="nowrap",
                        flex_direction="column",
                    )
                )
            output_box_container[:] = [
                create_loadingdata_output_box("Averaged Cross Spectrum generated successfully.")
            ]
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create averaged cross spectrum.")
            ]

    def show_dataframe(event=None):
        if not state_manager.get_event_data():
            output_box_container[:] = [
                create_loadingdata_output_box("No loaded event data available.")
            ]
            return

        selected_event_list_index_1 = event_list_dropdown_1.value
        selected_event_list_index_2 = event_list_dropdown_2.value
        if selected_event_list_index_1 is None or selected_event_list_index_2 is None:
            output_box_container[:] = [
                create_loadingdata_output_box("Both event lists must be selected.")
            ]
            return

        dt = dt_slider.value
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm, segment_size)
        if df is not None:
            dataframe_output = create_dataframe_panes(df, f"{state_manager.get_event_data()[selected_event_list_index_1][0]} vs {state_manager.get_event_data()[selected_event_list_index_2][0]}", dt, norm, segment_size)
            if dataframe_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=dataframe_output,
                        title=f"DataFrame for {state_manager.get_event_data()[selected_event_list_index_1][0]} vs {state_manager.get_event_data()[selected_event_list_index_2][0]}",
                    )
                )
            else:
                plots_container.append(dataframe_output)
            output_box_container[:] = [
                create_loadingdata_output_box("DataFrame generated successfully.")
            ]
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

    generate_cross_spectrum_button = pn.widgets.Button(
        name="Generate Averaged Cross Spectrum", button_type="primary"
    )
    generate_cross_spectrum_button.on_click(generate_avg_cross_spectrum)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab_content = pn.Column(
        event_list_dropdown_1,
        event_list_dropdown_2,
        dt_slider,
        norm_select,
        segment_size_input,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_cross_spectrum_button, show_dataframe_button),
    )
    return tab_content

def create_quicklook_avg_cross_spectrum_main_area(
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
        "Averaged Cross Spectrum": create_avg_cross_spectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)

def create_quicklook_avg_cross_spectrum_area():
    return PlotsContainer()
