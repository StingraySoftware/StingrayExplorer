"""
Spectrum service for spectral analysis operations.

This service handles all spectrum-related business logic including:
- Power spectrum creation (single and averaged)
- Cross spectrum creation (single and averaged)
- Dynamical power spectrum creation
- Spectrum rebinning (linear and logarithmic)
"""

from typing import Dict, Any
from stingray import EventList, Lightcurve, Powerspectrum, Crossspectrum
from stingray import AveragedPowerspectrum, AveragedCrossspectrum, DynamicalPowerspectrum
from .base_service import BaseService
from utils.performance_monitor import performance_monitor


class SpectrumService(BaseService):
    """
    Service for spectral analysis operations.

    Handles power spectrum, cross spectrum, and dynamical power spectrum
    creation without any UI dependencies. All operations return standardized
    result dictionaries.
    """

    def create_power_spectrum(
        self,
        event_list: EventList,
        dt: float,
        norm: str = "leahy"
    ) -> Dict[str, Any]:
        """
        Create a power spectrum from an EventList.

        Args:
            event_list: The EventList to analyze
            dt: Time binning in seconds
            norm: Normalization type ("leahy", "frac", "abs", "none")

        Returns:
            Result dictionary with the Powerspectrum as data

        Example:
            >>> result = spectrum_service.create_power_spectrum(
            ...     event_list=event_list,
            ...     dt=0.1,
            ...     norm="leahy"
            ... )
        """
        with performance_monitor.track_operation("create_power_spectrum", dt=dt, norm=norm):
            try:
                lc = event_list.to_lc(dt=dt)
                ps = Powerspectrum(lc, norm=norm)

                return self.create_result(
                    success=True,
                    data=ps,
                    message=f"Power spectrum created successfully (dt={dt}s, norm={norm})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating power spectrum",
                    dt=dt,
                    norm=norm
                )

    def create_averaged_power_spectrum(
        self,
        event_list: EventList,
        dt: float,
        segment_size: float,
        norm: str = "leahy"
    ) -> Dict[str, Any]:
        """
        Create an averaged power spectrum from an EventList.

        Args:
            event_list: The EventList to analyze
            dt: Time binning in seconds
            segment_size: Segment size in seconds for averaging
            norm: Normalization type ("leahy", "frac", "abs", "none")

        Returns:
            Result dictionary with the AveragedPowerspectrum as data

        Example:
            >>> result = spectrum_service.create_averaged_power_spectrum(
            ...     event_list=event_list,
            ...     dt=0.1,
            ...     segment_size=100,
            ...     norm="leahy"
            ... )
        """
        with performance_monitor.track_operation("create_averaged_power_spectrum", dt=dt, segment_size=segment_size, norm=norm):
            try:
                lc = event_list.to_lc(dt=dt)
                ps = AveragedPowerspectrum.from_lightcurve(lc, segment_size, norm=norm)

                return self.create_result(
                    success=True,
                    data=ps,
                    message=f"Averaged power spectrum created successfully (segment={segment_size}s, norm={norm})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating averaged power spectrum",
                    dt=dt,
                    segment_size=segment_size,
                    norm=norm
                )

    def create_cross_spectrum(
        self,
        event_list_1: EventList,
        event_list_2: EventList,
        dt: float,
        norm: str = "leahy"
    ) -> Dict[str, Any]:
        """
        Create a cross spectrum from two EventLists.

        Args:
            event_list_1: First EventList
            event_list_2: Second EventList
            dt: Time binning in seconds
            norm: Normalization type ("leahy", "frac", "abs", "none")

        Returns:
            Result dictionary with the Crossspectrum as data

        Example:
            >>> result = spectrum_service.create_cross_spectrum(
            ...     event_list_1=event_list_1,
            ...     event_list_2=event_list_2,
            ...     dt=0.1,
            ...     norm="leahy"
            ... )
        """
        with performance_monitor.track_operation("create_cross_spectrum", dt=dt, norm=norm):
            try:
                # Validate GTIs
                if event_list_1.gti.shape[0] == 0 or event_list_2.gti.shape[0] == 0:
                    return self.create_result(
                        success=False,
                        data=None,
                        message="GTIs are empty for one or both event lists",
                        error="Empty GTI arrays"
                    )

                cs = Crossspectrum.from_events(
                    events1=event_list_1,
                    events2=event_list_2,
                    dt=dt,
                    norm=norm
                )

                return self.create_result(
                    success=True,
                    data=cs,
                    message=f"Cross spectrum created successfully (dt={dt}s, norm={norm})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating cross spectrum",
                    dt=dt,
                    norm=norm
                )

    def create_averaged_cross_spectrum(
        self,
        event_list_1: EventList,
        event_list_2: EventList,
        dt: float,
        segment_size: float,
        norm: str = "leahy"
    ) -> Dict[str, Any]:
        """
        Create an averaged cross spectrum from two EventLists.

        Args:
            event_list_1: First EventList
            event_list_2: Second EventList
            dt: Time binning in seconds
            segment_size: Segment size in seconds for averaging
            norm: Normalization type ("leahy", "frac", "abs", "none")

        Returns:
            Result dictionary with the AveragedCrossspectrum as data

        Example:
            >>> result = spectrum_service.create_averaged_cross_spectrum(
            ...     event_list_1=event_list_1,
            ...     event_list_2=event_list_2,
            ...     dt=0.1,
            ...     segment_size=100,
            ...     norm="leahy"
            ... )
        """
        with performance_monitor.track_operation("create_averaged_cross_spectrum", dt=dt, segment_size=segment_size, norm=norm):
            try:
                # Validate GTIs
                if event_list_1.gti.shape[0] == 0 or event_list_2.gti.shape[0] == 0:
                    return self.create_result(
                        success=False,
                        data=None,
                        message="GTIs are empty for one or both event lists",
                        error="Empty GTI arrays"
                    )

                lc1 = event_list_1.to_lc(dt=dt)
                lc2 = event_list_2.to_lc(dt=dt)

                cs = AveragedCrossspectrum.from_lightcurve(
                    lc1=lc1,
                    lc2=lc2,
                    segment_size=segment_size,
                    norm=norm
                )

                return self.create_result(
                    success=True,
                    data=cs,
                    message=f"Averaged cross spectrum created successfully (segment={segment_size}s, norm={norm})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating averaged cross spectrum",
                    dt=dt,
                    segment_size=segment_size,
                    norm=norm
                )

    def create_dynamical_power_spectrum(
        self,
        event_list: EventList,
        dt: float,
        segment_size: float,
        norm: str = "leahy"
    ) -> Dict[str, Any]:
        """
        Create a dynamical power spectrum from an EventList.

        Args:
            event_list: The EventList to analyze
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            norm: Normalization type ("leahy", "frac", "abs", "none")

        Returns:
            Result dictionary with the DynamicalPowerspectrum as data

        Example:
            >>> result = spectrum_service.create_dynamical_power_spectrum(
            ...     event_list=event_list,
            ...     dt=0.1,
            ...     segment_size=100,
            ...     norm="leahy"
            ... )
        """
        with performance_monitor.track_operation("create_dynamical_power_spectrum", dt=dt, segment_size=segment_size, norm=norm):
            try:
                lc = event_list.to_lc(dt=dt)
                dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm=norm)

                return self.create_result(
                    success=True,
                    data=dps,
                    message=f"Dynamical power spectrum created successfully (segment={segment_size}s, norm={norm})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating dynamical power spectrum",
                    dt=dt,
                    segment_size=segment_size,
                    norm=norm
                )

    def rebin_spectrum_linear(
        self,
        spectrum: Any,
        rebin_factor: float
    ) -> Dict[str, Any]:
        """
        Rebin a spectrum linearly.

        Args:
            spectrum: The spectrum object to rebin (Powerspectrum, Crossspectrum, etc.)
            rebin_factor: Rebinning factor

        Returns:
            Result dictionary with the rebinned spectrum as data

        Example:
            >>> result = spectrum_service.rebin_spectrum_linear(
            ...     spectrum=ps,
            ...     rebin_factor=2.0
            ... )
        """
        try:
            rebinned_spectrum = spectrum.rebin(rebin_factor)

            return self.create_result(
                success=True,
                data=rebinned_spectrum,
                message=f"Spectrum rebinned linearly (factor={rebin_factor})"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Rebinning spectrum linearly",
                rebin_factor=rebin_factor
            )

    def rebin_spectrum_log(
        self,
        spectrum: Any,
        log_factor: float
    ) -> Dict[str, Any]:
        """
        Rebin a spectrum logarithmically.

        Args:
            spectrum: The spectrum object to rebin
            log_factor: Logarithmic rebinning factor

        Returns:
            Result dictionary with the rebinned spectrum as data

        Example:
            >>> result = spectrum_service.rebin_spectrum_log(
            ...     spectrum=ps,
            ...     log_factor=0.1
            ... )
        """
        try:
            rebinned_spectrum = spectrum.rebin_log(log_factor)

            return self.create_result(
                success=True,
                data=rebinned_spectrum,
                message=f"Spectrum rebinned logarithmically (factor={log_factor})"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Rebinning spectrum logarithmically",
                log_factor=log_factor
            )
