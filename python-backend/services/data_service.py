"""
Data service for EventList operations.

Handles loading, saving, and managing event lists.
"""

import os
import tempfile
from typing import Any, Dict, List, Optional

import requests
from stingray import EventList

from .base_service import BaseService


class DataService(BaseService):
    """
    Service for EventList data operations.

    Handles loading, saving, and managing event lists without any UI dependencies.
    """

    def load_event_list(
        self,
        file_path: str,
        name: str,
        fmt: str = "ogip",
        rmf_file: Optional[str] = None,
        additional_columns: Optional[List[str]] = None,
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
            Result dictionary with the EventList data
        """
        try:
            # Validate the name doesn't already exist
            if self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"An event list with the name '{name}' already exists.",
                    error=None,
                )

            # Load the event list using Stingray
            event_list = EventList.read(
                file_path,
                fmt=fmt,
                rmf_file=rmf_file,
                additional_columns=additional_columns,
            )

            # Add to state manager
            self.state.add_event_data(name, event_list)

            # Prepare serializable summary
            summary = {
                "name": name,
                "n_events": len(event_list.time),
                "time_range": [float(event_list.time[0]), float(event_list.time[-1])],
                "has_energy": event_list.energy is not None,
                "has_pi": event_list.pi is not None,
                "gti_count": len(event_list.gti) if event_list.gti is not None else 0,
            }

            return self.create_result(
                success=True,
                data=summary,
                message=f"EventList '{name}' loaded successfully ({len(event_list.time)} events)",
            )

        except Exception as e:
            return self.handle_error(
                e, "Loading event list", file_path=file_path, name=name, fmt=fmt
            )

    def load_event_list_from_url(
        self,
        url: str,
        name: str,
        fmt: str = "ogip",
    ) -> Dict[str, Any]:
        """
        Load an EventList from a URL.

        Args:
            url: URL to download the event file from
            name: Name to assign to the loaded event list
            fmt: File format

        Returns:
            Result dictionary
        """
        try:
            # Validate the name doesn't already exist
            if self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"An event list with the name '{name}' already exists.",
                    error=None,
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

            summary = {
                "name": name,
                "n_events": len(event_list.time),
                "time_range": [float(event_list.time[0]), float(event_list.time[-1])],
            }

            return self.create_result(
                success=True,
                data=summary,
                message=f"EventList '{name}' loaded successfully from URL",
            )

        except requests.RequestException as e:
            return self.create_result(
                success=False,
                data=None,
                message=f"Failed to download file from URL: {str(e)}",
                error=str(e),
            )
        except Exception as e:
            return self.handle_error(
                e, "Loading event list from URL", url=url, name=name, fmt=fmt
            )

    def save_event_list(
        self,
        name: str,
        file_path: str,
        fmt: str = "ogip",
    ) -> Dict[str, Any]:
        """
        Save an EventList to disk.

        Args:
            name: Name of the event list in state
            file_path: Path where to save the file
            fmt: File format to save as

        Returns:
            Result dictionary
        """
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"No event list found with name '{name}'",
                    error=None,
                )

            event_list = self.state.get_event_data(name)

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save based on format
            if fmt == "hdf5":
                event_list.to_astropy_table().write(
                    file_path, format=fmt, path="data"
                )
            else:
                event_list.write(file_path, fmt)

            return self.create_result(
                success=True,
                data={"file_path": file_path},
                message=f"EventList '{name}' saved to '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e, "Saving event list", name=name, file_path=file_path, fmt=fmt
            )

    def delete_event_list(self, name: str) -> Dict[str, Any]:
        """Delete an EventList from state."""
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"No event list found with name '{name}'",
                    error=None,
                )

            self.state.remove_event_data(name)

            return self.create_result(
                success=True,
                data={"name": name},
                message=f"EventList '{name}' deleted successfully",
            )

        except Exception as e:
            return self.handle_error(e, "Deleting event list", name=name)

    def get_event_list_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about an EventList.

        Args:
            name: Name of the event list

        Returns:
            Result dictionary with event list information
        """
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"No event list found with name '{name}'",
                    error=None,
                )

            event_list = self.state.get_event_data(name)

            info = {
                "name": name,
                "n_events": len(event_list.time),
                "time_range": [float(event_list.time[0]), float(event_list.time[-1])],
                "duration": float(event_list.time[-1] - event_list.time[0]),
                "has_energy": event_list.energy is not None,
                "has_pi": event_list.pi is not None,
                "gti_count": len(event_list.gti) if event_list.gti is not None else 0,
                "mjdref": float(event_list.mjdref) if event_list.mjdref else None,
            }

            return self.create_result(
                success=True,
                data=info,
                message=f"EventList '{name}' info retrieved",
            )

        except Exception as e:
            return self.handle_error(e, "Getting event list info", name=name)

    def list_event_lists(self) -> Dict[str, Any]:
        """List all loaded EventLists."""
        try:
            event_data = self.state.get_event_data()

            summaries = []
            for name, event_list in event_data:
                summaries.append({
                    "name": name,
                    "n_events": len(event_list.time),
                    "time_range": [float(event_list.time[0]), float(event_list.time[-1])],
                })

            return self.create_result(
                success=True,
                data=summaries,
                message=f"Found {len(summaries)} event list(s)",
            )

        except Exception as e:
            return self.handle_error(e, "Listing event lists")

    def check_file_size(self, file_path: str) -> Dict[str, Any]:
        """Check file size and provide loading recommendations."""
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024**2)
            file_size_gb = file_size / (1024**3)

            # Determine risk level
            if file_size_gb > 10:
                risk_level = "critical"
            elif file_size_gb > 5:
                risk_level = "risky"
            elif file_size_gb > 1:
                risk_level = "caution"
            else:
                risk_level = "safe"

            recommend_lazy = file_size_gb > 1.0 or risk_level in ["caution", "risky", "critical"]

            return self.create_result(
                success=True,
                data={
                    "file_size_bytes": file_size,
                    "file_size_mb": file_size_mb,
                    "file_size_gb": file_size_gb,
                    "risk_level": risk_level,
                    "recommend_lazy": recommend_lazy,
                },
                message=f"File size: {file_size_mb:.2f} MB, Risk: {risk_level}",
            )

        except Exception as e:
            return self.handle_error(e, "Checking file size", file_path=file_path)
