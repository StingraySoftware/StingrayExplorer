"""
Data service for EventList operations.

This service handles all EventList-related business logic including:
- Loading event lists from files and URLs
- Saving event lists to disk
- Validating and managing event list names
- Interfacing with StateManager for persistence
"""

from typing import Dict, Any, Optional, List
import os
import tempfile
import requests
from stingray import EventList
from .base_service import BaseService
from utils.performance_monitor import performance_monitor


class DataService(BaseService):
    """
    Service for EventList data operations.

    Handles loading, saving, and managing event lists without any UI dependencies.
    All operations return standardized result dictionaries.
    """

    def load_event_list(
        self,
        file_path: str,
        name: str,
        fmt: str = "ogip",
        rmf_file: Optional[str] = None,
        additional_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Load an EventList from a file.

        Args:
            file_path: Path to the event file
            name: Name to assign to the loaded event list
            fmt: File format (ogip, hdf5, hea, etc.)
            rmf_file: Optional path to RMF file
            additional_columns: Optional list of additional columns to read

        Returns:
            Result dictionary with:
                - success: True if loaded successfully
                - data: The loaded EventList object
                - message: User-friendly status message
                - error: Technical error message if failed

        Example:
            >>> result = data_service.load_event_list(
            ...     file_path="/path/to/obs.evt",
            ...     name="observation_1",
            ...     fmt="ogip"
            ... )
            >>> if result["success"]:
            ...     event_list = result["data"]
        """
        with performance_monitor.track_operation("load_event_list", file_path=file_path, fmt=fmt):
            try:
                # Validate the name doesn't already exist
                if self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"An event list with the name '{name}' already exists. Please use a different name.",
                        error=None
                    )

                # Load the event list using Stingray
                event_list = EventList.read(
                    file_path,
                    fmt=fmt,
                    rmf_file=rmf_file,
                    additional_columns=additional_columns
                )

                # Add to state manager
                self.state.add_event_data(name, event_list)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message=f"EventList '{name}' loaded successfully from '{file_path}' (format: {fmt})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Loading event list",
                    file_path=file_path,
                    name=name,
                    fmt=fmt
                )

    def load_event_list_from_url(
        self,
        url: str,
        name: str,
        fmt: str = "ogip"
    ) -> Dict[str, Any]:
        """
        Load an EventList from a URL.

        Downloads the file to a temporary location, then loads it.

        Args:
            url: URL to download the event file from
            name: Name to assign to the loaded event list
            fmt: File format (ogip, hdf5, hea, etc.)

        Returns:
            Result dictionary

        Example:
            >>> result = data_service.load_event_list_from_url(
            ...     url="https://example.com/data.evt",
            ...     name="remote_obs",
            ...     fmt="ogip"
            ... )
        """
        with performance_monitor.track_operation("load_event_list_from_url", url=url, fmt=fmt):
            try:
                # Validate the name doesn't already exist
                if self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"An event list with the name '{name}' already exists. Please use a different name.",
                        error=None
                    )

                # Download file to temporary location
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tmp_file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            tmp_file.write(chunk)
                    temp_filename = tmp_file.name

                # Load the event list
                event_list = EventList.read(temp_filename, fmt)

                # Clean up temporary file
                os.remove(temp_filename)

                # Add to state manager
                self.state.add_event_data(name, event_list)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message=f"EventList '{name}' loaded successfully from URL (format: {fmt})"
                )

            except requests.RequestException as e:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Failed to download file from URL: {str(e)}",
                    error=str(e)
                )
            except Exception as e:
                return self.handle_error(
                    e,
                    "Loading event list from URL",
                    url=url,
                    name=name,
                    fmt=fmt
                )

    def save_event_list(
        self,
        name: str,
        file_path: str,
        fmt: str = "ogip"
    ) -> Dict[str, Any]:
        """
        Save an EventList to disk.

        Args:
            name: Name of the event list in state
            file_path: Path where to save the file
            fmt: File format to save as

        Returns:
            Result dictionary

        Example:
            >>> result = data_service.save_event_list(
            ...     name="observation_1",
            ...     file_path="/path/to/save/obs.hdf5",
            ...     fmt="hdf5"
            ... )
        """
        with performance_monitor.track_operation("save_event_list", name=name, file_path=file_path, fmt=fmt):
            try:
                # Get the event list from state
                if not self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"No event list found with name '{name}'",
                        error=None
                    )

                event_list = self.state.get_event_data(name)

                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Save based on format
                if fmt == "hdf5":
                    event_list.to_astropy_table().write(
                        file_path,
                        format=fmt,
                        path="data"
                    )
                else:
                    event_list.write(file_path, fmt)

                return self.create_result(
                    success=True,
                    data=file_path,
                    message=f"EventList '{name}' saved successfully to '{file_path}' (format: {fmt})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Saving event list",
                    name=name,
                    file_path=file_path,
                    fmt=fmt
                )

    def delete_event_list(self, name: str) -> Dict[str, Any]:
        """
        Delete an EventList from state.

        Args:
            name: Name of the event list to delete

        Returns:
            Result dictionary

        Example:
            >>> result = data_service.delete_event_list("observation_1")
        """
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"No event list found with name '{name}'",
                    error=None
                )

            self.state.remove_event_data(name)

            return self.create_result(
                success=True,
                data=name,
                message=f"EventList '{name}' deleted successfully"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Deleting event list",
                name=name
            )

    def get_event_list(self, name: str) -> Dict[str, Any]:
        """
        Retrieve an EventList from state.

        Args:
            name: Name of the event list to retrieve

        Returns:
            Result dictionary with the EventList as data

        Example:
            >>> result = data_service.get_event_list("observation_1")
            >>> if result["success"]:
            ...     event_list = result["data"]
        """
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"No event list found with name '{name}'",
                    error=None
                )

            event_list = self.state.get_event_data(name)

            return self.create_result(
                success=True,
                data=event_list,
                message=f"EventList '{name}' retrieved successfully"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Retrieving event list",
                name=name
            )

    def list_event_lists(self) -> Dict[str, Any]:
        """
        List all loaded EventLists.

        Returns:
            Result dictionary with list of (name, event_list) tuples as data

        Example:
            >>> result = data_service.list_event_lists()
            >>> if result["success"]:
            ...     for name, event_list in result["data"]:
            ...         print(f"EventList: {name}")
        """
        try:
            event_data = self.state.get_event_data()

            return self.create_result(
                success=True,
                data=event_data,
                message=f"Found {len(event_data)} event list(s)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Listing event lists"
            )

    def validate_event_list_name(self, name: str) -> Dict[str, Any]:
        """
        Validate that an event list name is valid and doesn't already exist.

        Args:
            name: Name to validate

        Returns:
            Result dictionary with success=True if valid

        Example:
            >>> result = data_service.validate_event_list_name("new_obs")
            >>> if result["success"]:
            ...     # Name is valid and unique
            ...     pass
        """
        if not name or not name.strip():
            return self.create_result(
                success=False,
                data=None,
                message="Event list name cannot be empty",
                error=None
            )

        if self.state.has_event_data(name):
            return self.create_result(
                success=False,
                data=None,
                message=f"An event list with the name '{name}' already exists",
                error=None
            )

        return self.create_result(
            success=True,
            data=name,
            message=f"Name '{name}' is valid and available"
        )
