"""
Export service for data export operations.

This service handles data export and conversion including:
- Converting Stingray objects to DataFrames
- Exporting EventLists to various formats
- Saving DataFrames to CSV/HDF5
"""

from typing import Dict, Any, Optional
import os
import pandas as pd
import numpy as np
from stingray import EventList
from .base_service import BaseService
from utils.performance_monitor import performance_monitor


class ExportService(BaseService):
    """
    Service for data export operations.

    Handles conversion and export of astronomical data without any UI dependencies.
    All operations return standardized result dictionaries.
    """

    def export_event_list(
        self,
        name: str,
        file_path: str,
        fmt: str = "ogip"
    ) -> Dict[str, Any]:
        """
        Export an EventList to disk.

        This is a convenience wrapper around DataService.save_event_list.

        Args:
            name: Name of the event list in state
            file_path: Path where to save the file
            fmt: File format to save as (ogip, hdf5, etc.)

        Returns:
            Result dictionary

        Example:
            >>> result = export_service.export_event_list(
            ...     name="observation_1",
            ...     file_path="/path/to/save/obs.hdf5",
            ...     fmt="hdf5"
            ... )
        """
        with performance_monitor.track_operation("export_event_list", name=name, file_path=file_path, fmt=fmt):
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
                    message=f"EventList '{name}' exported to '{file_path}' (format: {fmt})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Exporting event list",
                    name=name,
                    file_path=file_path,
                    fmt=fmt
                )

    def to_dataframe_power_spectrum(
        self,
        power_spectrum: Any
    ) -> Dict[str, Any]:
        """
        Convert a power spectrum to a pandas DataFrame.

        Args:
            power_spectrum: Powerspectrum or AveragedPowerspectrum object

        Returns:
            Result dictionary with DataFrame as data

        Example:
            >>> result = export_service.to_dataframe_power_spectrum(ps)
            >>> if result["success"]:
            ...     df = result["data"]
        """
        try:
            df = pd.DataFrame({
                "Frequency": power_spectrum.freq,
                "Power": power_spectrum.power
            })

            return self.create_result(
                success=True,
                data=df,
                message=f"Power spectrum converted to DataFrame ({len(df)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Converting power spectrum to DataFrame"
            )

    def to_dataframe_cross_spectrum(
        self,
        cross_spectrum: Any
    ) -> Dict[str, Any]:
        """
        Convert a cross spectrum to a pandas DataFrame.

        Args:
            cross_spectrum: Crossspectrum or AveragedCrossspectrum object

        Returns:
            Result dictionary with DataFrame as data

        Example:
            >>> result = export_service.to_dataframe_cross_spectrum(cs)
        """
        try:
            df = pd.DataFrame({
                "Frequency": cross_spectrum.freq,
                "Power": cross_spectrum.power
            })

            return self.create_result(
                success=True,
                data=df,
                message=f"Cross spectrum converted to DataFrame ({len(df)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Converting cross spectrum to DataFrame"
            )

    def to_dataframe_bispectrum(
        self,
        bispectrum: Any
    ) -> Dict[str, Any]:
        """
        Convert a bispectrum to a pandas DataFrame.

        Args:
            bispectrum: Bispectrum object

        Returns:
            Result dictionary with DataFrame as data

        Example:
            >>> result = export_service.to_dataframe_bispectrum(bs)
        """
        try:
            # Create 2D grids for Frequency and Lags
            freq_grid, lags_grid = np.meshgrid(bispectrum.freq, bispectrum.lags)

            # Flatten grids and corresponding Bispectrum data
            freq_flat = freq_grid.flatten()
            lags_flat = lags_grid.flatten()
            mag_flat = bispectrum.bispec_mag.flatten()
            phase_flat = bispectrum.bispec_phase.flatten()
            cum3_flat = bispectrum.cum3.flatten()

            # Create DataFrame
            df = pd.DataFrame({
                "Frequency": freq_flat,
                "Lags": lags_flat,
                "Cumulant (Cum3)": cum3_flat,
                "Magnitude": mag_flat,
                "Phase": phase_flat,
            })

            return self.create_result(
                success=True,
                data=df,
                message=f"Bispectrum converted to DataFrame ({len(df)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Converting bispectrum to DataFrame"
            )

    def to_dataframe_lightcurve(
        self,
        lightcurve: Any
    ) -> Dict[str, Any]:
        """
        Convert a lightcurve to a pandas DataFrame.

        Args:
            lightcurve: Lightcurve object

        Returns:
            Result dictionary with DataFrame as data

        Example:
            >>> result = export_service.to_dataframe_lightcurve(lc)
        """
        try:
            df = pd.DataFrame({
                "Time": lightcurve.time,
                "Counts": lightcurve.counts
            })

            return self.create_result(
                success=True,
                data=df,
                message=f"Lightcurve converted to DataFrame ({len(df)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Converting lightcurve to DataFrame"
            )

    def save_dataframe_to_csv(
        self,
        dataframe: pd.DataFrame,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Save a DataFrame to CSV file.

        Args:
            dataframe: The DataFrame to save
            file_path: Path where to save the CSV file

        Returns:
            Result dictionary

        Example:
            >>> result = export_service.save_dataframe_to_csv(
            ...     dataframe=df,
            ...     file_path="/path/to/save/data.csv"
            ... )
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            dataframe.to_csv(file_path, index=False)

            return self.create_result(
                success=True,
                data=file_path,
                message=f"DataFrame saved to CSV: '{file_path}' ({len(dataframe)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Saving DataFrame to CSV",
                file_path=file_path
            )

    def save_dataframe_to_hdf5(
        self,
        dataframe: pd.DataFrame,
        file_path: str,
        key: str = "data"
    ) -> Dict[str, Any]:
        """
        Save a DataFrame to HDF5 file.

        Args:
            dataframe: The DataFrame to save
            file_path: Path where to save the HDF5 file
            key: HDF5 dataset key

        Returns:
            Result dictionary

        Example:
            >>> result = export_service.save_dataframe_to_hdf5(
            ...     dataframe=df,
            ...     file_path="/path/to/save/data.h5"
            ... )
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            dataframe.to_hdf(file_path, key=key, mode='w')

            return self.create_result(
                success=True,
                data=file_path,
                message=f"DataFrame saved to HDF5: '{file_path}' ({len(dataframe)} rows)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Saving DataFrame to HDF5",
                file_path=file_path,
                key=key
            )
