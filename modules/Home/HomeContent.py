# Standard Imports
import os
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText
import psutil

# HoloViz Imports
import panel as pn

# Stingray Imports
from stingray.events import EventList
from stingray.gti import get_gti_lengths, get_btis, get_total_gti_length

# Dashboard Classes and Event Data Imports
from utils.globals import loaded_event_data
from utils.dashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    Footer,
    FloatingPlot,
    PlotsContainer,
)


# Strings Imports
from utils.strings import (
    HOME_HEADER_STRING,
    HOME_STINGRAY_TAB_STRING,
    HOME_HOLOVIZ_TAB_STRING,
    HOME_DASHBOARD_TAB_STRING,
    HOME_OUTPUT_BOX_STRING,
    HOME_WARNING_BOX_STRING,
)

matplotlib.use("Agg")

""" Header Section """


def create_home_header() -> MainHeader:
    """
    Create the header section for the home page.

    Returns
    -------
    MainHeader
        An instance of MainHeader with the specified heading and subheading.
    """
    home_heading_input = pn.widgets.TextInput(name="Heading", value=HOME_HEADER_STRING)
    home_subheading_input = pn.widgets.TextInput(
        name="Subheading", value="Stingray GUI using HoloViz"
    )

    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)


# Function to create a resource monitor
def create_home_resource_monitor() -> MainHeader:
    cpu_gauge = pn.indicators.Gauge(
        name="CPU",
        title_size=12,
        value=0,
        bounds=(0, 100),
        format="{value}%",
        sizing_mode="fixed",
        show_ticks=False,
        show_labels=False,
        width=190,
        height=190,
        annulus_width=5,
        custom_opts={
        "series": [{
            "radius": "75%",  # Adjust outer size
        }]
    }
    )
    memory_gauge = pn.indicators.Gauge(
        name="RAM",
        title_size=12,
        value=0,
        bounds=(0, 100),
        format="{value}%",
        sizing_mode="fixed",
        show_ticks=False,
        show_labels=False,
        width=190,
        height=190,
        annulus_width=5,
        custom_opts={
        "series": [{
            "radius": "75%",  # Adjust outer size
        }]
    }
    )

    # Function to fetch system resource usage
    def fetch_resources(event):
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        cpu_gauge.value = cpu
        memory_gauge.value = memory

    # Button to update system monitoring
    fetch_button = pn.widgets.Button(
        name="Check System Resources", button_type="primary"
    )
    fetch_button.on_click(fetch_resources)

    # Resource monitoring container
    resource_monitoring = pn.FlexBox(

        cpu_gauge,
        memory_gauge,
        fetch_button,
        align_items="center",        
    )
    return resource_monitoring


def create_home_main_area() -> MainArea:
    """
    Create the main content area for the home page.

    This function loads default data files into the global event data list,
    if they are not already loaded, and defines content for tabs.

    Returns
    -------
    MainArea
        An instance of MainArea containing tabs with content.
    """
    # Path to the data files
    data_dir = os.path.join(os.getcwd(), "files", "data")
    target_file1 = "nomission.evt"
    file_path1 = os.path.join(data_dir, target_file1)
    target_file2 = "xte_test.evt.gz"
    file_path2 = os.path.join(data_dir, target_file2)

    # Check if the file is already loaded
    if not any(file_name == "nomission" for file_name, _ in loaded_event_data):
        try:
            event_list = EventList.read(file_path1, "ogip")
            loaded_event_data.append(("nomission", event_list))
            print(f"File '{target_file1}' loaded successfully.")
        except Exception as e:
            print(f"Failed to load file '{target_file1}': {e}")
    if not any(file_name == "xte_test.evt.gz" for file_name, _ in loaded_event_data):
        try:
            event_list = EventList.read(file_path2, "ogip")
            loaded_event_data.append(("xte_test.evt.gz", event_list))
            print(f"File '{target_file2}' loaded successfully.")
        except Exception as e:
            print(f"Failed to load file '{target_file2}': {e}")

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


def create_home_output_box() -> OutputBox:
    """
    Create the output box section for the home page.

    Returns
    -------
    OutputBox
        An instance of OutputBox with predefined content.
    """
    return OutputBox(output_content=HOME_OUTPUT_BOX_STRING)


""" Floating Plots """


def create_floating_plot_container(title, content) -> FloatingPlot:
    """
    Create a floating plot container for the home page.

    Parameters
    ----------
    title : str
        The title of the floating plot.
    content : pn.viewable.Viewer
        The content to be displayed in the floating plot.

    Returns
    -------
    FloatingPlot
        An instance of FloatingPlot with the specified title and content.
    """
    return FloatingPlot(title, content)


""" Warning Box Section """


def create_home_warning_box() -> WarningBox:
    """
    Create the warning box section for the home page.

    Returns
    -------
    WarningBox
        An instance of WarningBox with predefined content.
    """
    return WarningBox(warning_content=HOME_WARNING_BOX_STRING)


""" Plots Area Section Initial """


def create_home_plots_area_initial() -> PlotsContainer:
    """
    Create the initial plots area for the home page.

    This function displays a message instead of generating plots
    to reduce load time on the first visit.

    Returns
    -------
    PlotsContainer
        An instance of PlotsContainer with a message.
    """
    text = pn.pane.Markdown(
        "Not displaying the NICER analysis plots on first load as it takes time to load. Move around the dashboard and come back to home page, to see the analysis plots. The buttons to navigate are in the sidebar."
    )
    return PlotsContainer(text)


""" Plots Area Section """


def create_home_plots_area() -> PlotsContainer:
    """
    Create the main plots area for the home page.

    This function generates multiple plots including light curves,
    histograms of bad time intervals, and comparisons between raw
    and filled light curves.

    Returns
    -------
    PlotsContainer
        An instance of PlotsContainer with various plots.
    """
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
    anchored_text = AnchoredText(stats_text, loc="upper right", frameon=True)
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
    ax5.get_lines()[-1].set_label("Raw Light Curve")

    # Modify the color of the raw light curve plot manually
    for line in ax5.get_lines():
        line.set_color("black")

    # Plot the filled light curve
    ax5.plot(
        lc_filled.time,
        lc_filled.counts,
        color="navy",
        drawstyle="steps-mid",
        zorder=20,
        label="Filled Light Curve",
    )

    # Add a title and labels
    ax5.set_title("Comparison of Raw Light Curve and Simulated Data")
    ax5.set_xlabel("Time (s)")
    ax5.set_ylabel("Counts")

    # Add a legend to differentiate between the curves
    ax5.legend()

    # Embed the plot into a Panel component
    comparison_plot_pane = pn.pane.Matplotlib(fig5, width=600, height=600)

    return PlotsContainer(
        raw_lightcurve_pane,
        axislimited_lightcurve_pane,
        bti_plot_pane,
        filled_bti_plot_pane,
        comparison_plot_pane,
    )


""" Help Area Section """


def create_home_help_area() -> HelpBox:
    """
    Create the help section for the home page.

    Combines the main dashboard help content with additional help
    for specific sections.

    Returns
    -------
    HelpBox
        An instance of HelpBox with combined help content.
    """

    tabs_content = {"1st": pn.pane.Markdown("")}
    # help_content = f"{HOME_HELP_BOX_STRING}\n\n{DASHBOARD_HELP_CONTENT}"
    return HelpBox(tabs_content=tabs_content, title="Help Section")


""" Footer Section """


def create_home_footer() -> Footer:
    """
    Create the footer section for the home page.

    Includes additional links such as Privacy Policy, Terms of Service, and Support.

    Returns
    -------
    Footer
        An instance of Footer with the specified content and links.
    """
    footer_content = "© 2024 Stingray. All rights reserved."
    additional_links = [
        "[Privacy Policy](https://github.com/StingraySoftware/StingrayExplorer/blob/main/PrivacyPolicy.md)",
        "[Terms of Service](https://github.com/StingraySoftware/StingrayExplorer/blob/main/TermsOfService.md)",
        "[Contact Us](https://github.com/StingraySoftware/StingrayExplorer/blob/main/ContactUs.md)",
        "[Support](https://github.com/StingraySoftware/StingrayExplorer/blob/main/Support.md)",
        "[About Us](https://github.com/StingraySoftware/StingrayExplorer/blob/main/AboutUs.md)",
    ]
    return Footer(
        main_content=footer_content,
        additional_links=additional_links,
    )
