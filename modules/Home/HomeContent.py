# Standard Imports
import os
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText
import psutil

# Get the current process for resource monitoring
_current_process = psutil.Process(os.getpid())

# HoloViz Imports
import panel as pn

# Stingray Imports
from stingray.events import EventList
from stingray.gti import get_gti_lengths, get_btis, get_total_gti_length

# Dashboard Classes and Event Data Imports
from utils.state_manager import state_manager
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
        name="Subheading", value="Stingray Graphical User Interface"
    )

    return MainHeader(heading=home_heading_input, subheading=home_subheading_input)


# Function to create a resource monitor
def create_home_resource_monitor():
    cpu_gauge = pn.indicators.Gauge(
        name="CPU",
        title_size=11,
        value=0,
        bounds=(0, 100),
        format="{value}%",
        sizing_mode="fixed",
        show_ticks=False,
        show_labels=False,
        width=180,
        height=148,
        annulus_width=2,
        custom_opts={
        "series": [{
            "radius": "100%",  # Adjust outer size
        }]
    }
    )
    memory_gauge = pn.indicators.Gauge(
        name="RAM",
        title_size=11,
        value=0,
        bounds=(0, 100),
        format="{value}%",
        sizing_mode="fixed",
        show_ticks=False,
        show_labels=False,
        width=180,
        height=148,
        annulus_width=2,
        custom_opts={
        "series": [{
            "radius": "100%",  # Adjust outer size
        }]
    }
    )

    # Get system information for display
    total_ram_bytes = psutil.virtual_memory().total
    total_ram_gb = total_ram_bytes / (1024 ** 3)  # Convert bytes to GB
    cpu_cores = psutil.cpu_count(logical=False)  # Physical cores
    cpu_threads = psutil.cpu_count(logical=True)  # Logical cores (threads)

    # Create system info text - CPU on top, RAM below
    cpu_info_text = pn.pane.Markdown(
        f"""**CPU:** {cpu_cores} cores ({cpu_threads} threads)""",
        sizing_mode="fixed",
        align="center",
        styles={"font-size": "12px", "text-align": "center", "margin": "0px", "padding": "0px"},
        margin=0,
    )

    ram_info_text = pn.pane.Markdown(
        f"""**Total RAM:** {total_ram_gb:.1f} GB""",
        sizing_mode="fixed",
        align="center",
        styles={"font-size": "12px", "text-align": "center", "margin": "0px", "padding": "0px"},
        margin=0,
    )

    # Function to fetch StingrayExplorer process resource usage
    # Uses a callback parameter to get the gauges from the button's click event
    def fetch_resources(event):
        # Get CPU usage for this process only (over 1 second interval)
        cpu = _current_process.cpu_percent(interval=1)
        # Get memory usage for this process only (as percentage of total system RAM)
        memory = _current_process.memory_percent()

        # Round to 1 decimal place for proper display in the gauge
        cpu_rounded = round(cpu, 1)
        memory_rounded = round(memory, 1)

        # Update the gauge values
        cpu_gauge.value = cpu_rounded
        memory_gauge.value = memory_rounded

    # Button to update resource monitoring (StingrayExplorer process only)
    fetch_button = pn.widgets.Button(
        name="Check Dashboard Resources", button_type="primary"
    )
    fetch_button.on_click(fetch_resources)

    # Button and info section (vertical layout: CPU, RAM, Button)
    button_info_section = pn.FlexBox(
        cpu_info_text,
        ram_info_text,
        fetch_button,
        flex_direction="column",
        align_items="center",
        justify_content="center",
        gap="2px",
    )

    # Resource monitoring container (horizontal layout)
    resource_monitoring = pn.FlexBox(
        cpu_gauge,
        memory_gauge,
        button_info_section,
        flex_direction="row",
        align_items="center",
        justify_content="center",
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
    if not state_manager.has_event_data("nomission"):
        try:
            event_list = EventList.read(file_path1, "ogip")
            state_manager.add_event_data("nomission", event_list)
            print(f"File '{target_file1}' loaded successfully.")
        except Exception as e:
            print(f"Failed to load file '{target_file1}': {e}")
    if not state_manager.has_event_data("xte_test.evt.gz"):
        try:
            event_list = EventList.read(file_path2, "ogip")
            state_manager.add_event_data("xte_test.evt.gz", event_list)
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


""" Plots Area Section """


def create_home_plots_area() -> PlotsContainer:
    """
    Create the main plots area for the home page.

    Returns an empty plots container. Users can generate plots
    by loading data via the 'Read Data' button.

    Returns
    -------
    PlotsContainer
        An empty instance of PlotsContainer.
    """
    return PlotsContainer()


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
