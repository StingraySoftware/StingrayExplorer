import panel as pn
import holoviews as hv
from stingray import DynamicalPowerspectrum
from stingray.power_colors import (
    hue_from_power_color,
    plot_power_colors,
    plot_hues,
    DEFAULT_COLOR_CONFIGURATION,
)
from utils.app_context import AppContext
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
def create_quicklook_powercolors_header(context: AppContext):
    header_input = pn.widgets.TextInput(name="Heading", value="QuickLook Power Colors")
    return MainHeader(heading=header_input)

""" Output Box Section """
def create_loadingdata_output_box(content):
    return OutputBox(output_content=content)

""" Warning Box Section """
def create_loadingdata_warning_box(content):
    return WarningBox(warning_content=content)

""" Main Area Section """
def create_powercolors_tab(
    context: AppContext,
    warning_handler,
):
    event_list_dropdown = pn.widgets.Select(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(context.state.get_event_data())},
    )

    segment_size_input = pn.widgets.IntInput(name="Segment Size", value=256, step=1)
    rebin_intervals_input = pn.widgets.IntInput(name="Rebin Intervals", value=2, step=1)

    def generate_powercolors(event=None):
        if not context.state.get_event_data():
            context.update_container('warning_box',
                create_loadingdata_warning_box("No loaded event data available.")
            )
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            context.update_container('warning_box',
                create_loadingdata_warning_box("No event list selected.")
            )
            return

        try:
            # Get EventList and create DynamicalPowerspectrum using service
            event_list = context.state.get_event_data()[selected_event_list_index][1]
            segment_size = segment_size_input.value

            # Use spectrum service to create dynamical power spectrum
            result = context.services.spectrum.create_dynamical_power_spectrum(
                event_list=event_list,
                dt=1 / 256,
                segment_size=segment_size,
                norm="leahy"
            )

            if not result["success"]:
                context.update_container('warning_box',
                    create_loadingdata_warning_box(f"Error: {result['message']}")
                )
                return

            dynps = result["data"]

            # Rebin the dynamical power spectrum
            rebin_intervals = rebin_intervals_input.value
            dynps_reb = dynps.rebin_by_n_intervals(rebin_intervals, method="average")

            # Calculate power colors
            freq_edges = [1 / 256, 1 / 32, 0.25, 2, 16]
            p1, p1e, p2, p2e = dynps_reb.power_colors(freq_edges=freq_edges)

            # Calculate hues from power colors
            hues = hue_from_power_color(p1, p2)

            # Calculate fractional rms
            poisson_noise_level = 2.0  # Adjust this as necessary
            rms, rmse = dynps_reb.compute_rms(
                min_freq=1 / 64, max_freq=16, poisson_noise_level=poisson_noise_level
            )

            # Plot configurations
            configuration = DEFAULT_COLOR_CONFIGURATION

            # Plot power colors
            fig1 = plot_power_colors(p1, p1e, p2, p2e, plot_spans=True, configuration=configuration)
            fig1.tight_layout()
            power_colors_plot = pn.pane.Matplotlib(fig1, width=600, height=400)

            # Plot hues
            fig2 = plot_hues(rms, rmse, p1, p2, plot_spans=True, configuration=configuration)
            fig2.tight_layout()
            hues_plot = pn.pane.Matplotlib(fig2, width=600, height=400)

            # Plot polar plot for hue and rms
            fig3 = plot_hues(
                rms, rmse, p1, p2, polar=True, plot_spans=True, configuration=configuration
            )
            fig3.tight_layout()
            polar_plot = pn.pane.Matplotlib(fig3, width=600, height=400)

            # Add to floating panel or main plot area
            context.append_to_container('float_panel',
                FloatingPlot(title="Power Colors", content=power_colors_plot)
            )
            context.append_to_container('float_panel',
                FloatingPlot(title="Hues", content=hues_plot)
            )
            context.append_to_container('float_panel',
                FloatingPlot(title="Polar Plot", content=polar_plot)
            )
        except Exception as e:
            context.update_container('warning_box',
                create_loadingdata_warning_box(f"Error: {str(e)}")
            )

    generate_powercolors_button = pn.widgets.Button(
        name="Generate Power Colors", button_type="primary"
    )
    generate_powercolors_button.on_click(generate_powercolors)

    tab_content = pn.Column(
        event_list_dropdown,
        segment_size_input,
        rebin_intervals_input,
        pn.Row(generate_powercolors_button),
    )
    return tab_content

def create_quicklook_powercolors_main_area(context: AppContext):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Power Colors": create_powercolors_tab(
            context=context,
            warning_handler=warning_handler,
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