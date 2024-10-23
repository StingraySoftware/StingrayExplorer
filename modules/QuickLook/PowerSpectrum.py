import panel as pn
import holoviews as hv
from utils.globals import loaded_event_data
import pandas as pd
import warnings
import holoviews.operation.datashader as hd
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

    dt_input = pn.widgets.FloatInput(
        name="Select dt",
        value=1.0,
        step=0.0001,
        start=0.0000000001,  # Prevents negative and zero values
        end=1000.0,
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
        name="Add Plot to FloatingPanel", value=True
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )
    
    rasterize_checkbox = pn.widgets.Checkbox(name="Rasterize Plots", value=True)

    time_info_pane = pn.pane.Markdown(
    "Select an event list to see time range", width=600
    )

    
    # New Checkboxes for Rebinning
    linear_rebin_checkbox = pn.widgets.Checkbox(name="Linear Rebinning", value=False)
    log_rebin_checkbox = pn.widgets.Checkbox(name="Logarithmic Rebinning", value=False)
    rebin_with_original_checkbox = pn.widgets.Checkbox(name="Plot Rebin with Original", value=False)

    # Input for Rebin Size
    rebin_size_input = pn.widgets.FloatInput(
        name="Rebin Size",
        value=0.1,
        step=0.000001,
        start=0.01,
        end=1000.0,
    )

    def update_time_info(event):
        selected_index = event_list_dropdown.value
        if selected_index is not None:
            event_list_name = loaded_event_data[selected_index][0]
            event_list = loaded_event_data[selected_index][1]
            start_time = event_list.time[0]
            end_time = event_list.time[-1]
            time_info_pane.object = (
                f"**Event List:** {event_list_name} \n"
                f"**Start Time:** {start_time} \n"
                f"**End Time:** {end_time}"
            )
        else:
            time_info_pane.object = "Select an event list to see time range"


    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600, linked_axes=False)

    def create_holoviews_plots(df, label, dt, norm, color_key=None):
        plot = df.hvplot(x="Frequency", y="Power", shared_axes=False, label=label)

        if color_key:
            if rasterize_checkbox.value:
                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Power"),
                    color_key=color_key,
                    line_width=3,
                    pixel_ratio=2,
                ).opts(
                    tools=["hover"],
                    cmap=[color_key],
                    width=600,
                    height=600,
                    colorbar=True,
                )
            else:
                return plot
        else:
            if rasterize_checkbox.value:
                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Power"),
                    line_width=3,
                    pixel_ratio=2,
                ).opts(
                    tools=["hover"],
                    width=600,
                    height=600,
                    cmap="Viridis",
                    colorbar=True,
                )
            else:
                return plot

    def create_holoviews_plots_no_colorbar(df, label, dt, norm, color_key=None):
        plot = df.hvplot(x="Frequency", y="Power", shared_axes=False, label=label)

        if color_key:
            if rasterize_checkbox.value:
                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Power"),
                    color_key=color_key,
                    line_width=3,
                    pixel_ratio=2,
                ).opts(
                    tools=["hover"],
                    cmap=[color_key],
                    width=600,
                    height=600,
                    colorbar=False,
                )
            else:
                return plot
        else:
            if rasterize_checkbox.value:
                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Power"),
                    line_width=3,
                    pixel_ratio=2,
                ).opts(
                    tools=["hover"],
                    width=600,
                    height=600,
                    colorbar=False,
                    cmap="Viridis",
                )
            else:
                return plot

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

    """ Rebin Functionality """

    def rebin_powerspectrum(ps):
        rebin_size = rebin_size_input.value
        
        if linear_rebin_checkbox.value:
            # Perform linear rebinning
            rebinned_ps = ps.rebin(rebin_size, method="mean")
            return rebinned_ps
        elif log_rebin_checkbox.value:
            # Perform logarithmic rebinning
            rebinned_ps = ps.rebin_log(f=rebin_size)
            return rebinned_ps
        return None

    """ Float Panel """

    def create_floatpanel_area(content, title):
        return FloatingPlot(content=content, title=title)

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

        dt = dt_input.value
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

        dt = dt_input.value
        norm = norm_select.value
        df, ps = create_dataframe(selected_event_list_index, dt, norm)
        
        if df is not None:
            event_list_name = loaded_event_data[selected_event_list_index][0]
            label = f"{event_list_name} (dt={dt}, norm={norm})"
            
            # Create the original plot
            original_plot_hv = create_holoviews_plots(df, label, dt, norm)

            # Initialize the holoviews_output variable
            holoviews_output = original_plot_hv
            
            # Rebin the powerspectrum if requested
            rebinned_ps = rebin_powerspectrum(ps)
            
            if rebinned_ps is not None:
                # Create a DataFrame for the rebinned plot
                rebinned_df = pd.DataFrame({
                    "Frequency": rebinned_ps.freq,
                    "Power": rebinned_ps.power,
                })
                rebinned_label = f"Rebinned {event_list_name} (dt={dt}, norm={norm})"
                rebinned_plot_hv = create_holoviews_plots(rebinned_df, rebinned_label, dt, norm)

                # Check if the user wants to plot rebin with the original
                if rebin_with_original_checkbox.value:
                    # Combine the original and rebinned plots using HoloViews
                    holoviews_output = original_plot_hv * rebinned_plot_hv
                else:
                    # Only use the rebinned plot
                    holoviews_output = rebinned_plot_hv

            # Convert the combined HoloViews object to a pane
            holoviews_output_pane = create_holoviews_panes(holoviews_output)

            # Append the pane to the appropriate container
            if floatpanel_plots_checkbox.value:
                float_panel_container.append(
                    create_floatpanel_area(
                        content=holoviews_output_pane,
                        title=f"Power Spectrum for {event_list_name} (dt={dt}, norm={norm})",
                    )
                )
            else:
                markdown_content = (
                    f"## Power Spectrum for {event_list_name} (dt={dt}, norm={norm})"
                )
                plots_container.append(
                    pn.FlexBox(
                        pn.pane.Markdown(markdown_content),
                        holoviews_output_pane,
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

        # Define a color key for distinct colors
        color_key = {
            index: colors[i % len(colors)]
            for i, index in enumerate(selected_event_list_indices)
        }

        for index in selected_event_list_indices:
            dt = dt_input.value
            norm = norm_select.value
            df, ps = create_dataframe(index, dt, norm)
            if df is not None:
                event_list_name = loaded_event_data[index][0]

                label = f"{event_list_name} (dt={dt}, norm={norm})"
                plot_hv = create_holoviews_plots_no_colorbar(
                    df, label, dt, norm, color_key=color_key[index]
                )
                combined_plots.append(plot_hv)
                combined_title.append(event_list_name)

        if combined_plots:
            combined_plot = (
                hv.Overlay(combined_plots)
                .opts(shared_axes=False, legend_position="right", width=600, height=600)
                .collate()
            )

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

    event_list_dropdown.param.watch(update_time_info, 'value')


    tab_content = pn.Column(
        event_list_dropdown,
        time_info_pane, 
        dt_input,
        norm_select,
        multi_event_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        rasterize_checkbox,
        linear_rebin_checkbox,
        log_rebin_checkbox,
        rebin_with_original_checkbox,
        rebin_size_input,
        pn.Row(generate_powerspectrum_button, show_dataframe_button, combine_plots_button),
    )
    return tab_content

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
