import panel as pn
import holoviews as hv
from stingray import DynamicalPowerspectrum
from stingray.power_colors import (
    hue_from_power_color,
    plot_power_colors,
    plot_hues,
    DEFAULT_COLOR_CONFIGURATION,
)
from utils.globals import loaded_event_data
import warnings
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
def create_quicklook_powercolors_header(
    header_container, main_area_container, output_box_container, warning_box_container, plots_container, help_box_container, footer_container, float_panel_container
):
    header_input = pn.widgets.TextInput(name="Heading", value="QuickLook Power Colors")
    return MainHeader(heading=header_input)

""" Output Box Section """
def create_loadingdata_output_box(content):
    return OutputBox(output_content=content)

""" Warning Box Section """
def create_loadingdata_warning_box(content):
    return WarningBox(warning_content=content)

""" Main Area Section """
def create_powercolors_tab(output_box_container, warning_box_container, warning_handler, plots_container, header_container, float_panel_container):
    event_list_dropdown = pn.widgets.Select(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
    )

    segment_size_input = pn.widgets.IntInput(name="Segment Size", value=256, step=1)

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600, linked_axes=False)

    def generate_powercolors(event=None):
        if not loaded_event_data:
            output_box_container[:] = [pn.pane.Markdown("No loaded event data available.")]
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            output_box_container[:] = [pn.pane.Markdown("No event list selected.")]
            return

        # Convert EventList to LightCurve
        event_list = loaded_event_data[selected_event_list_index][1]
        lightcurve = event_list.to_lc(dt=1 / 256)  # Adjust dt value as needed

        segment_size = segment_size_input.value
        dynps = DynamicalPowerspectrum(
            data=lightcurve,
            segment_size=segment_size,
            sample_time=1 / segment_size,
            norm="leahy",
        )

        dynps_reb = dynps.rebin_by_n_intervals(2, method="average")

        # Calculate power colors
        p1, p1e, p2, p2e = dynps_reb.power_colors(
            freq_edges=[1 / 256, 1 / 32, 0.25, 2, 16]
        )

        # Calculate hues from power colors
        hues = hue_from_power_color(p1, p2)

        # Plot power colors
        configuration = DEFAULT_COLOR_CONFIGURATION
        power_colors_plot = plot_power_colors(p1, p1e, p2, p2e, plot_spans=True, configuration=configuration)
        hues_plot = plot_hues(hues, p1, p2, plot_spans=True, configuration=configuration)

        # Create HoloViews pane for display
        power_colors_hv = create_holoviews_panes(power_colors_plot)
        hues_hv = create_holoviews_panes(hues_plot)

        # Add to floating panel or main area
        float_panel_container.append(
            FloatingPlot(title="Power Colors", content=power_colors_hv)
        )
        plots_container.append(hues_hv)

    generate_powercolors_button = pn.widgets.Button(name="Generate Power Colors", button_type="primary")
    generate_powercolors_button.on_click(generate_powercolors)

    tab_content = pn.Column(
        event_list_dropdown,
        segment_size_input,
        pn.Row(generate_powercolors_button),
    )
    return tab_content

def create_quicklook_powercolors_main_area(
    header_container, main_area_container, output_box_container, warning_box_container, plots_container, help_box_container, footer_container, float_panel_container
):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Power Colors": create_powercolors_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
        ),
    }
    return MainArea(tabs_content=tabs_content)

def create_quicklook_powercolors_area():
    """
    Create the plots area for the quicklook power colors tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the quicklook power colors tab.
    """
    return PlotsContainer()
