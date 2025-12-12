"""
Data service for EventList operations.

This service handles all EventList-related business logic including:
- Loading event lists from files and URLs
- Saving event lists to disk
- Validating and managing event list names
- Interfacing with StateManager for persistence
- Lazy loading for large files (memory-efficient)
"""

from typing import Dict, Any, Optional, List
import os
import tempfile
import requests
from stingray import EventList
from .base_service import BaseService
from utils.performance_monitor import performance_monitor
from utils.lazy_loader import LazyEventLoader, assess_loading_risk


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

    def check_file_size(self, file_path: str) -> Dict[str, Any]:
        """
        Check file size and assess loading risk.

        Args:
            file_path: Path to the file

        Returns:
            Result dictionary with:
                - file_size_mb: File size in megabytes
                - file_size_gb: File size in gigabytes
                - risk_level: 'safe', 'caution', 'risky', or 'critical'
                - recommend_lazy: Boolean suggesting lazy loading
                - memory_info: System memory information

        Example:
            >>> result = data_service.check_file_size("/path/to/large.evt")
            >>> if result["data"]["recommend_lazy"]:
            ...     # Use lazy loading
            ...     pass
        """
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024**2)
            file_size_gb = file_size / (1024**3)

            # Assess risk
            risk_level = assess_loading_risk(file_size, file_format='fits')

            # Recommend lazy loading if file > 1GB or risk >= caution
            recommend_lazy = (file_size_gb > 1.0) or (risk_level in ['caution', 'risky', 'critical'])

            # Get memory info
            loader = LazyEventLoader(file_path)
            memory_info = loader.get_system_memory_info()
            estimated_memory_mb = loader.estimate_memory_usage() / (1024**2)

            return self.create_result(
                success=True,
                data={
                    'file_size_bytes': file_size,
                    'file_size_mb': file_size_mb,
                    'file_size_gb': file_size_gb,
                    'risk_level': risk_level,
                    'recommend_lazy': recommend_lazy,
                    'estimated_memory_mb': estimated_memory_mb,
                    'memory_info': memory_info
                },
                message=f"File size: {loader.format_file_size(file_size)}, Risk: {risk_level}"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Checking file size",
                file_path=file_path
            )

    def load_event_list_lazy(
        self,
        file_path: str,
        name: str,
        safety_margin: float = 0.5,
        rmf_file: Optional[str] = None,
        additional_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Load EventList using lazy loading for large files.

        This method intelligently decides whether to use lazy loading
        or standard loading based on file size and available memory.

        Args:
            file_path: Path to the event file
            name: Name to assign to the loaded event list
            safety_margin: Fraction of available RAM to use (0.0-1.0)
            rmf_file: Optional path to RMF file for energy calibration
            additional_columns: Optional list of additional columns to read

        Returns:
            Result dictionary with:
                - success: True if loaded successfully
                - data: The loaded EventList object
                - message: User-friendly status message
                - metadata: Loading method and memory info

        Example:
            >>> result = data_service.load_event_list_lazy(
            ...     file_path="/path/to/large.evt",
            ...     name="large_observation",
            ...     rmf_file="/path/to/response.rmf",
            ...     additional_columns=["PI", "ENERGY"]
            ... )
            >>> if result["success"]:
            ...     event_list = result["data"]
            ...     print(f"Loaded via: {result['metadata']['method']}")
        """
        with performance_monitor.track_operation("load_event_list_lazy", file_path=file_path):
            try:
                # Validate the name doesn't already exist
                if self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"An event list with the name '{name}' already exists. Please use a different name.",
                        error=None
                    )

                # Create lazy loader
                loader = LazyEventLoader(file_path)

                # Get metadata
                metadata = loader.get_metadata()
                can_load_safe = loader.can_load_safely(safety_margin=safety_margin)

                if can_load_safe:
                    # Safe to load fully
                    event_list = loader.load_full(
                        rmf_file=rmf_file,
                        additional_columns=additional_columns
                    )
                    method = 'standard'
                    message = (
                        f"EventList '{name}' loaded successfully via standard method "
                        f"({len(event_list.time)} events, "
                        f"{loader.format_file_size(loader.file_size)})"
                    )
                else:
                    # File too large - need to warn user or use streaming
                    # For now, we'll still load but warn
                    message = (
                        f"WARNING: File is large ({loader.format_file_size(loader.file_size)}). "
                        f"Loading may consume significant memory. "
                        f"Consider using streaming operations instead."
                    )
                    event_list = loader.load_full(
                        rmf_file=rmf_file,
                        additional_columns=additional_columns
                    )
                    method = 'standard_risky'

                # Add to state manager
                self.state.add_event_data(name, event_list)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message=message,
                    metadata={
                        'method': method,
                        'file_metadata': metadata,
                        'memory_safe': can_load_safe
                    }
                )

            except MemoryError as e:
                return self.create_result(
                    success=False,
                    data=None,
                    message=(
                        f"Out of memory loading file. "
                        f"File is too large to load into memory. "
                        f"Try using streaming operations or processing on a machine with more RAM."
                    ),
                    error=str(e)
                )
            except Exception as e:
                return self.handle_error(
                    e,
                    "Loading event list with lazy loader",
                    file_path=file_path,
                    name=name
                )

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata from a FITS file without loading the event data.

        This is a fast operation that only reads FITS headers.

        Args:
            file_path: Path to the FITS file

        Returns:
            Result dictionary with metadata

        Example:
            >>> result = data_service.get_file_metadata("/path/to/obs.evt")
            >>> if result["success"]:
            ...     metadata = result["data"]
            ...     print(f"Observation duration: {metadata['duration_s']}s")
        """
        try:
            loader = LazyEventLoader(file_path)
            metadata = loader.get_metadata()

            return self.create_result(
                success=True,
                data=metadata,
                message=f"Metadata extracted from {os.path.basename(file_path)}"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Extracting file metadata",
                file_path=file_path
            )

    def is_large_file(self, file_path: str, threshold_gb: float = 1.0) -> bool:
        """
        Check if a file is considered "large".

        Args:
            file_path: Path to the file
            threshold_gb: Size threshold in gigabytes (default: 1.0 GB)

        Returns:
            True if file size exceeds threshold
        """
        try:
            file_size = os.path.getsize(file_path)
            file_size_gb = file_size / (1024**3)
            return file_size_gb > threshold_gb
        except Exception:
            return False

    def load_event_list_preview(
        self,
        file_path: str,
        name: str,
        preview_duration: float = 100.0,
        rmf_file: Optional[str] = None,
        additional_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Load only the first segment of a large file as a preview.

        This is useful for extremely large files that cannot fit in memory.
        Instead of loading the entire file, this loads only the first
        `preview_duration` seconds of data.

        Args:
            file_path: Path to the event file
            name: Name to assign to the loaded event list
            preview_duration: Duration in seconds to preview (default: 100s)
            rmf_file: Optional path to RMF file for energy calibration
            additional_columns: Optional list of additional columns to read

        Returns:
            Result dictionary with:
                - success: True if loaded successfully
                - data: The preview EventList object
                - message: User-friendly status message
                - metadata: Preview info (duration, total file size, etc.)

        Example:
            >>> result = data_service.load_event_list_preview(
            ...     file_path="/path/to/huge.evt",
            ...     name="huge_preview",
            ...     preview_duration=50.0
            ... )
            >>> if result["success"]:
            ...     preview_events = result["data"]
            ...     print(f"Preview: {len(preview_events.time)} events from first 50s")
        """
        with performance_monitor.track_operation("load_event_list_preview", file_path=file_path):
            try:
                # Validate the name doesn't already exist
                if self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"An event list with the name '{name}' already exists. Please use a different name.",
                        error=None
                    )

                # Create lazy loader
                loader = LazyEventLoader(file_path)

                # Get metadata
                metadata = loader.get_metadata()

                # Get first segment of data
                import numpy as np
                segments_iter = loader.stream_segments(segment_size=preview_duration)
                first_segment_times = next(segments_iter)

                # Create EventList from the preview segment
                # Note: This is a simplified EventList with just times
                from stingray import EventList
                event_list = EventList(
                    time=first_segment_times,
                    gti=loader.reader.gti,
                    mjdref=metadata['mjdref']
                )

                # Add to state manager
                self.state.add_event_data(name, event_list)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message=(
                        f"Preview loaded: '{name}' - First {preview_duration}s "
                        f"({len(event_list.time)} events from "
                        f"{loader.format_file_size(loader.file_size)} file)"
                    ),
                    metadata={
                        'method': 'preview',
                        'preview_duration': preview_duration,
                        'total_duration': metadata['duration_s'],
                        'file_size_gb': metadata['file_size_gb'],
                        'estimated_total_events': metadata['n_events_estimate']
                    }
                )

            except StopIteration:
                return self.create_result(
                    success=False,
                    data=None,
                    message="File has no data in the specified preview duration",
                    error="No segments available"
                )
            except Exception as e:
                return self.handle_error(
                    e,
                    "Loading event list preview",
                    file_path=file_path,
                    name=name,
                    preview_duration=preview_duration
                )

    def export_event_list_to_astropy_table(
        self,
        event_list_name: str,
        output_path: str,
        fmt: str = 'ascii.ecsv'
    ) -> Dict[str, Any]:
        """
        Export an EventList to Astropy Table format.

        This provides interoperability with the Astropy ecosystem, allowing
        EventLists to be converted to Astropy tables and saved in various formats.

        Args:
            event_list_name: Name of the EventList in state
            output_path: Path where to save the table
            fmt: Output format (ascii.ecsv, fits, votable, hdf5, etc.)

        Returns:
            Result dictionary with success status and message

        Example:
            >>> result = data_service.export_event_list_to_astropy_table(
            ...     event_list_name="my_events",
            ...     output_path="events_table.ecsv",
            ...     fmt="ascii.ecsv"
            ... )
        """
        try:
            # Get EventList from state
            event_data = self.state.get_event_data()
            event_list = None
            for name, ev in event_data:
                if name == event_list_name:
                    event_list = ev
                    break

            if event_list is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found in loaded data",
                    error="EventList not in state"
                )

            # Convert to Astropy Table
            table = event_list.to_astropy_table()

            # Write to file
            table.write(output_path, format=fmt, overwrite=True)

            return self.create_result(
                success=True,
                data=table,
                message=f"EventList '{event_list_name}' exported to {output_path} ({fmt} format)",
                metadata={
                    'format': fmt,
                    'output_path': output_path,
                    'n_rows': len(table)
                }
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Exporting EventList to Astropy table",
                event_list_name=event_list_name,
                output_path=output_path,
                fmt=fmt
            )

    def import_event_list_from_astropy_table(
        self,
        file_path: str,
        name: str,
        fmt: str = 'ascii.ecsv'
    ) -> Dict[str, Any]:
        """
        Import an EventList from Astropy Table format.

        This allows loading EventLists that were exported as Astropy tables
        or created using Astropy tools.

        Args:
            file_path: Path to the Astropy table file
            name: Name to assign to the loaded EventList
            fmt: Input format (ascii.ecsv, fits, votable, hdf5, etc.)

        Returns:
            Result dictionary with EventList data

        Example:
            >>> result = data_service.import_event_list_from_astropy_table(
            ...     file_path="events_table.ecsv",
            ...     name="imported_events",
            ...     fmt="ascii.ecsv"
            ... )
        """
        try:
            # Check for duplicate names
            if self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"An event list with the name '{name}' already exists",
                    error="Duplicate name"
                )

            # Import table
            from astropy.table import Table
            from stingray import EventList

            table = Table.read(file_path, format=fmt)

            # Convert to EventList
            event_list = EventList.from_astropy_table(table)

            # Add to state
            self.state.add_event_data(name, event_list)

            return self.create_result(
                success=True,
                data=event_list,
                message=f"EventList '{name}' imported from {file_path} ({fmt} format)",
                metadata={
                    'format': fmt,
                    'file_path': file_path,
                    'n_events': len(event_list.time)
                }
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Importing EventList from Astropy table",
                file_path=file_path,
                name=name,
                fmt=fmt
            )
