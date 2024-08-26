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
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
    )

    dt_slider = pn.widgets.FloatSlider(
        name="Select dt",
        start=0.1,
        end=1000,
        step=0.1,
        value=1,
    )

    # tstart_input = pn.widgets.FloatInput(
    #     name="Start Time (tstart)",
    #     value=None,
    #     step=0.1,
    # )

    multi_event_select = pn.widgets.MultiSelect(
        name="Or Select Event List(s) to Combine",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
        size=8,
    )

    # combine_plots_checkbox = pn.widgets.Checkbox(
    #     name="Combine with Existing Plot", value=False
    # )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=False
    )

    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    # floating_plot_titles = []
    # plots_container_titles = []

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600)

    def create_holoviews_plots(df, label, dt):
        return df.hvplot(x="Time", y="Counts", shared_axes=False, label=f"{label} (dt={dt})")

    def create_dataframe_panes(df, title, dt):
        return pn.FlexBox(
            pn.pane.Markdown(f"**{title} (dt={dt})**"),
            pn.pane.DataFrame(df, width=600, height=600),
            align_items="center",
            justify_content="center",
            flex_wrap="nowrap",
            flex_direction="column",
        )

    def create_dataframe(selected_event_list_index, dt):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]
            lc_new = event_list.to_lc(dt=dt)

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
        df = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            # Get the title
            event_list_name = loaded_event_data[selected_event_list_index][0]
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
        df = create_dataframe(selected_event_list_index, dt)
        if df is not None:
            # Get the title
            event_list_name = loaded_event_data[selected_event_list_index][0]
            plot_hv = create_holoviews_plots(df, label=event_list_name, dt=dt)
            holoviews_output = create_holoviews_panes(plot=plot_hv)

            # Handle case when plots are not combined
            if floatpanel_plots_checkbox.value:

                # Add title to the list of floating plot titles
                # floating_plot_titles.append(event_list_name)
                # Create a new FloatPanel for each independent plot
                new_floatpanel = create_floating_plot_container(
                    content=holoviews_output, title=event_list_name
                )
                float_panel_container.append(new_floatpanel)
            else:
                # Add title to the list of plots container titles
                # plots_container_titles.append(event_list_name)
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

        for index in selected_event_list_indices:
            dt = dt_slider.value
            df = create_dataframe(index, dt)
            if df is not None:
                event_list_name = loaded_event_data[index][0]
                plot_hv = create_holoviews_plots(df, label=event_list_name, dt=dt)
                combined_plots.append(plot_hv)
                combined_title.append(event_list_name)

        if combined_plots:
            combined_plot = hv.Overlay(combined_plots).opts(shared_axes=False)
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

        # if not combine_plots_checkbox.value:
        #     # Handle case when plots are not combined
        #     if floatpanel_plots_checkbox.value:

        #         # Add title to the list of floating plot titles
        #         floating_plot_titles.append(event_list_name)
        #         # Create a new FloatPanel for each independent plot
        #         new_floatpanel = create_floating_plot_container(
        #             content=holoviews_output, title=event_list_name
        #         )
        #         float_panel_container.append(new_floatpanel)
        #     else:
        #         # Add title to the list of plots container titles
        #         plots_container_titles.append(event_list_name)
        #         plots_container.append(holoviews_output)
        # else:
        #     # Handle case when plots are combined
        #     if floatpanel_plots_checkbox.value:
        #         existing_floating_panels = [
        #             p.object
        #             for p in float_panel_container
        #             if isinstance(p, pn.pane.HoloViews)
        #         ]
        #         combined_plot = hv.Overlay(
        #             existing_floating_panels + [plot_hv]
        #         )
        #         combined_pane = create_holoviews_panes(combined_plot)

        #         combined_title = " + ".join(
        #             floating_plot_titles + [event_list_name]
        #         )
        #         floating_plot_titles.append(event_list_name)
        #         new_floatpanel = create_floating_plot_container(
        #             content=combined_pane, title=combined_title
        #         )
        #         float_panel_container.append(new_floatpanel)
        #     else:
        #         existing_plots = [
        #             p.object
        #             for p in plots_container
        #             if isinstance(p, pn.pane.HoloViews)
        #         ]
        #         combined_plot = hv.Overlay(existing_plots + [plot_hv])

        #         combined_pane = create_holoviews_panes(combined_plot)

        #         plots_container.append(combined_pane)

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

    tab1_content = pn.Column(
        event_list_dropdown,
        dt_slider,
        multi_event_select,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
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
