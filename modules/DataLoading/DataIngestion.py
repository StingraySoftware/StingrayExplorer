# Standard Imports
import os
import stat
import numpy as np
import warnings
from bokeh.models import Tooltip


# HoloViz Imports
import panel as pn

# Stingray Imports
from stingray.events import EventList
from stingray import Lightcurve
from stingray.io import get_file_extension

# Dashboard Classes and Event Data Imports
from utils.globals import loaded_event_data, loaded_light_curve
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    WarningHandler,
    PlotsContainer,
)

# Strings Imports
from utils.strings import LOADING_DATA_HELP_BOX_STRING



# Path to the topmost directory for loaded data
loaded_data_path = os.path.join(os.getcwd(), "files", "loaded-data")

# Create the loaded-data directory if it doesn't exist
os.makedirs(loaded_data_path, exist_ok=True)


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


def create_loadingdata_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    """
    Create the header for the data loading section.

    Args:
        header_container: The container for the header.
        main_area_container: The container for the main content area.
        output_box_container: The container for the output messages.
        warning_box_container: The container for warning messages.
        plots_container: The container for plots.
        help_box_container: The container for the help section.
        footer_container: The container for the footer.

    Returns:
        MainHeader: An instance of MainHeader with the specified heading.

    Example:
        >>> header = create_loadingdata_header(header_container, main_area_container, ...)
        >>> header.heading.value
        'Data Ingestion and creation'
    """
    home_heading_input = pn.widgets.TextInput(
        name="Heading", value="Data Ingestion"
    )
    return MainHeader(heading=home_heading_input)


""" Output Box Section """


def create_loadingdata_output_box(content):
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


def create_loadingdata_warning_box(content):
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


def read_event_data(
    event,
    file_selector,
    filename_input,
    format_input,
    format_checkbox,
    rmf_file_dropper,
    additional_columns_input,
    output_box_container,
    warning_box_container,
    warning_handler,
):
    """
    Load event data from selected files.

    Args:
        event: The event object triggering the function.
        file_selector (FileSelector): The file selector widget.
        filename_input (TextInput): The input widget for filenames.
        format_input (TextInput): The input widget for formats.
        format_checkbox (Checkbox): The checkbox for default format.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Side effects:
        - Modifies the global `loaded_event_data` list.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the output box if file loading fails.

    Restrictions:
        - Requires that the number of formats matches the number of files unless default format is used.

    Example:
        >>> read_event_data(event, file_selector, filename_input, format_input, format_checkbox, ...)
        >>> len(loaded_event_data)
        1  # Assuming one file was loaded
    """
    if not file_selector.value:
        output_box_container[:] = [
            create_loadingdata_output_box(
                "No file selected. Please select a file to upload."
            )
        ]
        return

    file_paths = file_selector.value
    filenames = (
        [name.strip() for name in filename_input.value.split(",")]
        if filename_input.value
        else []
    )
    formats = (
        [fmt.strip() for fmt in format_input.value.split(",")]
        if format_input.value
        else []
    )

    if format_checkbox.value:
        formats = ["ogip" for _ in range(len(file_paths))]

    if len(filenames) < len(file_paths):
        filenames.extend(
            [
                os.path.basename(path).split(".")[0]
                for path in file_paths[len(filenames):]
            ]
        )
    if len(formats) < len(file_paths):
        output_box_container[:] = [
            create_loadingdata_output_box(
                "Please specify formats for all files or check the default format option."
            )
        ]
        return

def read_event_data(
    event,
    file_selector,
    filename_input,
    format_input,
    format_checkbox,
    rmf_file_dropper,
    additional_columns_input,
    output_box_container,
    warning_box_container,
    warning_handler,
):
    """
    Load event data from selected files with extended EventList.read functionality,
    supporting FileDropper for RMF files and additional columns.
    """
    # Validation for required inputs
    if not file_selector.value:
        output_box_container[:] = [
            create_loadingdata_output_box(
                "No file selected. Please select a file to upload."
            )
        ]
        return

    file_paths = file_selector.value
    filenames = (
        [name.strip() for name in filename_input.value.split(",")]
        if filename_input.value
        else []
    )
    formats = (
        [fmt.strip() for fmt in format_input.value.split(",")]
        if format_input.value
        else []
    )

    if format_checkbox.value:
        formats = ["ogip" for _ in range(len(file_paths))]

    # Retrieve the RMF file from FileDropper (if any)
    if rmf_file_dropper.value:
        rmf_file = rmf_file_dropper.value

    # Parse additional columns
    additional_columns = (
        [col.strip() for col in additional_columns_input.value.split(",")]
        if additional_columns_input.value
        else None
    )

    try:
        loaded_files = []
        for file_path, file_name, file_format in zip(file_paths, filenames, formats):
            if any(file_name == event[0] for event in loaded_event_data):
                output_box_container[:] = [
                    create_loadingdata_output_box(
                        f"A file with the name '{file_name}' already exists in memory. Please provide a different name."
                    )
                ]
                return
            # Handle rmf_file separately for 'hea' or 'ogip' formats
            if file_format in ("hea", "ogip"):
                event_list = EventList.read(file_path, fmt=file_format, additional_columns=additional_columns)
            else:
                # Directly pass rmf_file content for other formats
                event_list = EventList.read(file_path, fmt=file_format, rmf_file=rmf_file,additional_columns=additional_columns)
            loaded_event_data.append((file_name, event_list))
            loaded_files.append(
                f"File '{file_path}' loaded successfully as '{file_name}' with format '{file_format}'."
            )
        output_box_container[:] = [
            create_loadingdata_output_box("\n".join(loaded_files))
        ]
        if warning_handler.warnings:
            warning_box_container[:] = [
                create_loadingdata_warning_box("\n".join(warning_handler.warnings))
            ]
        else:
            warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]
    except Exception as e:
        output_box_container[:] = [
            create_loadingdata_output_box(f"An error occurred: {e}")
        ]

    # Clear the warnings after displaying them
    warning_handler.warnings.clear()


def save_loaded_files(
    event,
    filename_input,
    format_input,
    format_checkbox,
    output_box_container,
    warning_box_container,
    warning_handler,
):
    """
    Save loaded event data to specified file formats.

    Args:
        event: The event object triggering the function.
        filename_input (TextInput): The input widget for filenames.
        format_input (TextInput): The input widget for formats.
        format_checkbox (Checkbox): The checkbox for default format.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Side effects:
        - Saves files to disk in the specified formats.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if file saving fails.

    Restrictions:
        - Requires that the number of filenames and formats matches the number of loaded files unless default format is used.

    Example:
        >>> save_loaded_files(event, filename_input, format_input, format_checkbox, ...)
        >>> os.path.exists('/path/to/saved/file.hdf5')
        True  # Assuming the file was saved successfully
    """
    if not loaded_event_data:
        output_box_container[:] = [
            create_loadingdata_output_box("No files loaded to save.")
        ]
        return

    filenames = (
        [name.strip() for name in filename_input.value.split(",")]
        if filename_input.value
        else [event[0] for event in loaded_event_data]
    )
    formats = (
        [fmt.strip() for fmt in format_input.value.split(",")]
        if format_input.value
        else []
    )

    if format_checkbox.value:
        formats = ["hdf5" for _ in range(len(loaded_event_data))]

    if len(filenames) < len(loaded_event_data):
        output_box_container[:] = [
            create_loadingdata_output_box("Please specify names for all loaded files.")
        ]
        return
    if len(filenames) != len(loaded_event_data):
        output_box_container[:] = [
            create_loadingdata_output_box(
                "Please ensure that the number of names matches the number of loaded files."
            )
        ]
        return
    if len(formats) < len(loaded_event_data):
        output_box_container[:] = [
            create_loadingdata_output_box(
                "Please specify formats for all loaded files or check the default format option."
            )
        ]
        return

    saved_files = []
    try:
        for (loaded_name, event_list), file_name, file_format in zip(
            loaded_event_data, filenames, formats
        ):
            if os.path.exists(
                os.path.join(loaded_data_path, f"{file_name}.{file_format}")
            ):
                output_box_container[:] = [
                    create_loadingdata_output_box(
                        f"A file with the name '{file_name}' already exists. Please provide a different name."
                    )
                ]
                return

            save_path = os.path.join(loaded_data_path, f"{file_name}.{file_format}")
            if file_format == "hdf5":
                event_list.to_astropy_table().write(
                    save_path, format=file_format, path="data"
                )
            else:
                event_list.write(save_path, file_format)

            saved_files.append(
                f"File '{file_name}' saved successfully to '{save_path}'."
            )

        output_box_container[:] = [
            create_loadingdata_output_box("\n".join(saved_files))
        ]
        if warning_handler.warnings:
            warning_box_container[:] = [
                create_loadingdata_warning_box("\n".join(warning_handler.warnings))
            ]
        else:
            warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]
    except Exception as e:
        warning_box_container[:] = [
            create_loadingdata_warning_box(f"An error occurred while saving files: {e}")
        ]

    # Clear the warnings after displaying them
    warning_handler.warnings.clear()


def delete_selected_files(
    event,
    file_selector,
    warning_box_container,
    output_box_container,
    warning_handler,
):
    """
    Delete selected files from the file system.

    Args:
        event: The event object triggering the function.
        file_selector (FileSelector): The file selector widget.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Side effects:
        - Deletes files from the file system.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if file deletion fails.

    Restrictions:
        - Cannot delete `.py` files for safety reasons.

    Example:
        >>> delete_selected_files(event, file_selector, warning_box_container, output_box_container, warning_handler)
        >>> os.path.exists('/path/to/deleted/file')
        False  # Assuming the file was deleted successfully
    """
    
    # Define allowed extensions for deletion
    allowed_extensions = {
        ".pkl", ".pickle", ".fits", ".evt", ".h5", ".hdf5",
        ".ecsv", ".txt", ".dat", ".csv", ".vot", ".tex", ".html", ".gz"
    }
    if not file_selector.value:
        output_box_container[:] = [
            create_loadingdata_output_box(
                "No file selected. Please select a file to delete."
            )
        ]
        return

    file_paths = file_selector.value
    deleted_files = []
    for file_path in file_paths:
        
        if not any(file_path.endswith(ext) for ext in allowed_extensions):
            deleted_files.append(
                f"Cannot delete file '{file_path}': File type is not allowed for deletion."
            )
            continue

        try:
            # Change the file permissions to ensure it can be deleted
            os.chmod(file_path, stat.S_IWUSR | stat.S_IREAD | stat.S_IWRITE)
            os.remove(file_path)
            deleted_files.append(f"File '{file_path}' deleted successfully.")
        except Exception as e:
            deleted_files.append(f"An error occurred while deleting '{file_path}': {e}")
    output_box_container[:] = [create_loadingdata_output_box("\n".join(deleted_files))]
    if warning_handler.warnings:
        warning_box_container[:] = [
            create_loadingdata_warning_box("\n".join(warning_handler.warnings))
        ]
    else:
        warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]

    warning_handler.warnings.clear()


def preview_loaded_files(
    event,
    output_box_container,
    warning_box_container,
    warning_handler,
    time_limit=10,
):
    """
    Preview the loaded event data files and light curves.

    Args:
        event: The event object triggering the function.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.
        time_limit (int): The number of time entries to preview.

    Side Effects:
        Updates the output and warning containers with preview information.

    Exceptions:
        Captures exceptions and displays them in the warning box.

    Restrictions:
        None.

    Example:
        >>> preview_loaded_files(event, output_box_container, warning_box_container, warning_handler)
        "Event List - my_event_list:\nTimes (first 10): [0.1, 0.2, ...]\nMJDREF: 58000"
    """
    preview_data = []

    # Preview EventList data
    if loaded_event_data:
        for file_name, event_list in loaded_event_data:
            try:
                time_data = f"Times (first {time_limit}): {event_list.time[:time_limit]}"
                mjdref = f"MJDREF: {event_list.mjdref}"
                gti = f"GTI: {event_list.gti}"
                pi_data = (
                    f"PI (first {time_limit}): {event_list.pi[:time_limit]}"
                    if event_list.pi is not None
                    else "PI: Not available"
                )
                energy_data = (
                    f"Energy (first {time_limit}): {event_list.energy[:time_limit]}"
                    if event_list.energy is not None
                    else "Energy: Not available"
                )
                preview_data.append(
                    f"Event List - {file_name}:\n{time_data}\n{mjdref}\n{gti}\n{pi_data}\n{energy_data}\n"
                )
            except Exception as e:
                warning_handler.warn(str(e), category=RuntimeWarning)

    # Preview Lightcurve data
    if loaded_light_curve:
        for lc_name, lightcurve in loaded_light_curve:
            try:
                time_data = f"Times (first {time_limit}): {lightcurve.time[:time_limit]}"
                counts_data = f"Counts (first {time_limit}): {lightcurve.counts[:time_limit]}"
                dt = f"dt: {lightcurve.dt}"
                preview_data.append(f"Light Curve - {lc_name}:\n{time_data}\n{counts_data}\n{dt}\n")
            except Exception as e:
                warning_handler.warn(str(e), category=RuntimeWarning)

    # Display preview data or message if no data available
    if preview_data:
        output_box_container[:] = [
            create_loadingdata_output_box("\n\n".join(preview_data))
        ]
    else:
        output_box_container[:] = [
            create_loadingdata_output_box("No valid files or light curves loaded for preview.")
        ]

    if warning_handler.warnings:
        warning_box_container[:] = [
            create_loadingdata_warning_box("\n".join(warning_handler.warnings))
        ]
    else:
        warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]

    warning_handler.warnings.clear()



def clear_loaded_files(event, output_box_container, warning_box_container):
    """
    Clear all loaded event data files and light curves from memory.

    Args:
        event: The event object triggering the function.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.

    Side effects:
        - Clears the global `loaded_event_data` and `loaded_light_curve` lists.
        - Updates the output and warning containers with messages.

    Exceptions:
        - None.

    Restrictions:
        - None.

    Example:
        >>> clear_loaded_files(event, output_box_container, warning_box_container)
        "Loaded event files have been cleared."
    """
    global loaded_event_data, loaded_light_curve
    event_data_cleared = False
    light_curve_data_cleared = False

    # Clear EventList data
    if loaded_event_data:
        loaded_event_data.clear()
        event_data_cleared = True

    # Clear Lightcurve data
    if loaded_light_curve:
        loaded_light_curve.clear()
        light_curve_data_cleared = True

    # Create appropriate messages based on what was cleared
    messages = []
    if event_data_cleared:
        messages.append("Loaded event files have been cleared.")
    if light_curve_data_cleared:
        messages.append("Loaded light curves have been cleared.")
    if not messages:
        messages.append("No files or light curves loaded to clear.")

    # Update the output and warning containers
    output_box_container[:] = [create_loadingdata_output_box("\n".join(messages))]
    warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]


def create_event_list(
    event,
    times_input,
    energy_input,
    pi_input,
    gti_input,
    mjdref_input,
    name_input,
    output_box_container,
    warning_box_container,
    warning_handler,
):
    """
    Create an event list from user input.

    Args:
        event: The event object triggering the function.
        times_input (TextInput): The input widget for photon arrival times.
        energy_input (TextInput): The input widget for energy values (optional).
        pi_input (TextInput): The input widget for PI values (optional).
        gti_input (TextInput): The input widget for GTIs (optional).
        mjdref_input (TextInput): The input widget for MJDREF value.
        name_input (TextInput): The input widget for the event list name.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Side effects:
        - Creates a new EventList object and adds it to `loaded_event_data`.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if event list creation fails.

    Restrictions:
        - Requires photon arrival times and MJDREF to be provided.

    Example:
        >>> create_event_list(event, times_input, energy_input, pi_input, gti_input, mjdref_input, name_input, ...)
        "Event List created successfully!"
    """
    # Clear previous warnings
    warning_handler.warnings.clear()
    warnings.resetwarnings()

    try:
        if not times_input.value or not mjdref_input.value:
            output_box_container[:] = [
                create_loadingdata_output_box(
                    "Please enter Photon Arrival Times and MJDREF."
                )
            ]
            return

        times = [float(t) for t in times_input.value.split(",")]
        mjdref = float(mjdref_input.value)
        energy = (
            [float(e) for e in energy_input.value.split(",")]
            if energy_input.value
            else None
        )
        pi = [int(p) for p in pi_input.value.split(",")] if pi_input.value else None
        gti = (
            [
                [float(g) for g in interval.split()]
                for interval in gti_input.value.split(";")
            ]
            if gti_input.value
            else None
        )

        if name_input.value:
            name = name_input.value
            if any(name == event[0] for event in loaded_event_data):
                output_box_container[:] = [
                    create_loadingdata_output_box(
                        f"A file with the name '{name}' already exists in memory. Please provide a different name."
                    )
                ]
                return
        else:
            name = f"event_list_{len(loaded_event_data)}"

        event_list = EventList(times, energy=energy, pi=pi, gti=gti, mjdref=mjdref)

        loaded_event_data.append((name, event_list))

        output_box_container[:] = [
            create_loadingdata_output_box(
                f"Event List created successfully!\nSaved as: {name}\nTimes: {event_list.time}\nMJDREF: {event_list.mjdref}\nGTI: {event_list.gti}\nEnergy: {event_list.energy if energy else 'Not provided'}\nPI: {event_list.pi if pi else 'Not provided'}"
            )
        ]
    except ValueError as ve:
        warning_handler.warn(str(ve), category=ValueError)
    except Exception as e:
        warning_handler.warn(str(e), category=RuntimeError)

    if warning_handler.warnings:
        warning_box_container[:] = [
            create_loadingdata_warning_box("\n".join(warning_handler.warnings))
        ]
    else:
        warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]

    warning_handler.warnings.clear()


def simulate_event_list(
    event,
    time_slider,
    count_slider,
    dt_input,
    name_input,
    method_selector,
    output_box_container,
    warning_box_container,
    warning_handler,
):
    """
    Simulate an event list based on user-defined parameters.

    Args:
        event: The event object triggering the function.
        time_slider (IntSlider): The slider for the number of time bins.
        count_slider (IntSlider): The slider for the maximum counts per bin.
        dt_input (FloatSlider): The slider for delta time (dt).
        name_input (TextInput): The input widget for the simulated event list name.
        method_selector (Select): The selector for the simulation method.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Side effects:
        - Creates a simulated EventList object and adds it to `loaded_event_data`.
        - Updates the output and warning containers with messages.

    Exceptions:
        - Displays exceptions in the warning box if simulation fails.

    Restrictions:
        - Requires a unique name for the simulated event list.

    Example:
        >>> simulate_event_list(event, time_slider, count_slider, dt_input, name_input, method_selector, ...)
        "Event List simulated successfully!"
    """
    # Clear previous warnings
    warning_handler.warnings.clear()
    warnings.resetwarnings()

    try:
        if not name_input.value:
            output_box_container[:] = [
                create_loadingdata_output_box(
                    "Please provide a name for the simulated event list."
                )
            ]
            return

        if any(name_input.value == event[0] for event in loaded_event_data):
            output_box_container[:] = [
                create_loadingdata_output_box(
                    f"A file with the name '{name_input.value}' already exists in memory. Please provide a different name."
                )
            ]
            return

        times = np.arange(time_slider.value)
        counts = np.floor(np.random.rand(time_slider.value) * count_slider.value)
        dt = dt_input.value
        lc = Lightcurve(times, counts, dt=dt, skip_checks=True)

        if method_selector.value == "Standard Method":
            event_list = EventList.from_lc(lc)
        else:
            event_list = EventList()
            event_list.simulate_times(lc)

        name = name_input.value
        loaded_event_data.append((name, event_list))

        output_box_container[:] = [
            create_loadingdata_output_box(
                f"Event List simulated successfully!\nSaved as: {name}\nTimes: {event_list.time}\nCounts: {counts}"
            )
        ]

    except Exception as e:
        warning_handler.warn(str(e), category=RuntimeError)

    if warning_handler.warnings:
        warning_box_container[:] = [
            create_loadingdata_warning_box("\n".join(warning_handler.warnings))
        ]
    else:
        warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]

    warning_handler.warnings.clear()


def create_loading_tab(output_box_container, warning_box_container, warning_handler):
    """
    Create the tab for loading event data files.

    Args:
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the loading tab.

    Example:
        >>> tab = create_loading_tab(output_box_container, warning_box_container, warning_handler)
        >>> isinstance(tab, pn.Column)
        True
    """
    
    # Get the user's home directory
    home_directory = os.path.expanduser("~")
    
    file_selector = pn.widgets.FileSelector(
        home_directory, only_files=True, name="Select File", show_hidden=True
    )
    filename_input = pn.widgets.TextInput(
        name="Enter File Names",
        placeholder="Enter file names, comma-separated",
        width=400,
    )
    format_input = pn.widgets.TextInput(
        name="Enter Formats",
        placeholder="Enter formats (e.g., ogip, pickle, hdf5), comma-separated",
        width=400,
    )
    format_checkbox = pn.widgets.Checkbox(
        name="Use default format (\"ogip\" for reading, \"hdf5\" for writing/saving)", value=False
    )
    load_button = pn.widgets.Button(name="Read as EventLists", button_type="primary")
    save_button = pn.widgets.Button(name="Save loaded EventLists", button_type="success")
    delete_button = pn.widgets.Button(
        name="Delete Selected Files", button_type="danger"
    )
    preview_button = pn.widgets.Button(
        name="Preview loaded EventLists", button_type="default"
    )
    clear_button = pn.widgets.Button(name="Clear Loaded EventLists", button_type="warning")

    tooltip_format = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""For HEASoft-supported missions, use 'ogip'. Using 'fits' directly might cause issues with Astropy tables.""",
            position="bottom",
        )
    )

    tooltip_file = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Ensure the file contains at least a 'time' column.""",
            position="bottom",
        )
    )
    
    tooltip_rmf = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Calibrates PI(Pulse invariant) values to physical energy.""",
            position="bottom",
        )
    )
    
    tooltip_additional_columns = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""Any further keyword arguments to be passed for reading in event lists in OGIP/HEASOFT format""", 
            position="bottom",
        )
    )
    
    # FileDropper for RMF file
    rmf_file_dropper = pn.widgets.FileDropper(
        # accepted_filetypes=['.rmf', '.fits'],  # Accept RMF files or compatible FITS files
        multiple=False,  # Only allow a single file
        name="Upload RMF(Response Matrix File) File (optional)",
        max_file_size="1000MB",  # Limit file size
        layout="compact",  # Layout style
    )
    
    additional_columns_input = pn.widgets.TextInput(
    name="Additional Columns (optional)", placeholder="Comma-separated column names"
    )


    def on_load_click(event):
        # Clear previous outputs and warnings
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        read_event_data(
            event,
            file_selector,
            filename_input,
            format_input,
            format_checkbox,
            rmf_file_dropper,
            additional_columns_input,
            output_box_container,
            warning_box_container,
            warning_handler,
        )

    def on_save_click(event):
        # Clear previous outputs and warnings
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        save_loaded_files(
            event,
            filename_input,
            format_input,
            format_checkbox,
            output_box_container,
            warning_box_container,
            warning_handler,
        )

    def on_delete_click(event):
        # Clear previous outputs and warnings
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        delete_selected_files(
            event,
            file_selector,
            warning_box_container,
            output_box_container,
            warning_handler,
        )

    def on_preview_click(event):
        # Clear previous outputs and warnings
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        preview_loaded_files(
            event, output_box_container, warning_box_container, warning_handler
        )

    def on_clear_click(event):
        # Clear the loaded files list
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()
        clear_loaded_files(event, output_box_container, warning_box_container)

    load_button.on_click(on_load_click)
    save_button.on_click(on_save_click)
    delete_button.on_click(on_delete_click)
    preview_button.on_click(on_preview_click)
    clear_button.on_click(on_clear_click)

    first_column = pn.Column(
        pn.Row(pn.pane.Markdown("<h2> Read an EventList object from File</h2>"),pn.widgets.TooltipIcon(value=Tooltip(content="Supported Formats: pickle, hea or ogip, any other astropy.table.Table(ascii.ecsv, hdf5, etc.)", position="bottom"))),
        file_selector,
        pn.Row(filename_input, tooltip_file),
        pn.Row(format_input, tooltip_format),
        format_checkbox,
        pn.Row(rmf_file_dropper, tooltip_rmf),
        pn.Row(additional_columns_input, tooltip_additional_columns),
        pn.Row(load_button, save_button, delete_button),
        pn.Row(preview_button, clear_button),
        pn.pane.Markdown("<br/>"),
        width_policy="min",
    )

    tab_content = pn.Column(
        first_column,
        width_policy="min",
    )

    return tab_content


def create_event_list_tab(output_box_container, warning_box_container, warning_handler):
    """
    Create the tab for creating an event list.

    Args:
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the event list creation tab.

    Example:
        >>> tab = create_event_list_tab(output_box_container, warning_box_container, warning_handler)
        >>> isinstance(tab, pn.Column)
        True
    """
    times_input = pn.widgets.TextInput(
        name="Photon Arrival Times", placeholder="e.g., 0.5, 1.1, 2.2, 3.7"
    )
    mjdref_input = pn.widgets.TextInput(name="MJDREF", placeholder="e.g., 58000.")
    energy_input = pn.widgets.TextInput(
        name="Energy (optional)", placeholder="e.g., 0., 3., 4., 20."
    )
    pi_input = pn.widgets.TextInput(
        name="PI (optional)", placeholder="e.g., 100, 200, 300, 400"
    )
    gti_input = pn.widgets.TextInput(
        name="GTIs (optional)", placeholder="e.g., 0 4; 5 10"
    )
    name_input = pn.widgets.TextInput(
        name="Event List Name", placeholder="e.g., my_event_list"
    )
    create_button = pn.widgets.Button(name="Create Event List", button_type="primary")

    def on_create_button_click(event):
        # Clear previous output and warnings
        output_box_container.clear()
        warning_box_container.clear()
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        create_event_list(
            event,
            times_input,
            energy_input,
            pi_input,
            gti_input,
            mjdref_input,
            name_input,
            output_box_container,
            warning_box_container,
            warning_handler,
        )

    create_button.on_click(on_create_button_click)

    tab_content = pn.Column(
        pn.pane.Markdown("# Create Event List"),
        times_input,
        mjdref_input,
        energy_input,
        pi_input,
        gti_input,
        name_input,
        create_button,
    )
    return tab_content


def create_simulate_event_list_tab(
    output_box_container, warning_box_container, warning_handler
):
    """
    Create the tab for simulating event lists.

    Args:
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the event list simulation tab.

    Example:
        >>> tab = create_simulate_event_list_tab(output_box_container, warning_box_container, warning_handler)
        >>> isinstance(tab, pn.Column)
        True
    """
    simulation_title = pn.pane.Markdown("# Simulating Event Lists")
    time_slider = pn.widgets.IntSlider(
        name="Number of Time Bins", start=1, end=10000, value=10
    )
    count_slider = pn.widgets.IntSlider(
        name="Max Counts per Bin", start=1, end=10000, value=5
    )
    dt_input = pn.widgets.FloatSlider(
        name="Delta Time (dt)", start=0.0001, end=10000.0, step=0.001, value=1.0
    )
    method_selector = pn.widgets.Select(
        name="Method", options=["Standard Method", "Inverse CDF Method"]
    )
    sim_name_input = pn.widgets.TextInput(
        name="Simulated Event List Name", placeholder="e.g., my_sim_event_list"
    )
    simulate_button = pn.widgets.Button(
        name="Simulate Event List", button_type="primary"
    )

    def on_simulate_button_click(event):
        # Clear previous output and warnings
        output_box_container[:] = [create_loadingdata_output_box("N.A.")]
        warning_box_container[:] = [create_loadingdata_warning_box("N.A.")]
        warning_handler.warnings.clear()
        warnings.resetwarnings()

        # Simulate the event list
        simulate_event_list(
            event,
            time_slider,
            count_slider,
            dt_input,
            sim_name_input,
            method_selector,
            output_box_container,
            warning_box_container,
            warning_handler,
        )

    simulate_button.on_click(on_simulate_button_click)

    tab_content = pn.Column(
        simulation_title,
        time_slider,
        count_slider,
        dt_input,
        method_selector,
        sim_name_input,
        simulate_button,
    )
    return tab_content


def create_loadingdata_main_area(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
):
    """
    Create the main area for the data loading tab, including all sub-tabs.

    Args:
        header_container: The container for the header.
        main_area_container: The container for the main content area.
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        plots_container: The container for plots.
        help_box_container: The container for the help section.
        footer_container: The container for the footer.

    Returns:
        MainArea: An instance of MainArea with all the necessary tabs for data loading.

    Example:
        >>> main_area = create_loadingdata_main_area(header_container, main_area_container, ...)
        >>> isinstance(main_area, MainArea)
        True
    """
    warning_handler = create_warning_handler()
    tabs_content = {
        "Read Event List from File": create_loading_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
        ),
        "Create Event List": create_event_list_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
        ),
        "Simulate Event List": create_simulate_event_list_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
        ),
    }
    return MainArea(tabs_content=tabs_content)


def create_loadingdata_help_area():
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



def create_loadingdata_plots_area():
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
