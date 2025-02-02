# Standard Imports
import os
import stat
import copy
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
from stingray import Lightcurve

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
    # TODO: Add better example for create_loading_header()
        Example:
            >>> header = create_loadingdata_header(header_container, main_area_container, ...)
            >>> header.heading.value
            'Data Ingestion and creation'
    """
    home_heading_input = pn.widgets.TextInput(name="Heading", value="Data Ingestion")
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
    # TODO: Add better docstring for read_event_data
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

    # TODO: Add try and except block for error handling during selection of file path and display in warning box
    file_paths = file_selector.value
    filenames = (
        [name.strip() for name in filename_input.value.split(",")]
        if filename_input.value
        else []
    )

    # TODO: Add try and except block for error handling during selection of file format and display in warning box
    formats = (
        [fmt.strip() for fmt in format_input.value.split(",")]
        if format_input.value
        else []
    )

    # Use default format if checkbox is checked
    if format_checkbox.value:
        formats = ["ogip" for _ in range(len(file_paths))]

    # TODO: Add try and except block for error handling during selection of RMF file and display in warning box
    # Retrieve the RMF file from FileDropper (if any)
    if rmf_file_dropper.value:
        rmf_file = list(rmf_file_dropper.value.values())[0]

        # Save the file data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rmf") as tmp_file:
            tmp_file.write(rmf_file)
            tmp_file_path = tmp_file.name

    # TODO: Add try and except block for error handling during selection of additional columns and display in warning box
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
            # EventList read method used from stingray.EventList
            event_list = EventList.read(
                file_path,
                fmt=file_format,
                rmf_file=tmp_file_path if rmf_file_dropper.value else None,
                additional_columns=additional_columns,
            )
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
    # TODO: Add better example
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

    # TODO: ADD checks for valid formats
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


# TODO: ADD better comments, error handlling and docstrings
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
        ".pkl",
        ".pickle",
        ".fits",
        ".evt",
        ".h5",
        ".hdf5",
        ".ecsv",
        ".txt",
        ".dat",
        ".csv",
        ".vot",
        ".tex",
        ".html",
        ".gz",
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


# TODO: ADD better comments, error handlling and docstrings
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

    # Add a summary of loaded files and their names
    if loaded_event_data:
        preview_data.append(
            f"Loaded Event Files: {len(loaded_event_data)}\n"
            f"Event File Names: {[file_name for file_name, _ in loaded_event_data]}\n"
        )
    else:
        preview_data.append("No Event Files Loaded.\n")

    if loaded_light_curve:
        preview_data.append(
            f"Loaded Light Curves: {len(loaded_light_curve)}\n"
            f"Light Curve Names: {[lc_name for lc_name, _ in loaded_light_curve]}\n"
        )
    else:
        preview_data.append("No Light Curves Loaded.\n")

    # Preview EventList data
    if loaded_event_data:
        for file_name, event_list in loaded_event_data:
            try:
                # Gather available attributes dynamically
                attributes = [
                    ("Times (first entries)", event_list.time[:time_limit]),
                    ("Energy (keV)", getattr(event_list, "energy", "Not available")),
                    ("PI Channels", getattr(event_list, "pi", "Not available")),
                    ("MJDREF", event_list.mjdref),
                    ("Good Time Intervals (GTIs)", event_list.gti),
                    ("Mission", getattr(event_list, "mission", "Not available")),
                    ("Instrument", getattr(event_list, "instr", "Not available")),
                    (
                        "Detector IDs",
                        getattr(event_list, "detector_id", "Not available"),
                    ),
                    ("Ephemeris", getattr(event_list, "ephem", "Not available")),
                    ("Time Reference", getattr(event_list, "timeref", "Not available")),
                    ("Time System", getattr(event_list, "timesys", "Not available")),
                    ("Header", getattr(event_list, "header", "Not available")),
                ]

                # Format preview data
                event_preview = "\n\n\n----------------------\n"
                event_preview += f"Event List - {file_name}:\n"

                for attr_name, attr_value in attributes:
                    if isinstance(
                        attr_value, np.ndarray
                    ):  # Show limited entries for arrays
                        attr_value = attr_value[:time_limit]
                    event_preview += f"{attr_name}: {attr_value}\n\n"
                event_preview += "----------------------\n\n\n"
                preview_data.append(event_preview)

            except Exception as e:
                warning_handler.warn(str(e), category=RuntimeWarning)

    # Preview Lightcurve data
    if loaded_light_curve:
        for lc_name, lightcurve in loaded_light_curve:
            try:
                attributes = [
                    ("Times (first entries)", lightcurve.time[:time_limit]),
                    ("Counts (first entries)", lightcurve.counts[:time_limit]),
                    (
                        "Count Errors (first entries)",
                        getattr(lightcurve, "counts_err", "Not available"),
                    ),
                    (
                        "Background Counts",
                        getattr(lightcurve, "bg_counts", "Not available"),
                    ),
                    (
                        "Background Ratio",
                        getattr(lightcurve, "bg_ratio", "Not available"),
                    ),
                    (
                        "Fractional Exposure",
                        getattr(lightcurve, "frac_exp", "Not available"),
                    ),
                    ("Mean Rate", getattr(lightcurve, "meanrate", "Not available")),
                    ("Mean Counts", getattr(lightcurve, "meancounts", "Not available")),
                    ("Number of Points", getattr(lightcurve, "n", "Not available")),
                    ("Time Resolution (dt)", lightcurve.dt),
                    ("MJDREF", lightcurve.mjdref),
                    ("Good Time Intervals (GTIs)", lightcurve.gti),
                    ("Duration (tseg)", getattr(lightcurve, "tseg", "Not available")),
                    (
                        "Start Time (tstart)",
                        getattr(lightcurve, "tstart", "Not available"),
                    ),
                    (
                        "Error Distribution",
                        getattr(lightcurve, "err_dist", "Not available"),
                    ),
                    ("Mission", getattr(lightcurve, "mission", "Not available")),
                    ("Instrument", getattr(lightcurve, "instr", "Not available")),
                ]
                lightcurve_preview = "\n\n----------------------\n"
                lightcurve_preview += f"Light Curve - {lc_name}:\n"

                for attr_name, attr_value in attributes:
                    if isinstance(attr_value, np.ndarray):
                        attr_value = attr_value[:time_limit]
                    lightcurve_preview += f"{attr_name}: {attr_value}\n"
                lightcurve_preview += "----------------------\n\n"
                preview_data.append(lightcurve_preview)
            except Exception as e:
                warning_handler.warn(str(e), category=RuntimeWarning)

    # Display preview data or message if no data available
    if preview_data:
        output_box_container[:] = [
            create_loadingdata_output_box("\n\n".join(preview_data))
        ]
    else:
        output_box_container[:] = [
            create_loadingdata_output_box(
                "No valid files or light curves loaded for preview."
            )
        ]

    if warning_handler.warnings:
        warning_box_container[:] = [
            create_loadingdata_warning_box("\n".join(warning_handler.warnings))
        ]
    else:
        warning_box_container[:] = [create_loadingdata_warning_box("No warnings.")]

    warning_handler.warnings.clear()


# TODO: ADD better comments, error handlling and docstrings
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




# TODO: ADD better comments, error handlling and docstrings
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
        name='Use default format ("ogip" for reading, "hdf5" for writing/saving)',
        value=False,
    )
    load_button = pn.widgets.Button(name="Read as EventLists", button_type="primary")
    save_button = pn.widgets.Button(
        name="Save loaded EventLists", button_type="success"
    )
    delete_button = pn.widgets.Button(
        name="Delete Selected Files", button_type="danger"
    )
    preview_button = pn.widgets.Button(
        name="Preview loaded EventLists", button_type="default"
    )
    clear_button = pn.widgets.Button(
        name="Clear Loaded EventLists", button_type="warning"
    )

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
        pn.Row(
            pn.pane.Markdown("<h2> Read an EventList object from File</h2>"),
            pn.widgets.TooltipIcon(
                value=Tooltip(
                    content="Supported Formats: pickle, hea or ogip, any other astropy.table.Table(ascii.ecsv, hdf5, etc.)",
                    position="bottom",
                )
            ),
        ),
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


# TODO: Add better comments, error handlling and docstrings and increase the functionality
def create_fetch_eventlist_tab(
    output_box_container, warning_box_container, warning_handler
):
    """
    Create the tab for fetching EventList data from a link.

    Args:
        output_box_container (OutputBox): The container for output messages.
        warning_box_container (WarningBox): The container for warning messages.
        warning_handler (WarningHandler): The handler for warnings.

    Returns:
        Column: A Panel Column containing the widgets and layout for the fetch tab.
    """
    link_input = pn.widgets.TextInput(
        name="Enter File Link",
        placeholder="Enter the URL to the EventList file",
        width=400,
    )
    filename_input = pn.widgets.TextInput(
        name="File Name",
        placeholder="Provide a name for the EventList",
        width=400,
    )
    format_select = pn.widgets.Select(
        name="File Format",
        options=["ogip", "hdf5", "ascii.ecsv", "fits", "pickle"],
        value="ogip",
    )
    fetch_button = pn.widgets.Button(
        name="Fetch and Load EventList",
        button_type="primary",
    )
    
    tooltip_link = pn.widgets.TooltipIcon(
        value=Tooltip(
            content="""When using urls from github use raw links.""",
            position="bottom",
        )
    )

    def fetch_eventlist(event):
        if not link_input.value or not filename_input.value:
            output_box_container[:] = [
                create_loadingdata_output_box(
                    "Error: Please provide both the link and file name."
                )
            ]
            return

        try:
            link = link_input.value.strip()

            # Download the file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                temp_filename = tmp_file.name

            response = requests.get(link, stream=True)
            if response.status_code != 200:
                raise ValueError(f"Failed to download file. Status code: {response.status_code}")

            # Save file
            with open(temp_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            # Read the EventList
            event_list = EventList.read(temp_filename, format_select.value)

            # Add to global loaded_event_data
            loaded_event_data.append((filename_input.value.strip(), event_list))

            output_box_container[:] = [
                create_loadingdata_output_box(
                    f"EventList '{filename_input.value}' loaded successfully from link."
                )
            ]
        except Exception as e:
            warning_handler.warn(str(e), category=RuntimeWarning)
            output_box_container[:] = [
                create_loadingdata_output_box(f"Error occurred: {e}")
            ]
        finally:
            # Ensure the temporary file is deleted after processing
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    fetch_button.on_click(fetch_eventlist)

    tab_content = pn.Column(
        pn.pane.Markdown("### Fetch EventList from Link"),
        pn.Row(link_input, tooltip_link),
        filename_input,
        format_select,
        fetch_button,
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
        "Fetch EventList from Link": create_fetch_eventlist_tab(
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
