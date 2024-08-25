from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText
import panel as pn
import os
import numpy as np
from stingray.gti import get_gti_lengths, get_btis, get_total_gti_length
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    Footer,
    FloatingPlot,
    PlotsContainer,
)
from utils.strings import (
    HOME_HEADER_STRING,
    HOME_WELCOME_MESSAGE_STRING,
    HOME_FOOTER_STRING,
    HOME_STINGRAY_TAB_STRING,
    HOME_HOLOVIZ_TAB_STRING,
    HOME_DASHBOARD_TAB_STRING,
    HOME_OUTPUT_BOX_STRING,
    HOME_WARNING_BOX_STRING,
    HOME_HELP_BOX_STRING,
)
from stingray.gti import create_gti_from_condition, gti_border_bins, time_intervals_from_gtis, cross_two_gtis
from stingray.utils import show_progress
from stingray.fourier import avg_cs_from_events, avg_pds_from_events, poisson_level, get_average_ctrate
from stingray import AveragedPowerspectrum, AveragedCrossspectrum, EventList, Lightcurve
from stingray.modeling.parameterestimation import PSDLogLikelihood


""" Header Section """

def create_home_header():
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value=HOME_HEADER_STRING
    )
    home_subheading_input = pn.widgets.TextInput(
        name="Subheading", value="Stingray GUI using HoloViz"
    )

    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)


""" Main Area Section """

def create_home_main_area():
    tab1_content = pn.pane.Markdown(HOME_STINGRAY_TAB_STRING)
    tab2_content = pn.pane.Markdown(HOME_HOLOVIZ_TAB_STRING)
    tab3_content = pn.pane.Markdown(HOME_DASHBOARD_TAB_STRING)
    tabs_content = {
        "What's Stingray?": tab1_content,
        "What's HoloViz?": tab2_content,
        "Dashboard": tab3_content,
    }

    return MainArea(tabs_content=tabs_content)


""" Output Box Section """

def create_home_output_box():
    return OutputBox(output_content=HOME_OUTPUT_BOX_STRING)

""" Floating Plots """
def create_floating_plot_container(title, content):
    return FloatingPlot(title, content)

""" Warning Box Section """

def create_home_warning_box():
    return WarningBox(warning_content=HOME_WARNING_BOX_STRING)

""" Plots Area Section Initial """
def create_home_plots_area_initial():
    text = pn.pane.Markdown("Not displaying the NICER analysis plots on first load as it takes time to load. Move around the dashboard and come back to home page, to see the analysis plots. The buttons to navigate are in the sidebar.")
    return PlotsContainer(text)

# # Define the function to create demo plots
# def create_floating_plot_demo(floating_plot_container):
#     # Define different plots with independent axes
#     hv_plot = hv.Curve([1, 2, 3, 4, 5], label='Simple Line Plot').opts(
#         title="Simple Line Plot",
#         width=400,
#         height=300,
#         color='blue',
#         tools=['hover'],
#         shared_axes=False  # Prevent sharing axes
#     )
    
#     scatter_plot = hv.Scatter(
#         [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)], 
#         kdims=['x'], vdims=['y']
#     ).opts(
#         title="Simple Scatter Plot",
#         width=400,
#         height=300,
#         color='green',
#         size=10,
#         tools=['hover'],
#         shared_axes=False  # Prevent sharing axes
#     )
    
#     button = pn.widgets.Button(name='Click me', button_type='primary')
#     markdown = pn.pane.Markdown("This is a floating plot demo. Click the button to create a new plot.")
    
#     # Create and add different FloatPanel instances to the container
#     floating_plot = pn.layout.FloatPanel(
#         pn.panel(hv_plot),
#         name="NICER Analysis Plots",
#         contained=False,
#         position="center",
#         width=500,
#         height=300,
#         margin=20,
#         config={"headerControls": {"close": "remove"}}  # Example config
#     )
    
#     new_plot = pn.layout.FloatPanel(
#         button,
#         name="Button Panel",
#         contained=False,
#         position="center",
#         width=500,
#         height=300,
#         margin=20,
#         config={"headerControls": {"close": "remove"}}  # Example config
#     )
    
#     new_newplot = pn.layout.FloatPanel(
#         markdown,
#         name="Markdown Panel",
#         contained=False,
#         position="center",
#         width=500,
#         height=300,
#         margin=20,
#         config={"headerControls": {"close": "remove"}}  # Example config
#     )
    
#     scatter_plot_panel = pn.layout.FloatPanel(
#         pn.panel(scatter_plot),
#         name="Scatter Plot Panel",
#         contained=False,
#         position="center",
#         width=500,
#         height=300,
#         margin=20,
#         config={"headerControls": {"close": "remove"}}  # Example config
#     )

#     # Append panels to the container
#     floating_plot_container.append(floating_plot)
#     floating_plot_container.append(new_plot)
#     floating_plot_container.append(new_newplot)
#     floating_plot_container.append(scatter_plot_panel)
    
#     return


""" Plots Area Section """

def create_home_plots_area():

    # Path to the data files
    data_dir = os.path.join(os.getcwd(), "files", "data")

    target_file = "data_small.hdf5"

    file_path = os.path.join(data_dir, target_file)

    events = EventList.read(file_path, "hdf5", additional_columns=["DET_ID"])
    events.fname = file_path
    # Create the raw light curve and apply GTIs
    lc_raw = events.to_lc(dt=1)

    # Matplotlib raw lightcurve plot
    fig1, ax1 = plt.subplots()
    lc_raw.plot(ax=ax1)
    ax1.set_title("Lightcurve of NICER observation of MAXI 1820+070", fontsize=16)
    raw_lightcurve_pane = pn.pane.Matplotlib(fig1, width=600, height=600)

    # Same plot but axis limited
    fig2, ax2 = plt.subplots()
    lc_raw.plot(ax=ax2, axis_limits=[1.331126e8, 1.331134e8, None, None])
    ax2.set_title("Axis limited Lightcurve", fontsize=16)
    axislimited_lightcurve_pane = pn.pane.Matplotlib(fig2, width=600, height=600)


    # Statistics on bad time intervals
    gti_lengths = get_gti_lengths(events.gti)
    btis = get_btis(events.gti)
    bti_lengths = get_gti_lengths(btis) 

    fig3, ax3 = plt.subplots()
    ax3.hist(bti_lengths, bins=np.geomspace(1e-3, 10000, 30))
    ax3.set_xlabel("Length of bad time interval")
    ax3.set_ylabel("Number of intervals")
    ax3.set_xscale("log")
    ax3.set_yscale("log")

    # Add title to the plot
    ax3.set_title("Histogram of Bad Time Intervals")

    # Calculate the values
    total_exposure = get_total_gti_length(events.gti)
    total_bti_length = get_total_gti_length(btis)
    total_bti_length_short = get_total_gti_length(btis[bti_lengths < 1])

    # Add a text box with the statistics inside the plot
    stats_text = (
        f"Total exposure: {total_exposure:.2f}\n"
        f"Total BTI length: {total_bti_length:.2f}\n"
        f"Total BTI length (short BTIs): {total_bti_length_short:.2f}"
    )
    anchored_text = AnchoredText(stats_text, loc='upper right', frameon=True)
    anchored_text.patch.set_boxstyle("round,pad=0.3,rounding_size=0.2")
    ax3.add_artist(anchored_text)

    bti_plot_pane = pn.pane.Matplotlib(fig3, width=600, height=600)

    # Assume the events object is already created and contains the data
    # Example code for filling bad time intervals
    # max_length is the longest bad time interval in seconds we want to fill with simulated data.
    # The buffer size is the region (in seconds) around the bad time interval that we use to
    # extract the distribution of the data to simulate
    ev_filled = events.fill_bad_time_intervals(max_length=1, buffer_size=4)

    # Create a light curve from the filled events
    lc_filled = ev_filled.to_lc(dt=1)

    # Create the figure and axis
    fig4, ax4 = plt.subplots()

    # Plot the filled light curve
    lc_filled.plot(ax=ax4, axis_limits=[1.331126e8, 1.331134e8, None, None])

    # Add an apt title to the plot
    ax4.set_title("Light Curve with Simulated Data Filling Short Bad Time Intervals")

    # Label the axes
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Counts")

    # Embed the plot into a Panel component
    filled_bti_plot_pane = pn.pane.Matplotlib(fig4, width=600, height=600)

    # Plot the raw light curve and simulated data on the same plot
    fig5, ax5 = plt.subplots()
    # Plot the raw light curve
    lc_raw.plot(ax=ax5, axis_limits=[1.331126e8, 1.331134e8, None, None])

    # Manually add a label to the raw light curve plot
    ax5.get_lines()[-1].set_label('Raw Light Curve')


    # Modify the color of the raw light curve plot manually
    for line in ax5.get_lines():
        line.set_color('black')

    # Plot the filled light curve
    ax5.plot(lc_filled.time, lc_filled.counts, color='navy', drawstyle='steps-mid', zorder=20, label='Filled Light Curve')

    # Add a title and labels
    ax5.set_title("Comparison of Raw Light Curve and Simulated Data")
    ax5.set_xlabel("Time (s)")
    ax5.set_ylabel("Counts")

    # Add a legend to differentiate between the curves
    ax5.legend()

    # Embed the plot into a Panel component
    comparison_plot_pane = pn.pane.Matplotlib(fig5, width=600, height=600)


    return PlotsContainer(raw_lightcurve_pane, axislimited_lightcurve_pane, bti_plot_pane, filled_bti_plot_pane, comparison_plot_pane)



""" Help Area Section """


def create_home_help_area():
    help_content = HOME_HELP_BOX_STRING
    return HelpBox(help_content=help_content, title="Help Section")


""" Footer Section """


def create_home_footer():
    icon_buttons = [
        pn.widgets.Button(name="Icon 1", button_type="default"),
        pn.widgets.Button(name="Icon 2", button_type="default"),
        pn.widgets.Button(name="Icon 3", button_type="default"),
        pn.widgets.Button(name="Icon 4", button_type="default"),
        pn.widgets.Button(name="Icon 5", button_type="default"),
    ]
    footer_content = "© 2024 Stingray. All rights reserved."
    additional_links = [
        "[Privacy Policy](https://example.com)",
        "[Terms of Service](https://example.com)",
        "[Contact Us](https://example.com)",
        "[Support](https://example.com)",
        "[About Us](https://example.com)",
    ]
    return Footer(
        main_content=footer_content,
        additional_links=additional_links,
        icons=icon_buttons,
    )
