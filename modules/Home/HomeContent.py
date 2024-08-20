from matplotlib import pyplot as plt
import panel as pn
import holoviews as hv
import os
import numpy as np
from bokeh.plotting import figure
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
        name="Heading", value="Welcome to Stingray Explorer"
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


""" Warning Box Section """

def create_home_warning_box():
    return WarningBox(warning_content=HOME_WARNING_BOX_STRING)



""" Plots Area Section """

def create_home_plots_area():
    # Generate sample data
    times = np.arange(500)
    counts = np.floor(np.random.rand(500) * 50000)

    # Create a Lightcurve object
    lc = Lightcurve(times, counts, skip_checks=True, dt=1.0)
    lc2 = Lightcurve(times, counts, skip_checks=True, dt=1.0)
    lc3 = Lightcurve(times, counts, skip_checks=True, dt=1.0)
    lc4 = Lightcurve(times, counts, skip_checks=True, dt=1.0)

    # Create a Bokeh figure
    plot = figure(title="Demo Lightcurve", width=500, height=500)
    plot2 = figure(title="Demo Lightcurve 2", width=500, height=500)
    plot3 = figure(title="Demo Lightcurve 3", width=500, height=500)
    plot4 = figure(title="Demo Lightcurve 4", width=500, height=500)

    plot.line(lc.time, lc.counts, line_width=2)
    plot2.line(lc2.time, lc2.counts, line_width=2)
    plot3.line(lc3.time, lc3.counts, line_width=2)
    plot4.line(lc4.time, lc4.counts, line_width=2)

    return PlotsContainer(plot, plot2, plot3, plot4)



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
