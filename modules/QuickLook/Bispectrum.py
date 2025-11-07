import panel as pn
import holoviews as hv
from utils.state_manager import state_manager
import pandas as pd
import numpy as np
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


def create_quicklook_bispectrum_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
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
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
):
    
    event_list_dropdown = pn.widgets.Select(
        name="Select Event List",
        options={name: i for i, (name, event) in enumerate(state_manager.get_event_data())},
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
        try:
            event_list = state_manager.get_event_data()[selected_event_index][1]
            # Use `to_lc` for efficient light curve creation
            lc = event_list.to_lc(dt=dt)

            # Create Bispectrum
            bs = Bispectrum(lc, maxlag=maxlag, scale=scale, window=window)
            return bs
        except Exception as e:
            output_box_container[:] = [pn.pane.Markdown(f"Error: {str(e)}")]
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
            output_box_container[:] = [pn.pane.Markdown(f"Visualization Error: {str(e)}")]
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
                event_list = state_manager.get_event_data()[selected_event_list_index][1]

                # Convert EventList to Lightcurve
                lc = event_list.to_lc(dt=dt)

                # Generate the Bispectrum
                bs = Bispectrum(lc, maxlag=maxlag, window=window, scale=scale)

                # Create 2D grids for Frequency and Lags
                freq_grid, lags_grid = np.meshgrid(bs.freq, bs.lags)

                # Flatten grids and corresponding Bispectrum data
                freq_flat = freq_grid.flatten()
                lags_flat = lags_grid.flatten()
                mag_flat = bs.bispec_mag.flatten()
                phase_flat = bs.bispec_phase.flatten()
                cum3_flat = bs.cum3.flatten()

                # Ensure all arrays are of the same length
                if not (
                    len(freq_flat) == len(lags_flat) == len(mag_flat) == len(phase_flat) == len(cum3_flat)
                ):
                    raise ValueError("Inconsistent lengths of Bispectrum data.")

                # Create DataFrame
                df = pd.DataFrame(
                    {
                        "Frequency": freq_flat,
                        "Lags": lags_flat,
                        "Cumulant (Cum3)": cum3_flat,
                        "Magnitude": mag_flat,
                        "Phase": phase_flat,
                    }
                )
                return df, bs
            except Exception as e:
                output_box_container[:] = [
                    create_loadingdata_output_box(f"Error creating dataframe: {e}")
                ]
                return None, None
        return None, None



    """ Float Panel """


    def create_floatpanel_area(content, title):
        return FloatingPlot(content=content, title=title)

    def show_dataframe(event=None):
        if not state_manager.get_event_data():
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

        dt = dt_input.value
        maxlag = maxlag_input.value
        scale = scale_select.value
        window = window_select.value
        df, bs = create_dataframe(selected_event_list_index, dt, maxlag, scale, window)
        if df is not None:
            event_list_name = state_manager.get_event_data()[selected_event_list_index][0]
            dataframe_title = f"{event_list_name} (dt={dt}, maxlag={maxlag}, scale={scale}, window={window})"
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


    def generate_bispectrum(event=None):
        if not state_manager.get_event_data():
            output_box_container[:] = [pn.pane.Markdown("No event data available.")]
            return

        selected_index = event_list_dropdown.value
        if selected_index is None:
            output_box_container[:] = [pn.pane.Markdown("Select an event list.")]
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
                title = f"Bispectrum ({vis_type}) for Event {state_manager.get_event_data()[selected_index][0]}"
                if floatpanel_checkbox.value:
                    float_panel_container.append(FloatingPlot(title=title, content=pane))
                else:
                    plots_container.append(pn.Row(pn.pane.Markdown(f"## {title}"), pane))


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


def create_quicklook_bispectrum_main_area(
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
        "Bispectrum": create_bispectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
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
