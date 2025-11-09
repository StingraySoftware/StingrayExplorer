import panel as pn
import holoviews as hv
from utils.app_context import AppContext
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
def create_quicklook_avg_cross_spectrum_header(context: AppContext):
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
    context: AppContext,
    warning_handler,
):
    # Define Widgets
    event_list_dropdown_1 = pn.widgets.Select(
        name="Select Event List 1",
        options={name: i for i, (name, event) in enumerate(context.state.get_event_data())},
    )

    event_list_dropdown_2 = pn.widgets.Select(
        name="Select Event List 2",
        options={name: i for i, (name, event) in enumerate(context.state.get_event_data())},
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
            event_list_1 = context.state.get_event_data()[selected_event_list_index_1][1]
            event_list_2 = context.state.get_event_data()[selected_event_list_index_2][1]

            # Use spectrum service to create averaged cross spectrum
            result = context.services.spectrum.create_averaged_cross_spectrum(
                event_list_1=event_list_1,
                event_list_2=event_list_2,
                dt=dt,
                segment_size=segment_size,
                norm=norm
            )

            if not result["success"]:
                context.update_container('output_box',
                    create_loadingdata_output_box(f"Error: {result['message']}")
                )
                return None, None

            cs = result["data"]

            # Create DataFrame manually (cross spectrum has complex power)
            df = pd.DataFrame({
                "Frequency": cs.freq,
                "Cross Power": np.abs(cs.power),
            })

            return df, cs
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
        if not context.state.get_event_data():
            context.update_container('output_box',
                create_loadingdata_output_box("No loaded event data available.")
            )
            return

        selected_event_list_index_1 = event_list_dropdown_1.value
        selected_event_list_index_2 = event_list_dropdown_2.value
        if selected_event_list_index_1 is None or selected_event_list_index_2 is None:
            context.update_container('output_box',
                create_loadingdata_output_box("Both event lists must be selected.")
            )
            return

        dt = dt_slider.value
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm, segment_size)
        if df is not None:
            plot_title = f"Averaged Cross Spectrum for {context.state.get_event_data()[selected_event_list_index_1][0]} vs {context.state.get_event_data()[selected_event_list_index_2][0]}"
            plot_hv = create_holoviews_plots(cs, title=plot_title, dt=dt, norm=norm, segment_size=segment_size)
            holoviews_output = create_holoviews_panes(plot_hv)

            if floatpanel_plots_checkbox.value:
                context.append_to_container('float_panel',
                    create_floatpanel_area(
                        content=holoviews_output, title=plot_title
                    )
                )
            else:
                markdown_content = f"## {plot_title}"
                context.append_to_container('plots',
                    pn.FlexBox(
                        pn.pane.Markdown(markdown_content),
                        holoviews_output,
                        align_items="center",
                        justify_content="center",
                        flex_wrap="nowrap",
                        flex_direction="column",
                    )
                )
            context.update_container('output_box',
                create_loadingdata_output_box("Averaged Cross Spectrum generated successfully.")
            )
        else:
            context.update_container('output_box',
                create_loadingdata_output_box("Failed to create averaged cross spectrum.")
            )

    def show_dataframe(event=None):
        if not context.state.get_event_data():
            context.update_container('output_box',
                create_loadingdata_output_box("No loaded event data available.")
            )
            return

        selected_event_list_index_1 = event_list_dropdown_1.value
        selected_event_list_index_2 = event_list_dropdown_2.value
        if selected_event_list_index_1 is None or selected_event_list_index_2 is None:
            context.update_container('output_box',
                create_loadingdata_output_box("Both event lists must be selected.")
            )
            return

        dt = dt_slider.value
        norm = norm_select.value
        segment_size = segment_size_input.value
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm, segment_size)
        if df is not None:
            dataframe_output = create_dataframe_panes(df, f"{context.state.get_event_data()[selected_event_list_index_1][0]} vs {context.state.get_event_data()[selected_event_list_index_2][0]}", dt, norm, segment_size)
            if dataframe_checkbox.value:
                context.append_to_container('float_panel',
                    create_floatpanel_area(
                        content=dataframe_output,
                        title=f"DataFrame for {context.state.get_event_data()[selected_event_list_index_1][0]} vs {context.state.get_event_data()[selected_event_list_index_2][0]}",
                    )
                )
            else:
                context.append_to_container('plots', dataframe_output)
            context.update_container('output_box',
                create_loadingdata_output_box("DataFrame generated successfully.")
            )
        else:
            context.update_container('output_box',
                create_loadingdata_output_box("Failed to create dataframe.")
            )

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

def create_quicklook_avg_cross_spectrum_main_area(context: AppContext):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Averaged Cross Spectrum": create_avg_cross_spectrum_tab(
            context=context,
            warning_handler=warning_handler,
        ),
    }

    return MainArea(tabs_content=tabs_content)

def create_quicklook_avg_cross_spectrum_area():
    return PlotsContainer()
