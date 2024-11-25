import pytest
from unittest.mock import MagicMock, patch
from modules.DataLoading.DataIngestion import (
    create_loadingdata_output_box,
    load_event_data,
    save_loaded_files,
    delete_selected_files,
    preview_loaded_files,
    clear_loaded_files,
    create_event_list,
    simulate_event_list,
    create_warning_handler,
)


def test_create_loadingdata_output_box():
    content = "File loaded successfully."
    output_box = create_loadingdata_output_box(content)
    assert output_box.output_content == content


@patch("dataingestion.loaded_event_data", [])
def test_load_event_data_no_file_selected(
    output_box_container, warning_box_container, warning_handler, mock_file_selector, filename_input, format_input, format_checkbox
):
    # Set up file selector with no selection
    mock_file_selector.value = []
    load_event_data(
        event=None,
        file_selector=mock_file_selector,
        filename_input=filename_input,
        format_input=format_input,
        format_checkbox=format_checkbox,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "No file selected" in output_box_container[0].output_content


@patch("dataingestion.loaded_event_data", [])
@patch("dataingestion.EventList.read")
def test_load_event_data_success(mock_read, output_box_container, warning_box_container, warning_handler, mock_file_selector, filename_input, format_input, format_checkbox):
    # Mock EventList read to return a valid event
    mock_read.return_value = MagicMock()
    
    load_event_data(
        event=None,
        file_selector=mock_file_selector,
        filename_input=filename_input,
        format_input=format_input,
        format_checkbox=format_checkbox,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert len(output_box_container) > 0
    assert "loaded successfully" in output_box_container[0].output_content


@patch("dataingestion.loaded_event_data", [("file1", MagicMock())])
def test_load_event_data_duplicate_file(
    output_box_container, warning_box_container, warning_handler, mock_file_selector, filename_input, format_input, format_checkbox
):
    # Test with duplicate file name
    filename_input.value = "file1"
    load_event_data(
        event=None,
        file_selector=mock_file_selector,
        filename_input=filename_input,
        format_input=format_input,
        format_checkbox=format_checkbox,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "already exists in memory" in output_box_container[0].output_content


@patch("dataingestion.os.path.exists", return_value=False)
@patch("dataingestion.loaded_event_data", [("file1", MagicMock())])
def test_save_loaded_files_success(mock_exists, output_box_container, warning_box_container, warning_handler, filename_input, format_input, format_checkbox):
    save_loaded_files(
        event=None,
        filename_input=filename_input,
        format_input=format_input,
        format_checkbox=format_checkbox,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "saved successfully" in output_box_container[0].output_content


@patch("dataingestion.os.path.exists", return_value=True)
@patch("dataingestion.loaded_event_data", [("file1", MagicMock())])
def test_save_loaded_files_duplicate_name(mock_exists, output_box_container, warning_box_container, warning_handler, filename_input, format_input, format_checkbox):
    save_loaded_files(
        event=None,
        filename_input=filename_input,
        format_input=format_input,
        format_checkbox=format_checkbox,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "already exists" in output_box_container[0].output_content


@patch("dataingestion.os.remove")
def test_delete_selected_files_success(mock_remove, output_box_container, warning_box_container, warning_handler, mock_file_selector):
    delete_selected_files(
        event=None,
        file_selector=mock_file_selector,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "deleted successfully" in output_box_container[0].output_content


def test_preview_loaded_files_no_data(output_box_container, warning_box_container, warning_handler):
    preview_loaded_files(
        event=None,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "No valid files or light curves loaded" in output_box_container[0].output_content


@patch("dataingestion.loaded_event_data", [("event1", MagicMock(time=[0.1, 0.2], mjdref=58000, gti=[[0, 1]]) )])
def test_preview_loaded_files_with_data(output_box_container, warning_box_container, warning_handler):
    preview_loaded_files(
        event=None,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "Event List - event1" in output_box_container[0].output_content


@patch("dataingestion.loaded_event_data", [("event1", MagicMock())])
def test_clear_loaded_files(output_box_container, warning_box_container):
    clear_loaded_files(
        event=None,
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
    )
    assert "cleared" in output_box_container[0].output_content


def test_create_event_list_missing_data(output_box_container, warning_box_container, warning_handler):
    create_event_list(
        event=None,
        times_input=MagicMock(value=""),
        energy_input=MagicMock(value=""),
        pi_input=MagicMock(value=""),
        gti_input=MagicMock(value=""),
        mjdref_input=MagicMock(value=""),
        name_input=MagicMock(value=""),
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "Please enter Photon Arrival Times and MJDREF" in output_box_container[0].output_content


def test_simulate_event_list(output_box_container, warning_box_container, warning_handler):
    simulate_event_list(
        event=None,
        time_slider=MagicMock(value=10),
        count_slider=MagicMock(value=5),
        dt_input=MagicMock(value=0.1),
        name_input=MagicMock(value="simulated_event"),
        method_selector=MagicMock(value="Standard Method"),
        output_box_container=output_box_container,
        warning_box_container=warning_box_container,
        warning_handler=warning_handler,
    )
    assert "simulated successfully" in output_box_container[0].output_content


def test_create_warning_handler():
    handler = create_warning_handler()
    with pytest.warns(None) as record:
        handler.warn("Test warning", category=UserWarning)
    assert len(record) == 1
    assert record[0].message.args[0] == "Test warning"
