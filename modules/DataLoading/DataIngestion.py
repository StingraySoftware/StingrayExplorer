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

