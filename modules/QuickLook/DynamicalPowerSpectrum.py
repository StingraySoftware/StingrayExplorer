import panel as pn
import holoviews as hv
from stingray import DynamicalPowerspectrum
import warnings
import matplotlib.pyplot as plt
import numpy as np
from utils.DashboardClasses import (
    MainHeader,
    MainArea,
    OutputBox,
    WarningBox,
    HelpBox,
    Footer,
    WarningHandler,
    FloatingPlot,
    PlotsContainer,
)
from utils.globals import loaded_event_data
import hvplot.pandas
import holoviews.operation.datashader as hd


# Create a warning handler
def create_warning_handler():
    warning_handler = WarningHandler()
    warnings.showwarning = warning_handler.warn
    return warning_handler


""" Header Section """


def create_quicklook_dynamicalpowerspectrum_header(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
    float_panel_container,
):
    header_input = pn.widgets.TextInput(
        name="Heading", value="QuickLook Dynamical Power Spectrum"
    )
    return MainHeader(heading=header_input)


""" Output Box Section """


def create_loadingdata_output_box(content):
    return OutputBox(output_content=content)


""" Warning Box Section """


def create_loadingdata_warning_box(content):
    return WarningBox(warning_content=content)


""" Main Area Section """


def create_dynamicalpowerspectrum_tab(
    output_box_container,
    warning_box_container,
    warning_handler,
    plots_container,
    header_container,
    float_panel_container,
):
    event_list_dropdown = pn.widgets.Select(
        name="Select Event List(s)",
        options={name: i for i, (name, event) in enumerate(loaded_event_data)},
    )

    segment_size_input = pn.widgets.FloatInput(name="Segment Size", value=10, step=1)
    dt_input = pn.widgets.FloatInput(
        name="Select dt", value=1.0, step=0.0001, start=0.0000000001, end=1000.0
    )
    norm_select = pn.widgets.Select(
        name="Normalization", options=["leahy", "rms", "frac", "abs"], value="leahy"
    )
    rebin_freq_checkbox = pn.widgets.Checkbox(name="Rebin Frequency", value=False)
    rebin_time_checkbox = pn.widgets.Checkbox(name="Rebin Time", value=False)
    trace_checkbox = pn.widgets.Checkbox(name="Trace Drifting Feature", value=False)
    shift_add_checkbox = pn.widgets.Checkbox(name="Apply Shift-and-Add", value=False)
    # Inputs for new rebinning parameters
    rebin_freq_input = pn.widgets.FloatInput(
        name="New Frequency Resolution (Hz)", value=1.0, step=0.1, start=0.1
    )
    rebin_time_input = pn.widgets.FloatInput(
        name="New Time Resolution (s)", value=6.0, step=1, start=1.0
    )

    floatpanel_plots_checkbox = pn.widgets.Checkbox(
        name="Add Plot to FloatingPanel", value=True
    )
    dataframe_checkbox = pn.widgets.Checkbox(
        name="Add DataFrame to FloatingPanel", value=False
    )

    def create_dataframe(selected_event_list_index, dt, segment_size, norm):
        if selected_event_list_index is not None:
            event_list = loaded_event_data[selected_event_list_index][1]
            lc = event_list.to_lc(dt=dt)
            dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm=norm)
            return dps
        return None

    def create_holoviews_panes(plot):
        return pn.pane.HoloViews(plot, width=600, height=600, linked_axes=False)

    def create_dataframe(dps):
        data = {
            "Time": dps.time,
            "Frequency": dps.freq,
            "Power": dps.dyn_ps.flatten(),
        }

        return pn.pane.DataFrame(data, width=600, height=400)

    def generate_dynamicalpowerspectrum(event=None):
        if not loaded_event_data:
            output_box_container[:] = [
                create_loadingdata_output_box("No loaded event data available.")
            ]
            return

        selected_event_list_index = event_list_dropdown.value
        if selected_event_list_index is None:
            output_box_container[:] = [
                create_loadingdata_output_box("No event list selected.")
            ]
            return

        # Check for conflicting rebin selections
        if rebin_freq_checkbox.value and rebin_time_checkbox.value:
            warning_box_container[:] = [
                create_loadingdata_warning_box(
                    "Error: You cannot select both 'Rebin Frequency' and 'Rebin Time' simultaneously."
                )
            ]
            return
        
        dt = dt_input.value
        segment_size = segment_size_input.value
        norm = norm_select.value

        # Directly create DynamicalPowerspectrum
        event_list = loaded_event_data[selected_event_list_index][1]
        lc = event_list.to_lc(dt=dt)
        dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm=norm)
        if dps:
            # Create Matplotlib plots
            fig, ax = plt.subplots()
            extent = min(dps.time), max(dps.time), min(dps.freq), max(dps.freq)
            im = ax.imshow(
                dps.dyn_ps,
                aspect="auto",
                origin="lower",
                interpolation="none",
                extent=extent,
            )
            ax.set_title("Dynamic Powerspectrum")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Frequency (Hz)")
            plt.colorbar(im, ax=ax, label="Power")
            base_plot = pn.pane.Matplotlib(fig, width=600, height=400)
            # Add the base plot to the floating panel or plot area
            if floatpanel_plots_checkbox.value:
                float_panel_container.append(FloatingPlot(title="Base Dynamical Power Spectrum", content=base_plot))
            else:
                plots_container.append(base_plot)

            # Rebin Frequency if checkbox is enabled
            if rebin_freq_checkbox.value:
                new_freq_res = rebin_freq_input.value
                dps_rebin_freq = dps.rebin_frequency(df_new=new_freq_res, method="average")
                fig, ax = plt.subplots()
                extent = min(dps_rebin_freq.time), max(dps_rebin_freq.time), min(dps_rebin_freq.freq), max(dps_rebin_freq.freq)
                # extent = [dps_rebin_freq.time[0], dps_rebin_freq.time[-1], dps_rebin_freq.freq[0], dps_rebin_freq.freq[-1]]
                im = ax.imshow(dps_rebin_freq.dyn_ps, origin="lower", aspect="auto", interpolation="none", extent=extent)
                ax.set_title("Rebinned Frequency")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Frequency (Hz)")
                plt.colorbar(im, ax=ax, label="Power")
                rebin_freq_plot = pn.pane.Matplotlib(fig, width=600, height=400)

                if floatpanel_plots_checkbox.value:
                    float_panel_container.append(FloatingPlot(title="Rebinned Frequency", content=rebin_freq_plot))
                else:
                    plots_container.append(rebin_freq_plot)

            # Rebin Time if checkbox is enabled
            if rebin_time_checkbox.value:
                new_time_res = rebin_time_input.value
                dps_rebin_time = dps.rebin_time(dt_new=new_time_res, method="average")
                fig, ax = plt.subplots()
                extent = [dps_rebin_time.time[0], dps_rebin_time.time[-1], dps_rebin_time.freq[0], dps_rebin_time.freq[-1]]
                im = ax.imshow(dps_rebin_time.dyn_ps, origin="lower", aspect="auto", interpolation="none", extent=extent)
                ax.set_title("Rebinned Time")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Frequency (Hz)")
                plt.colorbar(im, ax=ax, label="Power")
                rebin_time_plot = pn.pane.Matplotlib(fig, width=600, height=400)

                if floatpanel_plots_checkbox.value:
                    float_panel_container.append(FloatingPlot(title="Rebinned Time", content=rebin_time_plot))
                else:
                    plots_container.append(rebin_time_plot)

            # Trace Maximum Power if checkbox is enabled
            if trace_checkbox.value:
                max_pos = dps.trace_maximum()
                fig, ax = plt.subplots()
                im = ax.imshow(dps.dyn_ps, aspect="auto", origin="lower", interpolation="none", extent=extent, alpha=0.6)
                ax.plot(dps.time, dps.freq[max_pos], color="red", lw=2, label="Drifting Feature")
                ax.set_title("Dynamic Powerspectrum with Feature Trace")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Frequency (Hz)")
                plt.colorbar(im, ax=ax, label="Power")
                ax.legend()
                trace_plot = pn.pane.Matplotlib(fig, width=600, height=400)

                if floatpanel_plots_checkbox.value:
                    float_panel_container.append(FloatingPlot(title="Feature Trace Overlay", content=trace_plot))
                else:
                    plots_container.append(trace_plot)


    generate_dynamicalpowerspectrum_button = pn.widgets.Button(
        name="Generate Dynamical Power Spectrum", button_type="primary"
    )
    generate_dynamicalpowerspectrum_button.on_click(generate_dynamicalpowerspectrum)

    tab_content = pn.Column(
        event_list_dropdown,
        dt_input,
        segment_size_input,
        norm_select,
        rebin_freq_checkbox,
        rebin_freq_input,
        rebin_time_checkbox,
        rebin_time_input,
        trace_checkbox,
        floatpanel_plots_checkbox,
        dataframe_checkbox,
        pn.Row(generate_dynamicalpowerspectrum_button),
    )
    return tab_content


def create_quicklook_dynamicalpowerspectrum_main_area(
    header_container,
    main_area_container,
    output_box_container,
    warning_box_container,
    plots_container,
    help_box_container,
    footer_container,
    float_panel_container,
):
    warning_handler = create_warning_handler()
    tabs_content = {
        "Dynamical Power Spectrum": create_dynamicalpowerspectrum_tab(
            output_box_container=output_box_container,
            warning_box_container=warning_box_container,
            warning_handler=warning_handler,
            plots_container=plots_container,
            header_container=header_container,
            float_panel_container=float_panel_container,
        ),
    }

    return MainArea(tabs_content=tabs_content)


def create_quicklook_dynamicalpowerspectrum_area():
    return PlotsContainer()
