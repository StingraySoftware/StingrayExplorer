import panel as pn
import holoviews as hv
from utils.app_context import AppContext
from utils.error_handler import ErrorHandler
import pandas as pd
import numpy as np
import logging
import warnings
import hvplot.pandas
from stingray.bispectrum import Bispectrum
from stingray import Lightcurve
import matplotlib.pyplot as plt
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

colors = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
    "#c49c94",
    "#f7b6d2",
    "#c7c7c7",
    "#dbdb8d",
    "#9edae5",
]

windows = [
    "uniform", "parzen", "hamming", "hanning", "triangular", 
    "blackmann", "welch", "flat-top"
]


# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler


""" Header Section """


def create_quicklook_bispectrum_header(context: AppContext):
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="Bispectrum"
    )
    home_subheading_input = pn.widgets.TextInput(name="Subheading", value="")

    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)


""" Output Box Section """


def create_loadingdata_output_box(content):
    return OutputBox(output_content=content)


""" Warning Box Section """


def create_loadingdata_warning_box(content):
    return WarningBox(warning_content=content)


""" Main Area Section """


def create_bispectrum_tab(
    context: AppContext,
    warning_handler,
):

    event_list_dropdown = pn.widgets.Select(
        name="Select Event List",
        options={name: i for i, (name, event) in enumerate(context.state.get_event_data())},
    )
    dt_input = pn.widgets.FloatInput(name="Select dt", value=1.0, step=0.0001, start=0.0001, end=1000.0)
    maxlag_input = pn.widgets.IntInput(name="Max Lag", value=25, step=1, start=1, end=100)
    scale_select = pn.widgets.Select(name="Scale", options=["biased", "unbiased"], value="unbiased")
    window_select = pn.widgets.Select(name="Window Type", options=windows, value=windows[0])
    visualization_select = pn.widgets.Select(name="Visualization", options=["Cumulant", "Magnitude", "Phase"], value="Magnitude")

    floatpanel_checkbox = pn.widgets.Checkbox(name="Add Plot to FloatingPanel", value=True)

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )
    
    def create_bispectrum(selected_event_index, dt, maxlag, scale, window):
        event_list = context.state.get_event_data()[selected_event_index][1]

        # Use timing service to create bispectrum
        result = context.services.timing.create_bispectrum(
            event_list=event_list,
            dt=dt,
            maxlag=maxlag,
            scale=scale,
            window=window
        )

        if result["success"]:
            return result["data"]
        else:
            context.update_container('output_box', pn.pane.Markdown(f"Error: {result['message']}"))
            return None


    def visualize_bispectrum(bs, vis_type):
        try:
            import matplotlib.pyplot as plt

            # Create a new figure for each plot to avoid reusing the same one
            plt.figure()

            if vis_type == "Cumulant":
                bs.plot_cum3()  # This directly plots on the current figure
            elif vis_type == "Magnitude":
                bs.plot_mag()  # This directly plots on the current figure
            elif vis_type == "Phase":
                bs.plot_phase()  # This directly plots on the current figure
            else:
                return None

            # Retrieve the current figure
            fig = plt.gcf()  # Get the current figure
            return pn.pane.Matplotlib(fig, width=600, height=600)

        except Exception as e:
            user_msg, tech_msg = ErrorHandler.handle_error(
                e,
                context="Visualizing bispectrum",
                visualization_type=vis_type
            )
            context.update_container('output_box', pn.pane.Markdown(f"Visualization Error: {user_msg}"))
            return None



        
        
        
    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600, linked_axes=False)

    def create_holoviews_plots(df, label, dt, window, scale, color_key=None):
        plot = df.hvplot(x="Frequency", y="Magnitude", shared_axes=False, label=label)
        return plot.opts(tools=['hover'], cmap=[color_key] if color_key else "viridis")

    def create_dataframe_panes(df, title):
        return pn.FlexBox(
            pn.pane.Markdown(f"**{title}**"),
            pn.pane.DataFrame(df, width=600, height=600),
            align_items="center",
            justify_content="center",
            flex_wrap="nowrap",
            flex_direction="column",
        )

    def create_dataframe(selected_event_list_index, dt, maxlag, scale, window):
        if selected_event_list_index is not None:
            try:
                # Fetch the selected EventList
                event_list = context.state.get_event_data()[selected_event_list_index][1]

                # Use timing service to create bispectrum
                result = context.services.timing.create_bispectrum(
                    event_list=event_list,
                    dt=dt,
                    maxlag=maxlag,
                    scale=scale,
                    window=window
                )

                if not result["success"]:
                    context.update_container('output_box',
                        create_loadingdata_output_box(f"Error: {result['message']}")
                    )
                    return None, None

                bs = result["data"]

                # Use export service to convert to DataFrame
                df_result = context.services.export.to_dataframe_bispectrum(bs)

                if df_result["success"]:
                    return df_result["data"], bs
                else:
                    context.update_container('output_box',
                        create_loadingdata_output_box(f"Error: {df_result['message']}")
                    )
                    return None, None
            except Exception as e:
                user_msg, tech_msg = ErrorHandler.handle_error(
                    e,
                    context="Creating bispectrum dataframe",
                    dt=dt,
                    maxlag=maxlag,
                    scale=scale,
                    window=window
                )
                context.update_container('output_box',
                    create_loadingdata_output_box(f"Error: {user_msg}")
                )
                return None, None
        return None, None



    """ Float Panel """


    def create_floatpanel_area(content, title):
        return FloatingPlot(content=content, title=title)

    def show_dataframe(event=None):
        if not context.state.get_event_data():
            context.update_container('output_box',
                create_loadingdata_output_box("No loaded event data available.")
            )
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            context.update_container('output_box',
                create_loadingdata_output_box("No event list selected.")
            )
            return

        dt = dt_input.value
        maxlag = maxlag_input.value
        scale = scale_select.value
        window = window_select.value
        df, bs = create_dataframe(selected_event_list_index, dt, maxlag, scale, window)
        if df is not None:
            event_list_name = context.state.get_event_data()[selected_event_list_index][0]
            dataframe_title = f"{event_list_name} (dt={dt}, maxlag={maxlag}, scale={scale}, window={window})"
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


    def generate_bispectrum(event=None):
        if not context.state.get_event_data():
            context.update_container('output_box', pn.pane.Markdown("No event data available."))
            return

        selected_index = event_list_dropdown.value
        if selected_index is None:
            context.update_container('output_box', pn.pane.Markdown("Select an event list."))
            return

        dt = dt_input.value
        maxlag = maxlag_input.value
        scale = scale_select.value
        window = window_select.value
        vis_type = visualization_select.value

        bs = create_bispectrum(selected_index, dt, maxlag, scale, window)
        if bs:
            pane = visualize_bispectrum(bs, vis_type)
            if pane:
                title = f"Bispectrum ({vis_type}) for Event {context.state.get_event_data()[selected_index][0]}"
                if floatpanel_checkbox.value:
                    context.append_to_container('float_panel', FloatingPlot(title=title, content=pane))
                else:
                    context.append_to_container('plots', pn.Row(pn.pane.Markdown(f"## {title}"), pane))


    generate_bispectrum_button = pn.widgets.Button(
        name="Generate Bispectrum", button_type="primary"
    )
    generate_bispectrum_button.on_click(generate_bispectrum)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    tab1_content = pn.Column(
        event_list_dropdown,
        dt_input,
        maxlag_input,
        scale_select,
        window_select,
        visualization_select,
        floatpanel_checkbox,
        dataframe_checkbox,
        pn.Row(generate_bispectrum_button, show_dataframe_button),
    )
    return tab1_content


def create_quicklook_bispectrum_main_area(context: AppContext):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Bispectrum": create_bispectrum_tab(
            context=context,
            warning_handler=warning_handler,
        ),
    }

    return MainArea(tabs_content=tabs_content)


def create_quicklook_bispectrum_area():
    """
    Create the plots area for the quicklook bispectrum tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the quicklook bispectrum tab.
    """
    return PlotsContainer()
