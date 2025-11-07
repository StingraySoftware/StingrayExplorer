import panel as pn
import holoviews as hv
import holoviews.operation.datashader as hd
from holoviews.operation.timeseries import rolling, rolling_outlier_std
from utils.state_manager import state_manager
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


""" Main Area Section """


def create_lightcurve_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
):

    event_list_dropdown = pn.widgets.Select(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(state_manager.get_event_data())},
    )

    dt_input = pn.widgets.FloatInput(
        name="Select dt",
        value=1.0,
        step=0.0001,
        start=0.0000000001,  # Prevents negative and zero values
        end=1000.0,
    )

    multi_event_select = pn.widgets.MultiSelect(
        name="Or Select Event List(s) to Combine",
        options={name: i for i, (name, event) in enumerate(state_manager.get_event_data())},
        size=8,
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=True
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )
    rasterize_checkbox = pn.widgets.Checkbox(name="Rasterize Plots", value=True)

    save_lightcurve_checkbox = pn.widgets.Checkbox(
        name="Save Generated Light Curve in RAM", value=False
    )

    time_info_pane = pn.pane.Markdown(
        "Select an event list to see time range", width=600
    )

    gti_input = pn.widgets.TextInput(
        name="Specify GTIs (Good Time Intervals)",
        placeholder="e.g., 0 4; 6 10",
    )

    # Callback to update the time information
    def update_time_info(event):
        selected_index = event_list_dropdown.value
        if selected_index is not None:
            event_list_name = state_manager.get_event_data()[selected_index][0]
            event_list = state_manager.get_event_data()[selected_index][1]
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

    def create_holoviews_plots(df, label, dt, color_key=None):

        plot = df.hvplot(
            x="Time", y="Counts", shared_axes=False, label=f"{label} (dt={dt})"
        )

        if color_key:

            if rasterize_checkbox.value:

                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Counts"),
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
                    plot, aggregator=hd.ds.mean("Counts"), line_width=3, pixel_ratio=2
                ).opts(
                    tools=["hover"],
                    width=600,
                    height=600,
                    colorbar=True,
                    cmap="Viridis",
                )

            else:

                return plot

    def create_holoviews_plots_no_colorbar(df, label, dt, color_key=None):

        plot = df.hvplot(
            x="Time", y="Counts", shared_axes=False, label=f"{label} (dt={dt})"
        )

        if color_key:

            if rasterize_checkbox.value:

                return hd.rasterize(
                    plot,
                    aggregator=hd.ds.mean("Counts"),
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
                    plot, aggregator=hd.ds.mean("Counts"), line_width=3, pixel_ratio=2
                ).opts(
                    tools=["hover"],
                    width=600,
                    height=600,
                    colorbar=False,
                    cmap="Viridis",
                )

            else:

                return plot

    def create_dataframe_panes(df, title, dt):
        return pn.FlexBox(
            pn.pane.Markdown(f"**{title} (dt={dt})**"),
            pn.pane.DataFrame(df, width=600, height=600),
            align_items="center",
            justify_content="center",
            flex_wrap="nowrap",
            flex_direction="column",
        )

    def create_dataframe(selected_event_list_index, dt, eventlist_name):
        if selected_event_list_index is not None:
            event_list = state_manager.get_event_data()[selected_event_list_index][1]


            # Parse GTIs from input if provided
            gti = None
            if gti_input.value:
                try:
                    gti = [
                        [float(start), float(end)]
                        for start, end in (
                            interval.split() for interval in gti_input.value.split(";")
                        )
                    ]
                except ValueError:
                    output_box_container[:] = [
                        create_loadingdata_output_box("Invalid GTI format. Use 'start end; start end'.")
                    ]
                    return None
                
            if gti_input.value:
                lc_new = event_list.to_lc(dt=dt).apply_gtis(gti)
            else:
                lc_new = event_list.to_lc(dt=dt)
            

            lightcurve_name = f"{eventlist_name}_lightcurve"

            # Add the generated light curve to state manager if the checkbox is checked
            if save_lightcurve_checkbox.value:
                state_manager.add_light_curve(lightcurve_name, lc_new)

            df = pd.DataFrame(
                {
                    "Time": lc_new.time,
                    "Counts": lc_new.counts,
                }
            )
            return df
        return None

    """ Floating Plots """

    def create_floating_plot_container(title, content):
        return FloatingPlot(title, content)

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
        df = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            event_list_name = state_manager.get_event_data()[selected_event_list_index][0]
            dataframe_output = create_dataframe_panes(df, f"{event_list_name}", dt)
            if dataframe_checkbox.value:
                float_panel_container.append(
                    create_floating_plot_container(
                        content=dataframe_output,
                        title=f"DataFrame for {event_list_name}",
                    )
                )
            else:
                plots_container.append(dataframe_output)
        else:
            output_box_container[:] = [
                create_loadingdata_output_box("Failed to create dataframe.")
            ]

    def generate_lightcurve(event=None):
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
        df = create_dataframe(
            selected_event_list_index,
            dt,
            state_manager.get_event_data()[selected_event_list_index][0],
        )
        if df is not None:
            event_list_name = state_manager.get_event_data()[selected_event_list_index][0]
            plot_hv = create_holoviews_plots(df, label=event_list_name, dt=dt)
            holoviews_output = create_holoviews_panes(plot=plot_hv)

            if floatpanel_plots_checkbox.value:
                new_floatpanel = create_floating_plot_container(
                    content=holoviews_output, title=event_list_name
                )
                float_panel_container.append(new_floatpanel)
            else:
                markdown_content = f"## {event_list_name}"
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

        # Define a color key for distinct colors
        color_key = {
            index: colors[i % len(colors)]
            for i, index in enumerate(selected_event_list_indices)
        }

        for index in selected_event_list_indices:
            dt = dt_input.value
            df = create_dataframe(index, dt)
            if df is not None:
                event_list_name = state_manager.get_event_data()[index][0]
                plot_hv = create_holoviews_plots_no_colorbar(
                    df, label=event_list_name, dt=dt, color_key=color_key[index]
                )
                combined_plots.append(plot_hv)
                combined_title.append(event_list_name)

        if combined_plots:
            # Use hv.Overlay and add legend manually
            combined_plot = (
                hv.Overlay(combined_plots)
                .opts(shared_axes=False, legend_position="right", width=600, height=600)
                .collate()
            )

            combined_pane = create_holoviews_panes(combined_plot)

            combined_title_str = " + ".join(combined_title)
            if floatpanel_plots_checkbox.value:
                new_floatpanel = create_floating_plot_container(
                    content=combined_pane, title=combined_title_str
                )
                float_panel_container.append(new_floatpanel)
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

    generate_lightcurve_button = pn.widgets.Button(
        name="Generate Light Curve", button_type="primary"
    )
    generate_lightcurve_button.on_click(generate_lightcurve)

    combine_plots_button = pn.widgets.Button(
        name="Combine Selected Plots", button_type="success"
    )
    combine_plots_button.on_click(combine_selected_plots)

    show_dataframe_button = pn.widgets.Button(
        name="Show DataFrame", button_type="primary"
    )
    show_dataframe_button.on_click(show_dataframe)

    event_list_dropdown.param.watch(update_time_info, 'value')


    tab1_content = pn.Column(
        event_list_dropdown,
        time_info_pane, 
        dt_input,
        gti_input,
        multi_event_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        rasterize_checkbox,
        save_lightcurve_checkbox,
        pn.Row(generate_lightcurve_button, show_dataframe_button, combine_plots_button),
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
            float_panel_container=float_panel_container,
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
