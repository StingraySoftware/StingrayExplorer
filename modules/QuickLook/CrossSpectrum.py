import panel as pn
import holoviews as hv
from utils.app_context import AppContext
import pandas as pd
import warnings
import hvplot.pandas
import numpy as np
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
from stingray import Crossspectrum

# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler

""" Header Section """
def create_quicklook_cross_spectrum_header(context: AppContext):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Cross Spectrum"
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
def create_cross_spectrum_tab(
    context: AppContext,
    warning_handler,
):
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

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=False
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600)

    def create_holoviews_plots(cs, event_list_name_1, event_list_name_2, dt, norm):
        label = f"{event_list_name_1} vs {event_list_name_2} (dt={dt}, norm={norm})"
        return hv.Curve((cs.freq, np.abs(cs.power)), label=label).opts(
            xlabel="Frequency (Hz)",
            ylabel="Cross Spectral Amplitude",
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

    def create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm):
        if selected_event_list_index_1 is not None and selected_event_list_index_2 is not None:
            event_list_1 = context.state.get_event_data()[selected_event_list_index_1][1]
            event_list_2 = context.state.get_event_data()[selected_event_list_index_2][1]

            # Use spectrum service to create cross spectrum
            result = context.services.spectrum.create_cross_spectrum(
                event_list_1=event_list_1,
                event_list_2=event_list_2,
                dt=dt,
                norm=norm
            )

            if not result["success"]:
                context.update_container('output_box',
                    create_loadingdata_output_box(f"Error: {result['message']}")
                )
                return None, None

            cs = result["data"]

            # Use export service to convert to DataFrame
            df_result = context.services.export.to_dataframe_cross_spectrum(cs)

            if df_result["success"]:
                return df_result["data"], cs
            else:
                context.update_container('output_box',
                    create_loadingdata_output_box(f"Error: {df_result['message']}")
                )
                return None, None

        return None, None

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
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm)
        if df is not None:
            event_list_name_1 = context.state.get_event_data()[selected_event_list_index_1][0]
            event_list_name_2 = context.state.get_event_data()[selected_event_list_index_2][0]
            dataframe_title = f"{event_list_name_1} vs {event_list_name_2} (dt={dt}, norm={norm})"
            dataframe_output = create_dataframe_panes(df, dataframe_title)
            if dataframe_checkbox.value:
                context.append_to_container('float_panel',
                    create_floatpanel_area(
                        content=dataframe_output,
                        title=f"DataFrame for {dataframe_title}",
                    )
                )
            else:
                context.append_to_container('plots', dataframe_output)
        else:
            context.update_container('output_box',
                create_loadingdata_output_box("Failed to create dataframe.")
            )

    def generate_cross_spectrum(event=None):
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
        df, cs = create_dataframe(selected_event_list_index_1, selected_event_list_index_2, dt, norm)
        if df is not None:
            event_list_name_1 = context.state.get_event_data()[selected_event_list_index_1][0]
            event_list_name_2 = context.state.get_event_data()[selected_event_list_index_2][0]
            plot_hv = create_holoviews_plots(cs, event_list_name_1, event_list_name_2, dt, norm)
            holoviews_output = create_holoviews_panes(plot_hv)

            if floatpanel_plots_checkbox.value:
                context.append_to_container('float_panel',
                    create_floatpanel_area(
                        content=holoviews_output, title=f"Cross Spectrum for {event_list_name_1} vs {event_list_name_2} (dt={dt}, norm={norm})"
                    )
                )
            else:
                markdown_content = f"## Cross Spectrum for {event_list_name_1} vs {event_list_name_2} (dt={dt}, norm={norm})"
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
        else:
            context.update_container('output_box',
                create_loadingdata_output_box("Failed to create cross spectrum.")
            )

    generate_cross_spectrum_button = pn.widgets.Button(
        name="Generate Cross Spectrum", button_type="primary"
    )
    generate_cross_spectrum_button.on_click(generate_cross_spectrum)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab_content = pn.Column(
        event_list_dropdown_1,
        event_list_dropdown_2,
        dt_slider,
        norm_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_cross_spectrum_button, show_dataframe_button),
    )
    return tab_content

def create_quicklook_cross_spectrum_main_area(context: AppContext):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Cross Spectrum": create_cross_spectrum_tab(
            context=context,
            warning_handler=warning_handler,
        ),
    }

    return MainArea(tabs_content=tabs_content)

def create_quicklook_cross_spectrum_area():
    return PlotsContainer()
