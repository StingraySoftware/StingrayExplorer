"""
Export service for data export operations.

Handles exporting data to various formats.
"""

import os
from typing import Any, Dict

import numpy as np
import pandas as pd

from .base_service import BaseService


class ExportService(BaseService):
    """
    Service for data export operations.

    Handles conversion and export of astronomical data.
    """

    def export_event_list_to_csv(
        self,
        name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Export an EventList to CSV file.

        Args:
            name: Name of the event list in state
            file_path: Path where to save the CSV file

        Returns:
            Result dictionary
        """
        try:
            if not self.state.has_event_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{name}' not found",
                    error=None,
                )

            event_list = self.state.get_event_data(name)

            # Create DataFrame
            data = {"time": event_list.time}
            if event_list.energy is not None:
                data["energy"] = event_list.energy
            if event_list.pi is not None:
                data["pi"] = event_list.pi

            df = pd.DataFrame(data)

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save to CSV
            df.to_csv(file_path, index=False)

            return self.create_result(
                success=True,
                data={"file_path": file_path, "n_rows": len(df)},
                message=f"EventList exported to '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e, "Exporting event list to CSV", name=name, file_path=file_path
            )

    def export_lightcurve_to_csv(
        self,
        name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Export a Lightcurve to CSV file.

        Args:
            name: Name of the lightcurve in state
            file_path: Path where to save the CSV file

        Returns:
            Result dictionary
        """
        try:
            if not self.state.has_lightcurve_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Lightcurve '{name}' not found",
                    error=None,
                )

            lightcurve = self.state.get_lightcurve_data(name)

            df = pd.DataFrame({
                "time": lightcurve.time,
                "counts": lightcurve.counts,
            })

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_csv(file_path, index=False)

            return self.create_result(
                success=True,
                data={"file_path": file_path, "n_rows": len(df)},
                message=f"Lightcurve exported to '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e, "Exporting lightcurve to CSV", name=name, file_path=file_path
            )

    def export_power_spectrum_to_csv(
        self,
        name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Export a power spectrum to CSV file.

        Args:
            name: Name of the spectrum in state
            file_path: Path where to save the CSV file

        Returns:
            Result dictionary
        """
        try:
            if not self.state.has_spectrum_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Spectrum '{name}' not found",
                    error=None,
                )

            spectrum = self.state.get_spectrum_data(name)

            df = pd.DataFrame({
                "frequency": spectrum.freq,
                "power": spectrum.power,
            })

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_csv(file_path, index=False)

            return self.create_result(
                success=True,
                data={"file_path": file_path, "n_rows": len(df)},
                message=f"Spectrum exported to '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e, "Exporting spectrum to CSV", name=name, file_path=file_path
            )

    def export_bispectrum_to_csv(
        self,
        name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Export a bispectrum to CSV file.

        Args:
            name: Name of the bispectrum in state
            file_path: Path where to save the CSV file

        Returns:
            Result dictionary
        """
        try:
            bispectrum = self.state.get_analysis_result(name)

            if bispectrum is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Bispectrum '{name}' not found",
                    error=None,
                )

            # Create flattened DataFrame for 2D bispectrum data
            freq_grid, lags_grid = np.meshgrid(
                bispectrum.freq, bispectrum.lags
            )

            df = pd.DataFrame({
                "frequency": freq_grid.flatten(),
                "lags": lags_grid.flatten(),
                "cum3": bispectrum.cum3.flatten(),
                "magnitude": bispectrum.bispec_mag.flatten(),
                "phase": bispectrum.bispec_phase.flatten(),
            })

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_csv(file_path, index=False)

            return self.create_result(
                success=True,
                data={"file_path": file_path, "n_rows": len(df)},
                message=f"Bispectrum exported to '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e, "Exporting bispectrum to CSV", name=name, file_path=file_path
            )

    def export_to_hdf5(
        self,
        name: str,
        file_path: str,
        data_type: str = "event_list",
    ) -> Dict[str, Any]:
        """
        Export data to HDF5 file.

        Args:
            name: Name of the data in state
            file_path: Path where to save the HDF5 file
            data_type: Type of data ("event_list", "lightcurve", "spectrum")

        Returns:
            Result dictionary
        """
        try:
            if data_type == "event_list":
                if not self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"EventList '{name}' not found",
                        error=None,
                    )
                data = self.state.get_event_data(name)
                table = data.to_astropy_table()

            elif data_type == "lightcurve":
                if not self.state.has_lightcurve_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"Lightcurve '{name}' not found",
                        error=None,
                    )
                data = self.state.get_lightcurve_data(name)
                # Convert lightcurve to table
                from astropy.table import Table
                table = Table({
                    "time": data.time,
                    "counts": data.counts,
                })

            elif data_type == "spectrum":
                if not self.state.has_spectrum_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"Spectrum '{name}' not found",
                        error=None,
                    )
                data = self.state.get_spectrum_data(name)
                from astropy.table import Table
                table = Table({
                    "frequency": data.freq,
                    "power": data.power,
                })

            else:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Unknown data type: {data_type}",
                    error=None,
                )

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            table.write(file_path, format="hdf5", path="data", overwrite=True)

            return self.create_result(
                success=True,
                data={"file_path": file_path},
                message=f"Data exported to HDF5: '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Exporting to HDF5",
                name=name,
                file_path=file_path,
                data_type=data_type,
            )

    def export_to_fits(
        self,
        name: str,
        file_path: str,
        data_type: str = "event_list",
    ) -> Dict[str, Any]:
        """
        Export data to FITS file.

        Args:
            name: Name of the data in state
            file_path: Path where to save the FITS file
            data_type: Type of data

        Returns:
            Result dictionary
        """
        try:
            if data_type == "event_list":
                if not self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"EventList '{name}' not found",
                        error=None,
                    )
                data = self.state.get_event_data(name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                data.write(file_path, fmt="ogip")

            else:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"FITS export not supported for {data_type}",
                    error=None,
                )

            return self.create_result(
                success=True,
                data={"file_path": file_path},
                message=f"Data exported to FITS: '{file_path}'",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Exporting to FITS",
                name=name,
                file_path=file_path,
                data_type=data_type,
            )
