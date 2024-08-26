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
from stingray import AveragedPowerspectrum


# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler


""" Header Section """


def create_quicklook_avg_powerspectrum_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Averaged Power Spectrum"
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


def create_avg_powerspectrum_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
):
    # Define Widgets
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

    norm_select = pn.widgets.Select(
        name="Normalization",
        options=["frac", "leahy", "abs", "none"],
        value="leahy",
    )

    segment_size_input = pn.widgets.FloatInput(
        name="Segment Size", value=10, step=1
    )

    multi_event_select = pn.widgets.MultiSelect(
        name="Or Select Event List(s) to Combine",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
        size=8,
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=False
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    # Internal functions to encapsulate functionality
    def create_dataframe(selected_event_list_index, dt, norm, segment_size):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]

            # Create an AveragedPowerspectrum object using from_lightcurve
            try:
                lc = event_list.to_lc(dt=dt)
                ps = AveragedPowerspectrum.from_lightcurve(lc, segment_size, norm=norm)

                df = pd.DataFrame(
                    {
                        "Frequency": ps.freq,
                        "Power": ps.power,
                    }
                )
                return df, ps

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
                            f"Error generating Averaged Power Spectrum: {ae}. "
                        )
                    ]
                return None, None

            except Exception as e:
                if "requested segment size" in str(e):
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Failed to create power spectrum: dt is too large or the segment size is too small."
                        )
                    ]
                else:
                    output_box_container[:] = [
                        create_loadingdata_output_box(
                            f"Error generating Averaged Power Spectrum: {e}. "
                            "Try using a different segment size."
                        )]
                return None, None
        return None, None

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600)

    def create_holoviews_plots(ps, title, dt, norm, segment_size):
        label = f"{title} (dt={dt}, norm={norm}, segment={segment_size})"
        return hv.Curve((ps.freq, ps.power), label=label).opts(
            xlabel="Frequency (Hz)",
            ylabel="Power",
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

    def generate_avg_powerspectrum(event=None):
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
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, ps = create_dataframe(selected_event_list_index, dt, norm, segment_size)
        if df is not None:
            plot_title = f"Averaged Power Spectrum for {loaded_event_data[selected_event_list_index][0]}"
            plot_hv = create_holoviews_plots(ps, title=plot_title, dt=dt, norm=norm, segment_size=segment_size)
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
                create_loadingdata_output_box("Averaged Power Spectrum generated successfully.")
            ]
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create averaged power spectrum.")
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
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, ps = create_dataframe(selected_event_list_index, dt, norm, segment_size)
        if df is not None:
            dataframe_output = create_dataframe_panes(df, f"{loaded_event_data[selected_event_list_index][0]}", dt, norm, segment_size)
            if dataframe_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=dataframe_output,
                        title=f"DataFrame for {loaded_event_data[selected_event_list_index][0]}",
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

    def combine_selected_plots(event=None):
        selected_event_list_indices = multi_event_select.value
        if not selected_event_list_indices:
            output_box_container[:] = [
                create_loadingdata_output_box("No event lists selected.")
            ]
            return

        combined_plots = []
        combined_title = []

        for index in selected_event_list_indices:
            dt = dt_slider.value
            norm = norm_select.value
            segment_size = segment_size_input.value
            df, ps = create_dataframe(index, dt, norm, segment_size)
            if df is not None:
                event_list_name = loaded_event_data[index][0]
                plot_hv = create_holoviews_plots(ps, title=event_list_name, dt=dt, norm=norm, segment_size=segment_size)
                combined_plots.append(plot_hv)
                combined_title.append(event_list_name)

        if combined_plots:
            combined_plot = hv.Overlay(combined_plots).opts(shared_axes=False)
            combined_pane = create_holoviews_panes(combined_plot)

            combined_title_str = " + ".join(combined_title)
            if floatpanel_plots_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=combined_pane, title=combined_title_str
                    )
                )
            else:
                markdown_content = f"## {combined_title_str}"
                plots_container.append(
                    pn.FlexBox(
                        pn.pane.Markdown(markdown_content),
                        combined_pane,
                        align_items="center",
                        justify_content="center",
                        flex_wrap="nowrap",
                        flex_direction="column",
                    )
                )
            output_box_container[:] = [
                create_loadingdata_output_box("Combined plots generated successfully.")
            ]
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to combine plots.")
            ]

    generate_powerspectrum_button = pn.widgets.Button(
        name="Generate Averaged Power Spectrum", button_type="primary"
    )
    generate_powerspectrum_button.on_click(generate_avg_powerspectrum)

    combine_plots_button = pn.widgets.Button(
        name="Combine Selected Plots", button_type="success"
    )
    combine_plots_button.on_click(combine_selected_plots)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab_content = pn.Column(
        event_list_dropdown,
        dt_slider,
        norm_select,
        segment_size_input,
        multi_event_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_powerspectrum_button, show_dataframe_button, combine_plots_button),
    )
    return tab_content


def create_quicklook_avg_powerspectrum_main_area(
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
        "Averaged Power Spectrum": create_avg_powerspectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)


def create_quicklook_avg_powerspectrum_area():
    """
    Create the plots area for the quicklook averaged power spectrum tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the quicklook averaged power spectrum tab.
    """
    return PlotsContainer()
