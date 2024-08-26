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
    return FloatingPlot(content=content, title=title)


""" Main Area Section """


def create_powerspectrum_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
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

    norm_select = pn.widgets.Select(
        name="Normalization",
        options=["frac", "leahy", "abs", "none"],
        value="leahy",
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

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600)

    def create_holoviews_plots(ps, event_list_name, dt, norm):
        label = f"{event_list_name} (dt={dt}, norm={norm})"
        return hv.Curve((ps.freq, ps.power), label=label).opts(
            xlabel="Frequency (Hz)",
            ylabel="Power",
            title=label,
            width=600,
            height=600,
            shared_axes=False,
        )

    def create_dataframe_panes(df, title):
        return pn.FlexBox(
            pn.pane.Markdown(f"**{title}**"),
            pn.pane.DataFrame(df, width=600, height=600),
            align_items="center",
            justify_content="center",
            flex_wrap="nowrap",
            flex_direction="column",
        )

    def create_dataframe(selected_event_list_index, dt, norm):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]

            # Create a PowerSpectrum object using from_events
            ps = Powerspectrum.from_events(events=event_list, dt=dt, norm=norm)

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
        norm = norm_select.value
        df, ps = create_dataframe(selected_event_list_index, dt, norm)
        if df is not None:
            event_list_name = loaded_event_data[selected_event_list_index][0]
            dataframe_title = f"{event_list_name} (dt={dt}, norm={norm})"
            dataframe_output = create_dataframe_panes(df, dataframe_title)
            if dataframe_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=dataframe_output,
                        title=f"DataFrame for {dataframe_title}",
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
        norm = norm_select.value
        df, ps = create_dataframe(selected_event_list_index, dt, norm)
        if df is not None:
            event_list_name = loaded_event_data[selected_event_list_index][0]
            plot_hv = create_holoviews_plots(ps, event_list_name, dt, norm)
            holoviews_output = create_holoviews_panes(plot_hv)

            if floatpanel_plots_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=holoviews_output, title=f"Power Spectrum for {event_list_name} (dt={dt}, norm={norm})"
                    )
                )
            else:
                markdown_content = f"## Power Spectrum for {event_list_name} (dt={dt}, norm={norm})"
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
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create power spectrum.")
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
            df, ps = create_dataframe(index, dt, norm)
            if df is not None:
                event_list_name = loaded_event_data[index][0]
                plot_hv = create_holoviews_plots(ps, event_list_name, dt, norm)
                combined_plots.append(plot_hv)
                combined_title.append(event_list_name)

        if combined_plots:
            combined_plot = hv.Overlay(combined_plots).opts(shared_axes=False)
            combined_pane = create_holoviews_panes(combined_plot)

            combined_title_str = " + ".join(combined_title)
            combined_title_str += f" (dt={dt}, norm={norm})"
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

    generate_powerspectrum_button = pn.widgets.Button(
        name="Generate Power Spectrum", button_type="primary"
    )
    generate_powerspectrum_button.on_click(generate_powerspectrum)

    combine_plots_button = pn.widgets.Button(
        name="Combine Selected Plots", button_type="success"
    )
    combine_plots_button.on_click(combine_selected_plots)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab1_content = pn.Column(
        event_list_dropdown,
        dt_slider,
        norm_select,
        multi_event_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_powerspectrum_button, show_dataframe_button, combine_plots_button),
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
    float_panel_container,
):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Power Spectrum": create_powerspectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)


def create_quicklook_powerspectrum_area():
    """
    Create the plots area for the quicklook lightcurve tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the quicklook lightcurve tab.
    """
    return PlotsContainer()
