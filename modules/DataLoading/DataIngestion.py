import panel as pn
from stingray.events import EventList
from stingray import Lightcurve
import asyncio
import warnings
import os
import stat
import numpy as np
from bokeh.models import Tooltip
from .globals import loaded_event_data
from utils.dashboardClasses import MainHeader, MainArea, OutputBox, WarningBox, BokehPlotsContainer, HelpBox, Footer

# Path to the topmost directory for loaded-data
loaded_data_path = os.path.join(os.getcwd(), "files", "loaded-data")

# Create the loaded-data directory if it doesn't exist
os.makedirs(loaded_data_path, exist_ok=True)

# Custom warning handler
class WarningHandler:
    def __init__(self):
        self.warnings = []

    def warn(
        self, message, category=None, filename=None, lineno=None, file=None, line=None
    ):
        warning_message = f"Message: {message}\nCategory: {category.__name__ if category else 'N/A'}\nFile: {filename if filename else 'N/A'}\nLine: {lineno if lineno else 'N/A'}\n"
        self.warnings.append(warning_message)


# Create an instance of the warning handler
warning_handler = WarningHandler()

# Redirect warnings to the custom handler
warnings.showwarning = warning_handler.warn


async def load_event_data(
    event,
    file_selector,
    filename_input,
    format_input,
    format_checkbox,
    output,
    warning_output,
):
    if not file_selector.value:
        output.value = "No file selected. Please select a file to upload."
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
                for path in file_paths[len(filenames) :]
            ]
        )
    if len(formats) < len(file_paths):
        output.value = (
            "Please specify formats for all files or check the default format option."
        )
        return

    try:
        loaded_files = []
        loop = asyncio.get_event_loop()
        for file_path, file_name, file_format in zip(file_paths, filenames, formats):
            if any(file_name == event[0] for event in loaded_event_data):
                output.value = f"A file with the name '{file_name}' already exists in memory. Please provide a different name."
                return

            event_list = await loop.run_in_executor(
                None, EventList.read, file_path, file_format
            )
            loaded_event_data.append((file_name, event_list))
            loaded_files.append(
                f"File '{file_path}' loaded successfully as '{file_name}' with format '{file_format}'."
            )

        output.value = "\n".join(loaded_files)
        if warning_handler.warnings:
            warning_output.value = "\n".join(warning_handler.warnings)
        else:
            warning_output.value = "No warnings."
    except Exception as e:
        output.value = f"An error occurred: {e}"

    # Clear the warnings after displaying them
    warning_handler.warnings.clear()

def save_loaded_files(
    event, filename_input, format_input, format_checkbox, output, warning_output
):
    if not loaded_event_data:
        output.value = "No files loaded to save."
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
        output.value = "Please specify names for all loaded files."
        return
    if len(filenames) != len(loaded_event_data):
        output.value = (
            "Please ensure that the number of names matches the number of loaded files."
        )
        return
    if len(formats) < len(loaded_event_data):
        output.value = "Please specify formats for all loaded files or check the default format option."
        return

    saved_files = []
    try:
        for (loaded_name, event_list), file_name, file_format in zip(
            loaded_event_data, filenames, formats
        ):
            if os.path.exists(
                os.path.join(loaded_data_path, f"{file_name}.{file_format}")
            ):
                output.value = f"A file with the name '{file_name}' already exists. Please provide a different name."
                return

            save_path = os.path.join(loaded_data_path, f"{file_name}.{file_format}")
            if file_format == 'hdf5':
                event_list.to_astropy_table().write(save_path, format=file_format, path='data')
            else:
                event_list.write(save_path, file_format)

            saved_files.append(
                f"File '{file_name}' saved successfully to '{save_path}'."
            )

        output.value = "\n".join(saved_files)
        if warning_handler.warnings:
            warning_output.value = "\n".join(warning_handler.warnings)
        else:
            warning_output.value = "No warnings."
    except Exception as e:
        output.value = f"An error occurred while saving files: {e}"

    # Clear the warnings after displaying them
    warning_handler.warnings.clear()



def delete_selected_files(event, file_selector, output, warning_output):
    if not file_selector.value:
        output.value = "No file selected. Please select a file to delete."
        return

    file_paths = file_selector.value
    deleted_files = []
    for file_path in file_paths:
        if file_path.endswith(".py"):
            deleted_files.append(
                f"Cannot delete file '{file_path}': Deleting .py files is not allowed."
            )
            continue

        try:
            # Change the file permissions to ensure it can be deleted
            os.chmod(file_path, stat.S_IWUSR | stat.S_IREAD | stat.S_IWRITE)
            os.remove(file_path)
            deleted_files.append(f"File '{file_path}' deleted successfully.")
        except Exception as e:
            deleted_files.append(f"An error occurred while deleting '{file_path}': {e}")

    output.value = "\n".join(deleted_files)
    if warning_handler.warnings:
        warning_output.value = "\n".join(warning_handler.warnings)
    else:
        warning_output.value = "No warnings."

    warning_handler.warnings.clear()


def preview_loaded_files(event, output, warning_output, time_limit=10):
    if not loaded_event_data:
        output.value = "No files loaded to preview."
        return

    preview_data = []
    for file_name, event_list in loaded_event_data:
        try:
            time_data = f"Times (first {time_limit}): {event_list.time[:time_limit]}"
            mjdref = f"MJDREF: {event_list.mjdref}"
            gti = f"GTI: {event_list.gti}"
            preview_data.append(f"File: {file_name}\n{time_data}\n{mjdref}\n{gti}\n")
        except Exception as e:
            warning_handler.warn(str(e), category=RuntimeWarning)

    if preview_data:
        output.value = "\n\n".join(preview_data)
    else:
        output.value = "No valid files loaded for preview."

    if warning_handler.warnings:
        warning_output.value = "\n".join(warning_handler.warnings)
    else:
        warning_output.value = "No warnings."

    warning_handler.warnings.clear()