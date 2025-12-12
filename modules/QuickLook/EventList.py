# Standard Imports
import os
import stat
import copy
import logging
import numpy as np
import warnings
import tempfile
import traceback
import requests
from bokeh.models import Tooltip


# HoloViz Imports
import panel as pn

# Stingray Imports
from stingray.events import EventList

# Dashboard Classes and State Management Imports
from utils.app_context import AppContext
from utils.error_handler import ErrorHandler
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    WarningHandler,
    PlotsContainer,
)


def create_warning_handler():
    """
    Create an instance of WarningHandler and redirect warnings to this custom handler.

    Returns:
        WarningHandler: An instance of WarningHandler to handle warnings.

    Side effects:
        Overrides the default warning handler with a custom one.

    Example:
        >>> warning_handler = create_warning_handler()
        >>> warning_handler.warn("Test warning", category=RuntimeWarning)
    """
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler


""" Header Section """


def create_eventlist_header(context: AppContext):
    """
    Create the header for the EventList section.

    Args:
        context (AppContext): The application context containing containers and state.

    Returns:
        MainHeader: An instance of MainHeader with the specified heading.

    Example:
        >>> header = create_eventlist_header(context)
        >>> header.heading.value
        'QuickLook EventList'
    """
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook EventList"
    )
    return MainHeader(heading=home_heading_input)


def create_eventlist_output_box(content):
    """
    Create an output box to display messages.

    Args:
        content (str): The content to be displayed in the output box.

    Returns:
        OutputBox: An instance of OutputBox with the specified content.

    Example:
        >>> output_box = create_loadingdata_output_box("File loaded successfully.")
        >>> output_box.output_content
        'File loaded successfully.'
    """
    return OutputBox(output_content=content)


""" Warning Box Section """


def create_eventlist_warning_box(content):
    """
    Create a warning box to display warnings.

    Args:
        content (str): The content to be displayed in the warning box.

    Returns:
        WarningBox: An instance of WarningBox with the specified content.

    Example:
        >>> warning_box = create_loadingdata_warning_box("Invalid file format.")
        >>> warning_box.warning_content
        'Invalid file format.'
    """
    return WarningBox(warning_content=content)


# TODO: ADD better comments, error handlling and docstrings
def create_event_list(
    event,
    times_input,
    energy_input,
    pi_input,
    gti_input,
    mjdref_input,
    dt_input,
    high_precision_checkbox,
    mission_input,
    instr_input,
    detector_id_input,
    header_input,
    timeref_input,
    timesys_input,
    ephem_input,
    rmf_file_input,
    skip_checks_checkbox,
    notes_input,
    name_input,
    context: AppContext,
    warning_handler,
):
    """
    Create an event list from user input with all parameters of the EventList class.

    Args:
        See above function for argument details.

    Side effects:
        - Creates a new EventList object and adds it to `loaded_event_data`.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if event list creation fails.
    """
    try:

        # Mandatory input validation
        if not times_input.value:
            context.update_container('output_box',
                create_eventlist_output_box(
                    "Error: Photon Arrival Times is a mandatory field."
                )
            )
            context.update_container('warning_box',
                create_eventlist_warning_box(
                    "Warning: Mandatory fields are missing. Please provide required inputs."
                )
            )
            return

        # Clean and parse inputs, ignoring empty values
        times = [float(t) for t in times_input.value.split(",") if t.strip()]
        mjdref = (
            float(mjdref_input.value.strip()) if mjdref_input.value.strip() else 0.0
        )
        energy = (
            [float(e) for e in energy_input.value.split(",") if e.strip()]
            if energy_input.value.strip()
            else None
        )
        pi = (
            [int(p) for p in pi_input.value.split(",") if p.strip()]
            if pi_input.value.strip()
            else None
        )
        gti = (
            [
                [float(g) for g in interval.split()]
                for interval in gti_input.value.split(";")
                if interval.strip()
            ]
            if gti_input.value.strip()
            else None
        )
        dt = float(dt_input.value.strip()) if dt_input.value.strip() else 0.0
        high_precision = high_precision_checkbox.value
        mission = mission_input.value.strip() or None
        instr = instr_input.value.strip() or None
        detector_id = (
            [int(d) for d in detector_id_input.value.split(",") if d.strip()]
            if detector_id_input.value.strip()
            else None
        )
        header = header_input.value.strip() or None
        timeref = timeref_input.value.strip() or None
        timesys = timesys_input.value.strip() or None
        ephem = ephem_input.value.strip() or None
        rmf_file = rmf_file_input.value.strip() or None
        skip_checks = skip_checks_checkbox.value
        notes = notes_input.value.strip() or None
        name = name_input.value.strip() or f"event_list_{len(context.state.get_event_data())}"

        # Check for duplicates
        if context.state.has_event_data(name):
            context.update_container('output_box',
                create_eventlist_output_box(
                    f"A file with the name '{name}' already exists in memory. Please provide a different name."
                )
            )
            return

        # Create EventList
        event_list = EventList(
            time=times,
            energy=energy,
            pi=pi,
            gti=gti,
            mjdref=mjdref,
            dt=dt,
            high_precision=high_precision,
            mission=mission,
            instr=instr,
            detector_id=detector_id,
            header=header,
            timeref=timeref,
            timesys=timesys,
            ephem=ephem,
            rmf_file=rmf_file,
            skip_checks=skip_checks,
            notes=notes,
        )

        # Store the EventList
        context.state.add_event_data(name, event_list)

        context.update_container('output_box',
            create_eventlist_output_box(
                f"Event List created successfully!\nSaved as: {name}\nDetails:\n"
                f"Times: {event_list.time}\nMJDREF: {event_list.mjdref}\nGTI: {event_list.gti}\n"
                f"Energy: {event_list.energy if energy else 'Not provided'}\nPI: {event_list.pi if pi else 'Not provided'}\n"
                f"Mission: {event_list.mission if mission else 'Not provided'}\nInstrument: {event_list.instr if instr else 'Not provided'}"
            )
        )
    except ValueError as ve:
        user_msg, tech_msg = ErrorHandler.handle_error(
            ve,
            context="Creating custom event list",
            log_level=logging.WARNING
        )
        warning_handler.warn(tech_msg, category=ValueError)
        context.update_container('output_box',
            create_eventlist_output_box(f"Error: {user_msg}")
        )
    except Exception as e:
        user_msg, tech_msg = ErrorHandler.handle_error(
            e,
            context="Creating custom event list"
        )
        warning_handler.warn(tech_msg, category=RuntimeError)
        context.update_container('output_box',
            create_eventlist_output_box(f"Error: {user_msg}")
        )

    if warning_handler.warnings:
        context.update_container('warning_box',
            create_eventlist_warning_box("\n".join(warning_handler.warnings))
        )
    else:
        context.update_container('warning_box', create_eventlist_warning_box("No warnings."))

    warning_handler.warnings.clear()


# TODO: ADD better comments, error handlling and docstrings
def simulate_event_list(
    event,
    time_bins_input,
    max_counts_input,
    dt_input,
    name_input,
    method_selector,
    seed_input,
    simulate_energies_checkbox,
    energy_bins_input,
    energy_counts_input,
    context: AppContext,
    warning_handler,
):
    """
    Simulate an event list based on user-defined parameters.

    Args:
        event: The event object triggering the function.
        time_bins_input: The input for the number of time bins.
        max_counts_input: The input for the maximum counts per bin.
        dt_input: The input for delta time (dt).
        name_input: The input widget for the simulated event list name.
        method_selector: Radio button group for simulation method selection.
        seed_input: Input for random seed (optional).
        simulate_energies_checkbox: Checkbox to enable energy simulation.
        energy_bins_input: Energy bins input (comma-separated keV values).
        energy_counts_input: Counts per bin input (comma-separated values).
        context: Application context.
        warning_handler: The handler for warnings.

    Side effects:
        - Creates a simulated EventList object and adds it to `loaded_event_data`.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if simulation fails.

    Restrictions:
        - Requires a unique name for the simulated event list.

    Example:
        >>> simulate_event_list(event, time_bins_input, max_counts_input, dt_input, name_input, method_selector, seed_input, ...)
        "Event List simulated successfully!"
    """
    # Clear previous warnings
    warning_handler.warnings.clear()
    warnings.resetwarnings()

    try:
        if not name_input.value:
            context.update_container('output_box',
                create_eventlist_output_box(
                    "Please provide a name for the simulated event list."
                )
            )
            return

        if context.state.has_event_data(name_input.value):
            context.update_container('output_box',
                create_eventlist_output_box(
                    f"A file with the name '{name_input.value}' already exists in memory. Please provide a different name."
                )
            )
            return

        # Parse inputs from IntInput and FloatInput widgets
        time_bins = time_bins_input.value
        max_counts = max_counts_input.value
        dt = dt_input.value

        # Simulate the light curve using lightcurve service
        times = np.arange(time_bins)
        counts = np.random.randint(0, max_counts, size=time_bins)

        lc_result = context.services.lightcurve.create_lightcurve_from_arrays(
            times=times,
            counts=counts,
            dt=dt
        )

        if not lc_result["success"]:
            context.update_container('output_box',
                create_eventlist_output_box(f"Error: {lc_result['message']}")
            )
            return

        lc = lc_result["data"]

        # Map radio button value to method string
        method_map = {
            'Probabilistic (Recommended)': 'probabilistic',
            'Deterministic (Legacy)': 'deterministic'
        }
        method = method_map.get(method_selector.value, 'probabilistic')

        # Get seed value (None if empty)
        seed = seed_input.value if seed_input.value is not None else None

        # Simulate EventList from lightcurve using new method
        event_list_result = context.services.lightcurve.simulate_event_list_from_lightcurve(
            lightcurve=lc,
            method=method,
            seed=seed
        )

        if not event_list_result["success"]:
            context.update_container('output_box',
                create_eventlist_output_box(f"Error: {event_list_result['message']}")
            )
            return

        event_list = event_list_result["data"]
        metadata = event_list_result.get("metadata", {})
        name = name_input.value

        # Simulate energies if requested
        energy_metadata = {}
        if simulate_energies_checkbox.value:
            # Parse energy spectrum inputs
            energy_bins_str = energy_bins_input.value.strip()
            energy_counts_str = energy_counts_input.value.strip()

            if not energy_bins_str or not energy_counts_str:
                context.update_container('output_box',
                    create_eventlist_output_box(
                        "Error: Energy simulation enabled but spectrum not provided.\n"
                        "Please provide both energy bins and counts."
                    )
                )
                return

            try:
                # Parse comma-separated values
                energy_bins = [float(e.strip()) for e in energy_bins_str.split(',')]
                energy_counts = [float(c.strip()) for c in energy_counts_str.split(',')]

                # Create spectrum
                spectrum = [energy_bins, energy_counts]

                # Simulate energies
                energy_result = context.services.lightcurve.simulate_energies_for_event_list(
                    event_list=event_list,
                    spectrum=spectrum
                )

                if not energy_result["success"]:
                    context.update_container('output_box',
                        create_eventlist_output_box(f"Error simulating energies: {energy_result['message']}")
                    )
                    return

                event_list = energy_result["data"]
                energy_metadata = energy_result.get("metadata", {})

            except ValueError as ve:
                context.update_container('output_box',
                    create_eventlist_output_box(
                        f"Error parsing energy spectrum: {str(ve)}\n"
                        "Make sure to use comma-separated numbers."
                    )
                )
                return

        context.state.add_event_data(name, event_list)

        # Build output message with method, seed, and energy info
        output_message = (
            f"Event List simulated successfully!\n"
            f"Saved as: {name}\n"
            f"Method: {metadata.get('method', 'unknown').capitalize()}\n"
            f"Seed: {metadata.get('seed', 'random')}\n"
            f"Number of events: {metadata.get('n_events', len(event_list.time))}\n"
            f"Time range: {metadata.get('time_range', (event_list.time[0], event_list.time[-1]))}\n"
            f"Original lightcurve counts: {counts}"
        )

        if energy_metadata:
            output_message += (
                f"\n\nEnergy simulation:\n"
                f"Energy range: {energy_metadata.get('energy_range', 'N/A')} keV\n"
                f"Mean energy: {energy_metadata.get('mean_energy', 'N/A'):.2f} keV\n"
                f"Number of energy bins: {energy_metadata.get('n_energy_bins', 'N/A')}"
            )

        context.update_container('output_box',
            create_eventlist_output_box(output_message)
        )

    except Exception as e:
        user_msg, tech_msg = ErrorHandler.handle_error(
            e,
            context="Simulating event list from lightcurve",
            time_bins=time_bins,
            max_counts=max_counts,
            dt=dt
        )
        warning_handler.warn(tech_msg, category=RuntimeError)
        context.update_container('output_box',
            create_eventlist_output_box(f"Error: {user_msg}")
        )

    if warning_handler.warnings:
        context.update_container('warning_box',
            create_eventlist_warning_box("\n".join(warning_handler.warnings))
        )
    else:
        context.update_container('warning_box', create_eventlist_warning_box("No warnings."))

    warning_handler.warnings.clear()


# TODO: ADD better comments, error handlling and docstrings
def create_event_list_tab(context: AppContext, warning_handler):
    """
    Create the tab for creating an event list with all parameters of the EventList class.

    Args:
        context (AppContext): The application context containing all containers and state.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the event list creation tab.
    """
    # Mandatory parameters
    times_input = pn.widgets.TextInput(
        name="Photon Arrival Times", placeholder="e.g., 0.5, 1.1, 2.2, 3.7"
    )
    mjdref_input = pn.widgets.TextInput(
        name="Reference MJD", placeholder="e.g., 58000."
    )

    # Optional parameters
    energy_input = pn.widgets.TextInput(
        name="Energy (optional)", placeholder="e.g., 0., 3., 4., 20."
    )
    pi_input = pn.widgets.TextInput(
        name="PI (optional)", placeholder="e.g., 100, 200, 300, 400"
    )
    gti_input = pn.widgets.TextInput(
        name="GTIs (optional)", placeholder="e.g., 0 4; 5 10"
    )
    dt_input = pn.widgets.TextInput(
        name="Time Resolution (optional)", placeholder="e.g., 0.01"
    )
    high_precision_checkbox = pn.widgets.Checkbox(
        name="Use High Precision (float128)", value=False
    )
    mission_input = pn.widgets.TextInput(
        name="Mission (optional)", placeholder="e.g., NICER"
    )
    instr_input = pn.widgets.TextInput(
        name="Instrument (optional)", placeholder="e.g., XTI"
    )
    detector_id_input = pn.widgets.TextInput(
        name="Detector ID (optional)", placeholder="e.g., 1, 2, 3"
    )
    header_input = pn.widgets.TextAreaInput(
        name="Header (optional)", placeholder="Provide FITS header if available"
    )
    timeref_input = pn.widgets.TextInput(
        name="Time Reference (optional)", placeholder="e.g., SOLARSYSTEM"
    )
    timesys_input = pn.widgets.TextInput(
        name="Time System (optional)", placeholder="e.g., TDB"
    )
    ephem_input = pn.widgets.TextInput(
        name="Ephemeris (optional)", placeholder="e.g., DE430"
    )
    rmf_file_input = pn.widgets.TextInput(
        name="RMF File (optional)", placeholder="e.g., test.rmf"
    )
    skip_checks_checkbox = pn.widgets.Checkbox(name="Skip Validity Checks", value=False)
    notes_input = pn.widgets.TextAreaInput(
        name="Notes (optional)", placeholder="Any useful annotations"
    )
    name_input = pn.widgets.TextInput(
        name="Event List Name", placeholder="e.g., my_event_list"
    )

    # Create button
    create_button = pn.widgets.Button(name="Create Event List", button_type="primary")

    def on_create_button_click(event):
        # Clear previous output and warnings
        context.clear_container('output_box')
        context.clear_container('warning_box')
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        create_event_list(
            event,
            times_input,
            energy_input,
            pi_input,
            gti_input,
            mjdref_input,
            dt_input,
            high_precision_checkbox,
            mission_input,
            instr_input,
            detector_id_input,
            header_input,
            timeref_input,
            timesys_input,
            ephem_input,
            rmf_file_input,
            skip_checks_checkbox,
            notes_input,
            name_input,
            context,
            warning_handler,
        )

    create_button.on_click(on_create_button_click)

    tab_content = pn.Column(
        pn.pane.Markdown("# Create Event List"),
        pn.Row(
            pn.Column(
                name_input,
                times_input,
                mjdref_input,
                energy_input,
                pi_input,
                gti_input,
                dt_input,
                high_precision_checkbox,
                mission_input,
            ),
            pn.Column(
                instr_input,
                detector_id_input,
                header_input,
                timeref_input,
                timesys_input,
                ephem_input,
                rmf_file_input,
                skip_checks_checkbox,
                notes_input,
            ),
        ),
        create_button,
    )
    return tab_content


# TODO: ADD better comments, error handlling and docstrings
def create_simulate_event_list_tab(context: AppContext, warning_handler):
    """
    Create the tab for simulating event lists.

    Args:
        context (AppContext): The application context containing all containers and state.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the event list simulation tab.

    Example:
        >>> tab = create_simulate_event_list_tab(context, warning_handler)
        >>> isinstance(tab, pn.Column)
        True
    """
    simulation_title = pn.pane.Markdown("# Simulating Random Event Lists")
    time_bins_input = pn.widgets.IntInput(
        name="Number of Time Bins", value=10, step=1, start=1, end=1000000
    )
    max_counts_input = pn.widgets.IntInput(
        name="Max Possible Counts per Bin", value=5, step=1, start=1, end=100000
    )
    dt_input = pn.widgets.FloatInput(
        name="Delta Time (dt)", value=1.0, step=0.1, start=0.001, end=10000.0
    )
    sim_name_input = pn.widgets.TextInput(
        name="Simulated Event List Name", placeholder="e.g., my_sim_event_list"
    )

    method_selector = pn.widgets.RadioButtonGroup(
        name="Simulation Method",
        options=['Probabilistic (Recommended)', 'Deterministic (Legacy)'],
        value='Probabilistic (Recommended)',
        button_type='default'
    )

    method_tooltip = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Probabilistic (Recommended): Uses inverse CDF sampling for statistically realistic events. Each run produces different results (use seed for reproducibility).

Deterministic (Legacy): Creates exact count matching. Same results every time. Not suitable for scientific simulations.""",
            position="bottom",
        )
    )

    seed_input = pn.widgets.IntInput(
        name="Random Seed (optional, for reproducibility)",
        value=None,
        start=0,
        end=2147483647,
        placeholder="Leave empty for random"
    )

    seed_tooltip = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Set a random seed to make probabilistic simulations reproducible. Same seed = same result. Leave empty for truly random simulation.""",
            position="bottom",
        )
    )

    simulate_energies_checkbox = pn.widgets.Checkbox(
        name="Simulate photon energies (optional)",
        value=False
    )

    simulate_energies_tooltip = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Simulate realistic photon energies based on a spectral distribution. The spectrum defines energy bins (keV) and counts in each bin. Uses inverse CDF sampling.""",
            position="bottom",
        )
    )

    energy_bins_input = pn.widgets.TextInput(
        name="Energy bins (keV, comma-separated)",
        placeholder="e.g., 1, 2, 3, 4, 5, 6",
        visible=False
    )

    energy_counts_input = pn.widgets.TextInput(
        name="Counts per bin (comma-separated)",
        placeholder="e.g., 1000, 2040, 1000, 3000, 4020, 2070",
        visible=False
    )

    def toggle_energy_inputs(event):
        """Show/hide energy input fields based on checkbox."""
        energy_bins_input.visible = simulate_energies_checkbox.value
        energy_counts_input.visible = simulate_energies_checkbox.value

    simulate_energies_checkbox.param.watch(toggle_energy_inputs, 'value')

    simulate_button = pn.widgets.Button(
        name="Simulate Event List", button_type="primary"
    )
    simulate_button_tooltip = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Simulate a random light curve and then use it to get the EventList from the specified parameters.""",
            position="bottom",
        )
    )

    def on_simulate_button_click(event):
        # Clear previous output and warnings
        context.update_container('output_box', create_eventlist_output_box("N.A."))
        context.update_container('warning_box', create_eventlist_warning_box("N.A."))
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        # Simulate the event list
        simulate_event_list(
            event,
            time_bins_input,
            max_counts_input,
            dt_input,
            sim_name_input,
            method_selector,
            seed_input,
            simulate_energies_checkbox,
            energy_bins_input,
            energy_counts_input,
            context,
            warning_handler,
        )

    simulate_button.on_click(on_simulate_button_click)

    tab_content = pn.Column(
        simulation_title,
        time_bins_input,
        max_counts_input,
        dt_input,
        sim_name_input,
        pn.pane.Markdown("---"),
        pn.Row(method_selector, method_tooltip),
        pn.Row(seed_input, seed_tooltip),
        pn.pane.Markdown("---"),
        pn.Row(simulate_energies_checkbox, simulate_energies_tooltip),
        energy_bins_input,
        energy_counts_input,
        pn.pane.Markdown("---"),
        simulate_button,
    )
    return tab_content


# TODO: ADD better comments, error handlling and docstrings
def create_eventlist_operations_tab(context: AppContext, warning_handler):
    """
    Create the EventList Operations tab with buttons for operations like applying deadtime,
    filtering energy ranges, and converting PI to energy.

    Args:
        context (AppContext): The application context containing all containers and state.
        warning_handler: The custom warning handler.

    Returns:
        Panel layout for the tab.
    """
    # Define widgets for input
    multi_event_list_select = pn.widgets.MultiSelect(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(context.state.get_event_data())},
        size=8,
    )
    event_list_properties_box = pn.pane.Markdown(
        "**Select an EventList to view its properties.**"
    )

    multi_light_curve_select = pn.widgets.MultiSelect(
        name="Select Light Curve(s)",
        options={name: i for i, (name, lc) in enumerate(context.state.get_light_curve())},
        size=8,
    )

    light_curve_properties_box = pn.pane.Markdown(
        "**Select a LightCurve to view its properties.**"
    )

    deadtime_input = pn.widgets.FloatInput(
        name="Deadtime", value=0.01, step=0.001, start=0.001, end=10000.0
    )
    deadtime_inplace_checkbox = pn.widgets.Checkbox(
        name="If True, apply the deadtime to the current event list. Otherwise, return a new event list.",
        value=False,
    )
    apply_deadtime_button = pn.widgets.Button(
        name="Apply Deadtime", button_type="primary"
    )
    ## TODO: additional_output: Only returned if return_all checbox is True. See get_deadtime_mask for more details.

    rmf_file_input = pn.widgets.TextInput(
        name="RMF File Path", placeholder="Path to RMF file for PI to Energy conversion"
    )

    rmf_newEventList_checkbox = pn.widgets.Checkbox(
        name="If True, create a new event list with the converted energy values. Otherwise, modify the existing event list in place.",
        value=True,
    )

    convert_pi_button = pn.widgets.Button(
        name="Convert PI to Energy", button_type="primary"
    )

    energy_range_input = pn.widgets.TextInput(
        name="Energy Range in (keV) or PI channel if use_pi is True",
        placeholder="e.g., 0.3, 10",
    )

    filterEnergy_use_pi_checkbox = pn.widgets.Checkbox(
        name="Use PI channel instead of energy for filtering", value=False
    )

    filterEnergy_inplace_checkbox = pn.widgets.Checkbox(
        name="If True, filter the current event list in place. Otherwise, return a new event list.",
        value=False,
    )

    filter_energy_button = pn.widgets.Button(
        name="Filter by Energy Range", button_type="primary"
    )

    energy_ranges_input = pn.widgets.TextInput(
        name="Energy Ranges",
        placeholder="e.g., [[0.3, 2], [2, 10]]",
    )

    segment_size_input = pn.widgets.FloatInput(
        name="Segment Size", value=0.5, step=0.1, start=0.0, end=1e6
    )
    color_use_pi_checkbox = pn.widgets.Checkbox(
        name="Use PI channel instead of energy", value=False
    )
    compute_color_button = pn.widgets.Button(
        name="Compute Color Evolution", button_type="primary"
    )

    energy_mask_input = pn.widgets.TextInput(
        name="Energy Range (keV or PI if use_pi=True)", placeholder="e.g., 0.3, 10"
    )
    energy_mask_use_pi_checkbox = pn.widgets.Checkbox(
        name="Use PI channel instead of energy", value=False
    )
    get_energy_mask_button = pn.widgets.Button(
        name="Get Energy Mask", button_type="primary"
    )

    # Widgets for Intensity Evolution
    intensity_energy_range_input = pn.widgets.TextInput(
        name="Energy Range (keV or PI if use_pi=True)", placeholder="e.g., 0.3, 10"
    )
    intensity_segment_size_input = pn.widgets.FloatInput(
        name="Segment Size", value=0.5, step=0.1, start=0.0, end=1e6
    )
    intensity_use_pi_checkbox = pn.widgets.Checkbox(
        name="Use PI channel instead of energy", value=False
    )
    compute_intensity_button = pn.widgets.Button(
        name="Compute Intensity Evolution", button_type="primary"
    )

    # Widgets for Joining EventLists
    join_strategy_select = pn.widgets.Select(
        name="Join Strategy",
        options=["infer", "intersection", "union", "append", "none"],
        value="infer",
    )
    join_button = pn.widgets.Button(name="Join EventLists", button_type="primary")

    # Widgets for Sorting EventLists
    sort_inplace_checkbox = pn.widgets.Checkbox(name="Sort in place", value=False)
    sort_button = pn.widgets.Button(name="Sort EventLists", button_type="primary")

    # Widgets for Astropy Export
    astropy_export_path_input = pn.widgets.TextInput(
        name="Output file path",
        placeholder="/path/to/output.ecsv"
    )
    astropy_export_format_select = pn.widgets.Select(
        name="Export format",
        options=["ascii.ecsv", "fits", "votable", "hdf5"],
        value="ascii.ecsv"
    )
    export_astropy_button = pn.widgets.Button(
        name="Export to Astropy Table",
        button_type="primary"
    )

    # Widgets for Astropy Import
    astropy_import_path_input = pn.widgets.TextInput(
        name="Input file path",
        placeholder="/path/to/input.ecsv"
    )
    astropy_import_format_select = pn.widgets.Select(
        name="Import format",
        options=["ascii.ecsv", "fits", "votable", "hdf5"],
        value="ascii.ecsv"
    )
    astropy_import_name_input = pn.widgets.TextInput(
        name="EventList name",
        placeholder="imported_eventlist"
    )
    import_astropy_button = pn.widgets.Button(
        name="Import from Astropy Table",
        button_type="primary"
    )

    # Callback to update the properties box
    def update_event_list_properties(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            event_list_properties_box.object = "**No EventList selected.**"
            return

        properties = []
        for selected_index in selected_indices:
            event_list_name, event_list = context.state.get_event_data()[selected_index]
            gti_count = len(event_list.gti) if hasattr(event_list, "gti") else "N/A"
            time_span = (
                f"{event_list.time[0]:.2f} - {event_list.time[-1]:.2f}"
                if hasattr(event_list, "time") and len(event_list.time) > 0
                else "N/A"
            )
            energy_info = (
                "Available"
                if hasattr(event_list, "energy") and event_list.energy is not None
                else "Not available"
            )
            pi_info = (
                "Available"
                if hasattr(event_list, "pi") and event_list.pi is not None
                else "Not available"
            )

            properties.append(
                f"### EventList: {event_list_name}\n"
                f"- **GTI Count**: {gti_count}\n"
                f"- **Time Span**: {time_span}\n"
                f"- **Energy Data**: {energy_info}\n"
                f"- **PI Data**: {pi_info}\n"
            )

        event_list_properties_box.object = "\n".join(properties)

    # Callback to update the lightcurve properties box
    def update_light_curve_properties(event):
        selected_indices = multi_light_curve_select.value
        if not selected_indices:
            light_curve_properties_box.object = "**No LightCurve selected.**"
            return

        properties = []
        for selected_index in selected_indices:
            light_curve_name, light_curve = context.state.get_light_curve()[selected_index]
            properties.append(
                f"### LightCurve: {light_curve_name}\n"
                f"- **Counts**: {light_curve.counts}\n"
                f"- **Time Span**: {light_curve.time[0]:.2f} - {light_curve.time[-1]:.2f}\n"
                f"- **Time Resolution**: {light_curve.dt:.2f}\n"
            )

        light_curve_properties_box.object = "\n".join(properties)

    # Callback: Apply Deadtime
    def apply_deadtime_callback(event):
        selected_indices = multi_event_list_select.value
        if selected_indices is None:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return

        deadtime = deadtime_input.value
        inplace = deadtime_inplace_checkbox.value
        results = []

        for index in selected_indices:
            try:
                event_list_name, event_list = state_manager.get_event_data()[index]
                if inplace:
                    event_list.apply_deadtime(deadtime, inplace=True)
                    results.append(
                        f"Modified EventList '{event_list_name}' in place with deadtime={deadtime}s."
                    )
                else:
                    new_event_list = event_list.apply_deadtime(deadtime, inplace=False)
                    new_name = f"{event_list_name}_{deadtime}"
                    context.state.add_event_data(new_name, new_event_list)
                    results.append(
                        f"Created new EventList '{new_name}' with deadtime={deadtime}s."
                    )
            except Exception as e:
                warning_handler.warn(str(e), category=RuntimeWarning)

        # Update the output box with results
        if results:
            output_box_container[:] = [create_eventlist_output_box("\n".join(results))]
        else:
            output_box_container[:] = [
                create_eventlist_output_box("No event lists processed.")
            ]

    # Callback: Convert PI to Energy
    def convert_pi_callback(event):
        selected_indices = multi_event_list_select.value
        if selected_indices is None:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return

        if len(selected_indices) > 1:
            output_box_container[:] = [
                create_eventlist_output_box(
                    "Please select only one event list for PI to Energy conversion."
                )
            ]
            return

        try:
            rmf_file = rmf_file_input.value
            if not rmf_file:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        "Warning: No RMF file provided. Conversion cannot proceed."
                    )
                ]
                return

            if not os.path.isfile(rmf_file):
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        f"Warning: RMF file '{rmf_file}' does not exist. Please provide a valid file path."
                    )
                ]
                return

            # Perform PI to Energy conversion
            selected_index = selected_indices[0]
            event_list_name, event_list = context.state.get_event_data()[selected_index]

            # Check if PI data is available
            if not hasattr(event_list, "pi") or event_list.pi is None:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        f"Warning: EventList '{event_list_name}' has no valid PI data. Cannot convert to Energy."
                    )
                ]
                return

            if rmf_newEventList_checkbox.value:
                new_event_list = copy.deepcopy(
                    event_list
                )  # Deepcopy to ensure independence
                new_event_list.convert_pi_to_energy(rmf_file)
                new_event_list_name = f"{event_list_name}_converted_energy"
                context.state.add_event_data(
                    (new_event_list_name, new_event_list)
                )  # Add new event list
                output_box_container[:] = [
                    create_eventlist_output_box(
                        f"New EventList '{new_event_list_name}' created with converted energy values."
                    )
                ]
            else:  # Modify the existing event list in place
                event_list.convert_pi_to_energy(rmf_file)
                output_box_container[:] = [
                    create_eventlist_output_box(
                        f"Energy values converted in place for EventList '{event_list_name}'."
                    )
                ]

        except Exception as e:
            warning_handler.warn(str(e), category=RuntimeWarning)

    # Callback: Filter by Energy Range
    def filter_energy_callback(event):
        selected_indices = multi_event_list_select.value
        if selected_indices is None:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return
        try:
            energy_range_input_value = energy_range_input.value
            if not energy_range_input_value:
                raise ValueError(
                    "Energy range input cannot be empty. Please provide two comma-separated values."
                )
            try:
                energy_range = [
                    float(val.strip()) for val in energy_range_input_value.split(",")
                ]
            except ValueError:
                raise ValueError(
                    "Invalid energy range input. Please provide two valid numbers separated by a comma."
                )
            if len(energy_range) != 2:
                raise ValueError(
                    "Energy range must contain exactly two values (min, max)."
                )
            if energy_range[0] is None or energy_range[1] is None:
                raise ValueError("Energy range values cannot be None.")
            if energy_range[0] >= energy_range[1]:
                raise ValueError(
                    "Invalid energy range: Minimum value must be less than maximum value."
                )

            # Get the options for inplace and use_pi
            inplace = filterEnergy_inplace_checkbox.value
            use_pi = filterEnergy_use_pi_checkbox.value

            results = []

            for selected_index in selected_indices:
                event_list_name, event_list = context.state.get_event_data()[selected_index]

                # Validate energy or PI data
                if use_pi:
                    if not hasattr(event_list, "pi") or event_list.pi is None:
                        message = f"EventList '{event_list_name}' has no valid PI data."
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return

                else:
                    if not hasattr(event_list, "energy") or event_list.energy is None:
                        message = (
                            f"EventList '{event_list_name}' has no valid energy data. "
                            f"Please ensure the energy data is initialized (e.g., by converting PI to energy)."
                        )
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return

                if inplace:
                    # Modify the event list in place
                    event_list.filter_energy_range(
                        energy_range, inplace=True, use_pi=use_pi
                    )

                    results.append(
                        f"Filtered EventList '{event_list_name}' in place using energy range {energy_range} (use_pi={use_pi})."
                    )
                else:
                    # Create a new event list
                    filtered_event_list = event_list.filter_energy_range(
                        energy_range, inplace=False, use_pi=use_pi
                    )
                    if use_pi:
                        new_event_list_name = f"{event_list_name}_filtered_pi_{energy_range[0]}_{energy_range[1]}"
                    else:
                        new_event_list_name = f"{event_list_name}_filtered_energy_{energy_range[0]}_{energy_range[1]}"
                    context.state.add_event_data((new_event_list_name, filtered_event_list))

                    results.append(
                        f"Created new EventList '{new_event_list_name}' filtered using energy range {energy_range} (use_pi={use_pi})."
                    )

            # Update the output with the results
            if results:
                output_box_container[:] = [
                    create_eventlist_output_box("\n".join(results))
                ]
            else:
                output_box_container[:] = [
                    create_eventlist_output_box("No event lists were processed.")
                ]
        except Exception as e:
            warning_handler.warn(str(e), category=RuntimeWarning)

    # Callback: Compute Color Evolution
    def compute_color_callback(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return

        try:
            energy_ranges_input_value = energy_ranges_input.value
            if not energy_ranges_input_value:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        "Warning: Energy ranges input cannot be empty. Provide two energy ranges as [[min1, max1], [min2, max2]]."
                    )
                ]
                return
            try:
                energy_ranges = eval(energy_ranges_input_value)
                if (
                    not isinstance(energy_ranges, list)
                    or len(energy_ranges) != 2
                    or not all(len(er) == 2 for er in energy_ranges)
                ):
                    warning_box_container[:] = [
                        create_eventlist_warning_box(
                            "Warning: Invalid energy ranges format. Provide two energy ranges as [[min1, max1], [min2, max2]]."
                        )
                    ]
                    return
                energy_ranges = [[float(x) for x in er] for er in energy_ranges]
            except Exception:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        "Warning: Invalid energy ranges format. Provide two energy ranges as [[min1, max1], [min2, max2]]."
                    )
                ]
                return

            segment_size = segment_size_input.value
            use_pi = color_use_pi_checkbox.value

            results = []
            for selected_index in selected_indices:
                event_list_name, event_list = context.state.get_event_data()[selected_index]

                # Validate energy or PI data
                if use_pi:
                    if not hasattr(event_list, "pi") or event_list.pi is None:
                        message = f"EventList '{event_list_name}' has no valid PI data."
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return
                else:
                    if not hasattr(event_list, "energy") or event_list.energy is None:
                        message = (
                            f"EventList '{event_list_name}' has no valid energy data. "
                            f"Please ensure the energy data is initialized (e.g., by converting PI to energy)."
                        )
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return

                # Compute color evolution
                color_evolution = event_list.get_color_evolution(
                    energy_ranges, segment_size=segment_size, use_pi=use_pi
                )
                results.append(
                    f"Computed color evolution for EventList '{event_list_name}' with energy ranges {energy_ranges} and segment size {segment_size}."
                )
                results.append(f"Color Evolution: {color_evolution}")

            # Update the output with the results
            if results:
                output_box_container[:] = [
                    create_eventlist_output_box("\n".join(results))
                ]
            else:
                output_box_container[:] = [
                    create_eventlist_output_box("No event lists processed.")
                ]

        except Exception as e:
            error_message = (
                f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(str(e), category=RuntimeWarning)

    # Callback for Get Energy Mask
    def get_energy_mask_callback(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return

        try:
            # Parse and validate energy range
            energy_range_input_value = energy_mask_input.value
            if not energy_range_input_value:
                raise ValueError(
                    "Energy range input cannot be empty. Please provide two comma-separated values."
                )
            try:
                energy_range = [
                    float(val.strip()) for val in energy_range_input_value.split(",")
                ]
            except ValueError:
                raise ValueError(
                    "Invalid energy range input. Please provide two valid numbers separated by a comma."
                )
            if len(energy_range) != 2:
                raise ValueError(
                    "Energy range must contain exactly two values (min, max)."
                )
            if energy_range[0] is None or energy_range[1] is None:
                raise ValueError("Energy range values cannot be None.")
            if energy_range[0] >= energy_range[1]:
                raise ValueError(
                    "Invalid energy range: Minimum value must be less than maximum value."
                )

            use_pi = energy_mask_use_pi_checkbox.value

            results = []
            for selected_index in selected_indices:
                event_list_name, event_list = context.state.get_event_data()[selected_index]

                # Validate energy or PI data
                if use_pi:
                    if not hasattr(event_list, "pi") or event_list.pi is None:
                        message = f"EventList '{event_list_name}' has no valid PI data."
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return
                else:
                    if not hasattr(event_list, "energy") or event_list.energy is None:
                        message = (
                            f"EventList '{event_list_name}' has no valid energy data. "
                            f"Please ensure the energy data is initialized (e.g., by converting PI to energy)."
                        )
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return

                # Get energy mask
                energy_mask = event_list.get_energy_mask(energy_range, use_pi=use_pi)
                results.append(
                    f"Computed energy mask for EventList '{event_list_name}' with energy range {energy_range} (use_pi={use_pi})."
                )
                results.append(f"Energy Mask: {energy_mask}")

            # Update the output with results
            if results:
                output_box_container[:] = [
                    create_eventlist_output_box("\n".join(results))
                ]
            else:
                output_box_container[:] = [
                    create_eventlist_output_box("No event lists processed.")
                ]

        except Exception as e:
            error_message = (
                f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Callback for Intensity Evolution
    def compute_intensity_callback(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            output_box_container[:] = [
                create_eventlist_output_box("No event list selected.")
            ]
            return

        try:
            # Parse and validate energy range
            energy_range_input_value = intensity_energy_range_input.value
            if not energy_range_input_value:
                raise ValueError(
                    "Energy range input cannot be empty. Please provide two comma-separated values."
                )
            try:
                energy_range = [
                    float(val.strip()) for val in energy_range_input_value.split(",")
                ]
            except ValueError:
                raise ValueError(
                    "Invalid energy range input. Please provide two valid numbers separated by a comma."
                )
            if len(energy_range) != 2:
                raise ValueError(
                    "Energy range must contain exactly two values (min, max)."
                )
            if energy_range[0] is None or energy_range[1] is None:
                raise ValueError("Energy range values cannot be None.")
            if energy_range[0] >= energy_range[1]:
                raise ValueError(
                    "Invalid energy range: Minimum value must be less than maximum value."
                )

            segment_size = intensity_segment_size_input.value
            use_pi = intensity_use_pi_checkbox.value

            results = []
            for selected_index in selected_indices:
                event_list_name, event_list = context.state.get_event_data()[selected_index]

                # Validate energy or PI data
                if use_pi:
                    if not hasattr(event_list, "pi") or event_list.pi is None:
                        message = f"EventList '{event_list_name}' has no valid PI data."
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return
                else:
                    if not hasattr(event_list, "energy") or event_list.energy is None:
                        message = (
                            f"EventList '{event_list_name}' has no valid energy data. "
                            f"Please ensure the energy data is initialized (e.g., by converting PI to energy)."
                        )
                        warning_box_container[:] = [
                            create_eventlist_warning_box(message)
                        ]
                        return

                # Compute intensity evolution
                intensity_evolution = event_list.get_intensity_evolution(
                    energy_range, segment_size=segment_size, use_pi=use_pi
                )
                results.append(
                    f"Computed intensity evolution for EventList '{event_list_name}' with energy range {energy_range} and segment size {segment_size}."
                )
                results.append(f"Intensity Evolution: {intensity_evolution}")

            # Update the output with results
            if results:
                output_box_container[:] = [
                    create_eventlist_output_box("\n".join(results))
                ]
            else:
                output_box_container[:] = [
                    create_eventlist_output_box("No event lists processed.")
                ]

        except Exception as e:
            error_message = (
                f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Callback for Joining EventLists
    def join_eventlists_callback(event):
        selected_indices = multi_event_list_select.value
        if len(selected_indices) < 2:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please select at least two EventLists to join."
                )
            ]
            return

        try:
            strategy = join_strategy_select.value
            # Retrieve the selected event lists
            all_event_data = context.state.get_event_data()
            selected_event_lists = [all_event_data[i][1] for i in selected_indices]
            selected_names = [all_event_data[i][0] for i in selected_indices]

            # Perform the join operation
            result_event_list = selected_event_lists[0]
            for other_event_list in selected_event_lists[1:]:
                result_event_list = result_event_list.join(
                    other_event_list, strategy=strategy
                )

            # Generate a new name for the joined EventList
            new_event_list_name = f"joined_{'_'.join(selected_names)}_{strategy}"
            context.state.add_event_data(new_event_list_name, result_event_list)

            # Update the output container with success message
            output_box_container[:] = [
                create_eventlist_output_box(
                    f"Joined EventLists: {', '.join(selected_names)} using strategy '{strategy}'.\n"
                    f"New EventList saved as '{new_event_list_name}'."
                )
            ]

        except Exception as e:
            error_message = (
                f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Callback for Sorting EventLists
    def sort_eventlists_callback(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please select at least one EventList to sort."
                )
            ]
            return

        inplace = sort_inplace_checkbox.value
        results = []

        try:
            for selected_index in selected_indices:
                event_list_name, event_list = context.state.get_event_data()[selected_index]

                if inplace:
                    # Sort in place
                    event_list.sort(inplace=True)
                    results.append(f"Sorted EventList '{event_list_name}' in place.")
                else:
                    # Sort and create a new EventList
                    sorted_event_list = event_list.sort(inplace=False)
                    new_event_list_name = f"{event_list_name}_sorted"
                    context.state.add_event_data((new_event_list_name, sorted_event_list))
                    results.append(
                        f"Created a new sorted EventList '{new_event_list_name}' from '{event_list_name}'."
                    )

            # Update output container with results
            output_box_container[:] = [create_eventlist_output_box("\n".join(results))]

        except Exception as e:
            error_message = (
                f"An error occurred:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Callback for Exporting to Astropy Table
    def export_astropy_callback(event):
        selected_indices = multi_event_list_select.value
        if not selected_indices:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please select at least one EventList to export."
                )
            ]
            return

        if len(selected_indices) > 1:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please select only one EventList for export."
                )
            ]
            return

        output_path = astropy_export_path_input.value.strip()
        if not output_path:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please provide an output file path."
                )
            ]
            return

        try:
            selected_index = selected_indices[0]
            event_list_name, event_list = context.state.get_event_data()[selected_index]
            export_format = astropy_export_format_select.value

            # Call the service method
            result = context.services.data.export_event_list_to_astropy_table(
                event_list_name=event_list_name,
                output_path=output_path,
                fmt=export_format
            )

            if result["success"]:
                output_box_container[:] = [
                    create_eventlist_output_box(
                        f"Successfully exported EventList '{event_list_name}' to:\n"
                        f"{output_path}\n"
                        f"Format: {export_format}\n"
                        f"Rows: {result['metadata']['n_rows']}"
                    )
                ]
            else:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        f"Export failed: {result['message']}"
                    )
                ]

        except Exception as e:
            error_message = (
                f"An error occurred during export:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Callback for Importing from Astropy Table
    def import_astropy_callback(event):
        input_path = astropy_import_path_input.value.strip()
        if not input_path:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please provide an input file path."
                )
            ]
            return

        import_name = astropy_import_name_input.value.strip()
        if not import_name:
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    "Please provide a name for the imported EventList."
                )
            ]
            return

        if not os.path.isfile(input_path):
            warning_box_container[:] = [
                create_eventlist_warning_box(
                    f"File not found: {input_path}"
                )
            ]
            return

        try:
            import_format = astropy_import_format_select.value

            # Call the service method
            result = context.services.data.import_event_list_from_astropy_table(
                file_path=input_path,
                name=import_name,
                fmt=import_format
            )

            if result["success"]:
                output_box_container[:] = [
                    create_eventlist_output_box(
                        f"Successfully imported EventList '{import_name}' from:\n"
                        f"{input_path}\n"
                        f"Format: {import_format}\n"
                        f"Events: {result['metadata']['n_events']}"
                    )
                ]
            else:
                warning_box_container[:] = [
                    create_eventlist_warning_box(
                        f"Import failed: {result['message']}"
                    )
                ]

        except Exception as e:
            error_message = (
                f"An error occurred during import:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )
            print(error_message)
            warning_handler.warn(error_message, category=RuntimeWarning)

    # Assign callbacks to buttons
    multi_event_list_select.param.watch(update_event_list_properties, "value")
    multi_light_curve_select.param.watch(update_light_curve_properties, "value")
    apply_deadtime_button.on_click(apply_deadtime_callback)
    convert_pi_button.on_click(convert_pi_callback)
    filter_energy_button.on_click(filter_energy_callback)
    compute_color_button.on_click(compute_color_callback)
    get_energy_mask_button.on_click(get_energy_mask_callback)
    compute_intensity_button.on_click(compute_intensity_callback)
    join_button.on_click(join_eventlists_callback)
    sort_button.on_click(sort_eventlists_callback)
    export_astropy_button.on_click(export_astropy_callback)
    import_astropy_button.on_click(import_astropy_callback)

    # Layout for the tab
    tab_content = pn.Column(
        pn.pane.Markdown("# EventList Operations"),
        pn.Row(
            pn.Column(
                multi_event_list_select,
                event_list_properties_box,
            ),
            pn.Column(
                multi_light_curve_select,
                light_curve_properties_box,
            ),
        ),
        pn.Column(
            pn.FlexBox(
                pn.Column(
                    pn.pane.Markdown("## Apply Deadtime"),
                    deadtime_input,
                    deadtime_inplace_checkbox,
                    apply_deadtime_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Convert PI to Energy"),
                    rmf_file_input,
                    rmf_newEventList_checkbox,
                    convert_pi_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Filter by Energy Range"),
                    energy_range_input,
                    filterEnergy_inplace_checkbox,
                    filterEnergy_use_pi_checkbox,
                    filter_energy_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Compute Color Evolution"),
                    energy_ranges_input,
                    segment_size_input,
                    color_use_pi_checkbox,
                    compute_color_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Get Energy Mask"),
                    energy_mask_input,
                    energy_mask_use_pi_checkbox,
                    get_energy_mask_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Compute Intensity Evolution"),
                    intensity_energy_range_input,
                    intensity_segment_size_input,
                    intensity_use_pi_checkbox,
                    compute_intensity_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Join EventLists"),
                    join_strategy_select,
                    join_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Sort EventLists"),
                    sort_inplace_checkbox,
                    sort_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Export to Astropy Table"),
                    astropy_export_path_input,
                    astropy_export_format_select,
                    export_astropy_button,
                    width=400,
                    height=300,
                ),
                pn.Column(
                    pn.pane.Markdown("## Import from Astropy Table"),
                    astropy_import_path_input,
                    astropy_import_format_select,
                    astropy_import_name_input,
                    import_astropy_button,
                    width=400,
                    height=300,
                ),
                flex_direction="row",
                flex_wrap="wrap",
                align_items="center",
                justify_content="center",
            )
        ),
        pn.pane.Markdown("<br/>"),
    )
    return tab_content


def create_eventlist_main_area(context: AppContext):
    """
    Create the main area for the EventList tab, including all sub-tabs.

    Args:
        context (AppContext): The application context containing containers and state.

    Returns:
        MainArea: An instance of MainArea with all the necessary tabs.

    Example:
        >>> main_area = create_eventlist_main_area(context)
        >>> isinstance(main_area, MainArea)
        True
    """
    warning_handler = create_warning_handler()
    tabs_content = {
        "Create Event List": create_event_list_tab(
            context=context,
            warning_handler=warning_handler,
        ),
        "Simulate Event List": create_simulate_event_list_tab(
            context=context,
            warning_handler=warning_handler,
        ),
        "EventList Operations": create_eventlist_operations_tab(
            context=context,
            warning_handler=warning_handler,
        ),
    }
    return MainArea(tabs_content=tabs_content)


def create_eventlist_help_area():
    """
    Create the help area for the data loading tab.

    Returns:
        HelpBox: An instance of HelpBox with the help content.
    """

    # Content for "Introduction to Event Lists"
    intro_content = """
    ## Introduction to Event Lists

    ### What are Event Lists?

    In X-ray astronomy, an **Event List** represents a record of individual photon detection events as observed by a telescope. Each event corresponds to the detection of a photon and includes attributes like:
    - **Time of Arrival (TOA)**: The exact time when the photon was detected.
    - **Photon Energy**: Derived from the pulse height or energy channel recorded.
    - **Good Time Intervals (GTIs)**: Periods during which the instrument was actively recording valid data.
    - **Pulse Invariant (PI) Channel**: A standardized representation of photon energy.

    Event Lists are typically the starting point for data analysis in high-energy astrophysics. They provide unbinned, high-precision information about individual photon arrivals, enabling various scientific analyses such as timing, spectral, and correlation studies.

    ### Scientific Significance of Event Lists

    Event Lists allow astronomers to study the variability of astrophysical sources across a wide range of timescales:
    - **Fast Transients**: Sources like X-ray bursts, magnetar flares, or fast radio bursts, which brighten and dim on millisecond-to-minute scales.
    - **Quasi-Periodic Oscillations (QPOs)**: Oscillations in black hole and neutron star systems that vary unpredictably around a central frequency.
    - **Stochastic Variability**: Random fluctuations in brightness, often associated with accretion processes.

    Additionally, Event Lists are fundamental for studying:
    - **Time Lags**: Delays between high- and low-energy photon emissions due to processes like reflection or turbulent flows in accretion disks.
    - **Spectral Timing**: Techniques that combine time and energy data to probe the physical processes near compact objects.

    ### Anatomy of an Event List

    An Event List is often stored as a FITS (Flexible Image Transport System) file, with each row in the table corresponding to a single detected photon. The table contains columns for various attributes:
    - **Time**: Precise timestamp of the event (e.g., in seconds or Modified Julian Date).
    - **Energy or PI Channel**: Photon energy or pulse invariant channel.
    - **GTIs**: Intervals of valid observation time.
    - **Spatial Information** (optional): Detector coordinates or celestial coordinates.

    ### How Event Lists are Used

    Event Lists are typically processed and filtered to remove invalid events or background noise. They can then be converted into:
    - **Light Curves**: Binned time series of photon counts.
    - **Spectra**: Energy distributions of detected photons.
    - **Power Spectra**: Frequency-domain representations of variability.

    ### Key Terms in Event Lists

    - **Photon Time of Arrival (TOA)**: The recorded time when a photon hits the detector.
    - **Good Time Intervals (GTIs)**: Periods when the instrument was actively recording valid data.
    - **Pulse Invariant (PI) Channel**: A detector-specific channel number that maps to the photon’s energy.
    - **RMF File**: Response Matrix File, used to calibrate PI channels into physical energy values (e.g., keV).
    - **FITS Format**: The standard file format for Event Lists in high-energy astrophysics.

    ### Example: Event List Data Structure

    A typical Event List in FITS format contains columns like:
    ```
    TIME      PI      ENERGY   GTI
    ---------------------------------
    0.0012    12      2.3 keV  [0, 100]
    0.0034    15      3.1 keV  [0, 100]
    0.0048    10      1.8 keV  [0, 100]
    ```

    ### Advantages of Event Lists
    - **High Precision**: Tracks individual photon events without binning, preserving maximum information.
    - **Flexibility**: Can be transformed into various forms (e.g., light curves, spectra) for different analyses.
    - **Time-Energy Data**: Enables advanced spectral-timing techniques.

    ### Challenges and Considerations
    - **Dead Time**: Time intervals when the detector cannot record new events, affecting variability measurements.
    - **Instrumental Noise**: False events caused by electronics or background radiation.
    - **Time Resolution**: Limited by the instrument's precision in recording photon arrival times.

    By understanding Event Lists, astronomers gain insight into the underlying physical processes driving variability in high-energy astrophysical sources.

    ### References
    - van der Klis, M. (2006). "Rapid X-ray Variability."
    - Miniutti, G., et al. (2019). "Quasi-Periodic Eruptions in AGN."
    - Galloway, D., & Keek, L. (2021). "X-ray Bursts: Physics and Observations."
    - HEASARC Guidelines for FITS Event List Formats.
    <br><br>
    """

    eventlist_read_content = """
    ## Reading EventList

    The `EventList.read` method is used to read event data files and load them as `EventList` objects in Stingray. 
    This process involves parsing photon event data, such as arrival times, PI (Pulse Invariant) channels, and energy values.

    ### Supported File Formats
    - **`pickle`**: Serialized Python objects (not recommended for long-term storage).
    - **`hea`** / **`ogip`**: FITS event files (commonly used in X-ray astronomy).
    - **Other Table-supported formats**: e.g., `hdf5`, `ascii.ecsv`, etc.

    ### Parameters
    - **`filename` (str)**: Path to the file containing the event data.
    - **`fmt` (str)**: File format. Supported formats include:
      - `'pickle'`
      - `'hea'` or `'ogip'`
      - Table-compatible formats like `'hdf5'`, `'ascii.ecsv'`.
      - If `fmt` is not specified, the method attempts to infer the format based on the file extension.
    - **`rmf_file` (str, default=None)**:
      - Path to the RMF (Response Matrix File) for energy calibration.
      - Behavior:
        1. **If `fmt="hea"` or `fmt="ogip"`**:
           - `rmf_file` is ignored during the `read` process.
           - You must apply it manually after loading using `convert_pi_to_energy`.
        2. **If `fmt` is not `hea` or `ogip`**:
           - `rmf_file` can be directly specified in the `read` method for automatic energy calibration.
    - **`kwargs` (dict)**:
      - Additional parameters passed to the FITS reader (`load_events_and_gtis`) for reading OGIP/HEASOFT-compatible event lists.
      - Example: `additional_columns` for specifying extra data columns to read.

    ### Attributes in the Loaded EventList
    - **`time`**: Array of photon arrival times in seconds relative to `mjdref`.
    - **`energy`**: Array of photon energy values (if calibrated using `rmf_file`).
    - **`pi`**: Array of Pulse Invariant (PI) channels.
    - **`mjdref`**: Reference time (Modified Julian Date).
    - **`gtis`**: Good Time Intervals, defining valid observation periods.

    ### Stingray Classes and Functions in Use
    Below are the key classes and methods from Stingray that are used during this process:

    #### Class: `EventList`
    ```python
    from stingray.events import EventList

    class EventList:
        def __init__(self, time=None, energy=None, pi=None, gti=None, mjdref=0, rmf_file=None):
            # Initializes the event list with time, energy, PI channels, and other parameters
    ```

    #### Method: `EventList.read`
    ```python
    @classmethod
    def read(cls, filename, fmt=None, rmf_file=None, **kwargs):
        if fmt in ("hea", "ogip"):
            evt = FITSTimeseriesReader(filename, output_class=EventList, **kwargs)[:]
            if rmf_file:
                evt.convert_pi_to_energy(rmf_file)  # Must be applied manually for hea/ogip
            return evt
        return super().read(filename, fmt=fmt)
    ```

    #### Function: `convert_pi_to_energy`
    ```python
    def convert_pi_to_energy(self, rmf_file):
        self.energy = pi_to_energy(self.pi, rmf_file)
    ```

    ### Example Usage
    ```python
    from stingray.events import EventList

    # Reading an OGIP-compatible FITS file
    event_list = EventList.read("example.evt", fmt="ogip")

    # Applying RMF manually after reading
    event_list.convert_pi_to_energy("example.rmf")

    # Reading an HDF5 file with direct RMF calibration
    event_list = EventList.read("example.hdf5", fmt="hdf5", rmf_file="example.rmf")

    # Accessing attributes
    print(event_list.time)     # Photon arrival times
    print(event_list.energy)   # Calibrated energy values (if rmf_file used)
    print(event_list.pi)       # PI channels
    print(event_list.gtis)     # Good Time Intervals
    ```

    ### Important Notes
    1. **FITS Event Files (`hea` or `ogip`)**:
       - `rmf_file` must be applied manually after loading:
         ```python
         event_list.convert_pi_to_energy("example.rmf")
         ```
    2. **Energy Calibration**:
       - Ensure the file contains PI channel data for energy calibration.
       - Without PI channels, RMF calibration will not work, and energy values will remain `None`.
    3. **Good Time Intervals (GTIs)**:
       - GTIs define valid observation periods and are automatically extracted from compatible files.

    ### Common Issues
    - **Unsupported File Format**:
      Ensure the file extension and format (`fmt`) match.
    - **Energy Not Calibrated**:
      Check for PI channels and provide an RMF file if needed.
    - **Missing Columns**:
      For OGIP/HEASOFT-compatible files, ensure required columns (e.g., `time`, `PI`) are available.

    ### Additional Parameters for Advanced Use
    - **`additional_columns`**:
      Specify extra columns to read from the file.
      Example:
      ```python
      event_list = EventList.read("example.fits", fmt="hea", additional_columns=["detector_id"])
      ```
      
      <br><br>
    """

    # Create the help box
    return HelpBox(
        title="Help Section",
        tabs_content={
            "Event Lists": pn.pane.Markdown(intro_content),
            "Reading EventList": pn.pane.Markdown(eventlist_read_content),
        },
    )


def create_eventlist_plots_area():
    """
    Create the plots area for the data loading tab.

    Returns:
        PlotsContainer: An instance of PlotsContainer with the plots for the data loading tab.

    Example:
        >>> plots_area = create_loadingdata_plots_area()
        >>> isinstance(plots_area, PlotsContainer)
        True
    """
    return PlotsContainer()
