"""
Integration tests for lazy loading workflow.

This test suite covers end-to-end lazy loading functionality:
- DataService integration with lazy loading
- Memory usage verification
- Performance comparison (standard vs lazy)
- Error handling with real FITS files
- StateManager integration
- Large file handling scenarios
"""

import pytest
import os
import tempfile
import numpy as np
import psutil
from unittest.mock import patch, MagicMock
from astropy.io import fits
from stingray import EventList

from services.data_service import DataService
from utils.state_manager import StateManager
from utils.lazy_loader import LazyEventLoader, assess_loading_risk


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def state_manager():
    """Create a fresh StateManager instance for each test."""
    return StateManager()


@pytest.fixture
def data_service(state_manager):
    """Create DataService instance with StateManager."""
    service = DataService(state_manager)
    return service


@pytest.fixture
def sample_evt_file():
    """Path to real small sample EVT file."""
    return "files/data/monol_testA.evt"


@pytest.fixture
def sample_fits_file():
    """Path to real small sample FITS file."""
    return "files/data/lcurveA.fits"


@pytest.fixture
def synthetic_small_fits():
    """
    Create a synthetic small FITS file (~100KB) for testing.

    Yields path to temporary file, cleaned up after test.
    """
    # Create temporary file
    fd, tmp_path = tempfile.mkstemp(suffix='.evt')
    os.close(fd)

    try:
        # Generate synthetic event data
        n_events = 10000
        tstart = 0.0
        duration = 1000.0

        times = np.sort(np.random.uniform(tstart, tstart + duration, n_events))
        energy = np.random.uniform(0.5, 10.0, n_events)
        pi = (energy * 100).astype(np.int32)

        # Create FITS file structure
        # Primary HDU
        primary = fits.PrimaryHDU()

        # Events extension
        col1 = fits.Column(name='TIME', format='D', array=times)
        col2 = fits.Column(name='ENERGY', format='E', array=energy)
        col3 = fits.Column(name='PI', format='J', array=pi)

        cols = fits.ColDefs([col1, col2, col3])
        events_hdu = fits.BinTableHDU.from_columns(cols)
        events_hdu.header['EXTNAME'] = 'EVENTS'
        events_hdu.header['TELESCOP'] = 'TEST'
        events_hdu.header['INSTRUME'] = 'SYNTHETIC'
        events_hdu.header['MJDREFI'] = 55000
        events_hdu.header['MJDREFF'] = 0.0
        events_hdu.header['TIMEZERO'] = 0.0
        events_hdu.header['TIMEUNIT'] = 's'
        # Add required timing keywords
        events_hdu.header['TSTART'] = tstart
        events_hdu.header['TSTOP'] = tstart + duration
        events_hdu.header['TIMESYS'] = 'TT'
        events_hdu.header['TIMEREF'] = 'LOCAL'

        # GTI extension
        gti_start = np.array([tstart])
        gti_stop = np.array([tstart + duration])

        col1 = fits.Column(name='START', format='D', array=gti_start)
        col2 = fits.Column(name='STOP', format='D', array=gti_stop)

        gti_cols = fits.ColDefs([col1, col2])
        gti_hdu = fits.BinTableHDU.from_columns(gti_cols)
        gti_hdu.header['EXTNAME'] = 'GTI'

        # Write FITS file
        hdul = fits.HDUList([primary, events_hdu, gti_hdu])
        hdul.writeto(tmp_path, overwrite=True)

        yield tmp_path

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture
def synthetic_large_fits_info():
    """
    Return parameters for a hypothetical large FITS file.

    We don't actually create it (too slow/large), but return
    characteristics for testing logic.
    """
    return {
        'file_size': 2.5 * 1024**3,  # 2.5 GB
        'n_events': 200_000_000,  # 200 million events
        'duration': 50000.0,  # seconds
    }


# =============================================================================
# Integration Tests: DataService with Lazy Loading
# =============================================================================

def test_load_event_list_lazy_small_file_safe(data_service, synthetic_small_fits):
    """
    Test lazy loading with a small file that's safe to load.

    Should use standard loading method since file is small.
    """
    result = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="test_small",
        safety_margin=0.5
    )

    # Should succeed
    assert result["success"] is True
    assert result["data"] is not None
    assert isinstance(result["data"], EventList)

    # Should use standard method for small file
    assert result["metadata"]["method"] == "standard"
    assert result["metadata"]["memory_safe"] is True

    # Verify data is in state manager
    assert data_service.state.has_event_data("test_small")
    retrieved = data_service.state.get_event_data("test_small")
    assert len(retrieved) == len(result["data"].time)


def test_load_event_list_lazy_duplicate_name(data_service, synthetic_small_fits):
    """Test that lazy loading prevents duplicate names."""
    # Load first time
    result1 = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="duplicate_test",
        safety_margin=0.5
    )
    assert result1["success"] is True

    # Try loading again with same name
    result2 = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="duplicate_test",
        safety_margin=0.5
    )
    assert result2["success"] is False
    assert "already exists" in result2["message"]


def test_load_event_list_lazy_nonexistent_file(data_service):
    """Test lazy loading with non-existent file."""
    result = data_service.load_event_list_lazy(
        file_path="/nonexistent/file.evt",
        name="test_missing",
        safety_margin=0.5
    )

    assert result["success"] is False
    assert result["data"] is None
    assert "error" in result


def test_check_file_size_small_file(data_service, synthetic_small_fits):
    """Test file size checking with small file."""
    result = data_service.check_file_size(synthetic_small_fits)

    assert result["success"] is True
    data = result["data"]

    # Verify structure
    assert "file_size_bytes" in data
    assert "file_size_mb" in data
    assert "file_size_gb" in data
    assert "risk_level" in data
    assert "recommend_lazy" in data
    assert "estimated_memory_mb" in data
    assert "memory_info" in data

    # Small file should be safe
    assert data["risk_level"] == "safe"
    assert data["recommend_lazy"] is False
    assert data["file_size_gb"] < 0.1


def test_check_file_size_with_real_evt(data_service, sample_evt_file):
    """Test file size checking with real sample EVT file."""
    if not os.path.exists(sample_evt_file):
        pytest.skip(f"Sample file {sample_evt_file} not found")

    result = data_service.check_file_size(sample_evt_file)

    assert result["success"] is True
    data = result["data"]

    # Should be safe for small file
    assert data["risk_level"] == "safe"
    assert data["file_size_mb"] < 1.0  # Sample files are < 1MB


def test_get_file_metadata(data_service, synthetic_small_fits):
    """Test metadata extraction without loading full data."""
    result = data_service.get_file_metadata(synthetic_small_fits)

    assert result["success"] is True
    metadata = result["data"]

    # Verify metadata structure
    assert "gti" in metadata
    assert "mjdref" in metadata
    assert "n_events_estimate" in metadata
    assert "time_range" in metadata
    assert "file_size_mb" in metadata
    assert "duration_s" in metadata

    # Verify reasonable values
    assert metadata["duration_s"] > 0
    assert metadata["n_events_estimate"] > 0


def test_is_large_file(data_service, synthetic_small_fits):
    """Test large file detection."""
    # Small file
    assert data_service.is_large_file(synthetic_small_fits, threshold_gb=1.0) is False

    # With very small threshold
    assert data_service.is_large_file(synthetic_small_fits, threshold_gb=0.00001) is True


# =============================================================================
# Integration Tests: Memory Usage Monitoring
# =============================================================================

def test_memory_usage_during_loading(data_service, synthetic_small_fits):
    """
    Test that memory usage is tracked during loading.

    Verifies performance monitoring integration.
    """
    # Get initial memory
    process = psutil.Process()
    mem_before = process.memory_info().rss / (1024**2)  # MB

    # Load file
    result = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="mem_test",
        safety_margin=0.5
    )

    # Get final memory
    mem_after = process.memory_info().rss / (1024**2)  # MB

    # Should succeed
    assert result["success"] is True

    # Memory should increase (but not by much for small file)
    mem_increase = mem_after - mem_before
    assert mem_increase >= 0  # Memory should not decrease

    # For small test file (~100KB), increase should be < 50 MB
    assert mem_increase < 50


def test_lazy_loader_memory_info(synthetic_small_fits):
    """Test LazyEventLoader memory info reporting."""
    loader = LazyEventLoader(synthetic_small_fits)
    mem_info = loader.get_system_memory_info()

    # Verify structure
    assert "total_mb" in mem_info
    assert "available_mb" in mem_info
    assert "used_mb" in mem_info
    assert "percent" in mem_info
    assert "process_mb" in mem_info

    # Verify reasonable values
    assert mem_info["total_mb"] > 0
    assert mem_info["available_mb"] > 0
    assert 0 <= mem_info["percent"] <= 100


# =============================================================================
# Integration Tests: Error Handling
# =============================================================================

def test_load_corrupted_fits_file(data_service):
    """Test loading a corrupted FITS file."""
    # Create corrupted file
    fd, tmp_path = tempfile.mkstemp(suffix='.evt')
    try:
        os.write(fd, b"This is not a valid FITS file")
        os.close(fd)

        result = data_service.load_event_list_lazy(
            file_path=tmp_path,
            name="corrupted",
            safety_margin=0.5
        )

        # Should fail gracefully
        assert result["success"] is False
        assert "error" in result

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_load_with_memory_error_simulation(data_service, synthetic_small_fits):
    """
    Test handling of MemoryError during loading.

    Simulates out-of-memory condition.
    """
    # Patch EventList.read to raise MemoryError
    with patch('utils.lazy_loader.EventList.read', side_effect=MemoryError("Out of memory")):
        result = data_service.load_event_list_lazy(
            file_path=synthetic_small_fits,
            name="oom_test",
            safety_margin=0.5
        )

        # Should fail with specific message
        assert result["success"] is False
        assert "Out of memory" in result["message"] or "memory" in result["message"].lower()


# =============================================================================
# Integration Tests: Performance Comparison
# =============================================================================

def test_standard_vs_lazy_loading_workflow(data_service, synthetic_small_fits):
    """
    Compare standard vs lazy loading workflow.

    For small files, both should work, but lazy adds overhead.
    """
    import time

    # Test standard loading
    start = time.time()
    result_standard = data_service.load_event_list(
        file_path=synthetic_small_fits,
        name="standard_test",
        fmt="ogip"
    )
    time_standard = time.time() - start

    assert result_standard["success"] is True

    # Test lazy loading (with new name)
    start = time.time()
    result_lazy = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="lazy_test",
        safety_margin=0.5
    )
    time_lazy = time.time() - start

    assert result_lazy["success"] is True

    # Both should produce same size event list
    ev1 = result_standard["data"]
    ev2 = result_lazy["data"]
    assert len(ev1.time) == len(ev2.time)

    # Print timing info for reference
    print(f"\nTiming comparison:")
    print(f"  Standard: {time_standard:.4f}s")
    print(f"  Lazy:     {time_lazy:.4f}s")
    print(f"  Ratio:    {time_lazy/time_standard:.2f}x")


# =============================================================================
# Integration Tests: Risk Assessment
# =============================================================================

def test_assess_loading_risk_integration(synthetic_large_fits_info):
    """Test risk assessment with realistic large file parameters."""
    file_size = synthetic_large_fits_info['file_size']

    # Get actual available memory
    available_mem = psutil.virtual_memory().available

    # Assess risk
    risk = assess_loading_risk(file_size, file_format='fits', available_memory=available_mem)

    # For 2.5 GB file with 8x multiplier (20 GB needed):
    # - If available < 33 GB: critical (>90%)
    # - If available < 67 GB: risky (60-90%)
    # - If available < 22 GB: caution (30-60%)
    # This will vary by system

    assert risk in ['safe', 'caution', 'risky', 'critical']

    # Log for debugging
    print(f"\nRisk assessment for {file_size/(1024**3):.1f}GB file:")
    print(f"  Available RAM: {available_mem/(1024**3):.1f}GB")
    print(f"  Risk level: {risk}")


def test_lazy_loading_recommendation_logic(data_service, synthetic_small_fits):
    """Test the logic for recommending lazy loading."""
    result = data_service.check_file_size(synthetic_small_fits)

    assert result["success"] is True
    data = result["data"]

    # For small file: should NOT recommend lazy loading
    assert data["recommend_lazy"] is False

    # Manually test logic with mocked large file
    with patch('os.path.getsize', return_value=2.5 * 1024**3):  # 2.5 GB
        result_large = data_service.check_file_size("fake_large.evt")

        if result_large["success"]:
            # Should recommend lazy for large file
            assert result_large["data"]["recommend_lazy"] is True
            assert result_large["data"]["file_size_gb"] > 1.0


# =============================================================================
# Integration Tests: Streaming Operations
# =============================================================================

def test_lazy_loader_streaming_segments(synthetic_small_fits):
    """Test streaming segments from LazyEventLoader."""
    loader = LazyEventLoader(synthetic_small_fits)

    # Stream in 100s segments
    segments = list(loader.stream_segments(segment_size=100.0))

    # Should get multiple segments
    assert len(segments) > 0

    # Each segment should be a numpy array
    for segment in segments:
        assert isinstance(segment, np.ndarray)
        assert len(segment) > 0

    # Total events should match full load
    total_streamed = sum(len(seg) for seg in segments)

    full_events = loader.load_full()
    assert total_streamed == len(full_events.time)


def test_lazy_loader_lightcurve_streaming(synthetic_small_fits):
    """Test streaming lightcurve creation."""
    loader = LazyEventLoader(synthetic_small_fits)

    # Create lightcurve via streaming
    lc_segments = list(loader.create_lightcurve_streaming(
        segment_size=100.0,
        dt=1.0
    ))

    # Should get segments
    assert len(lc_segments) > 0

    # Each segment should be (times, counts) tuple
    for times, counts in lc_segments:
        assert isinstance(times, np.ndarray)
        assert isinstance(counts, np.ndarray)
        assert len(times) == len(counts)
        assert len(times) > 0


# =============================================================================
# Integration Tests: Full Workflow
# =============================================================================

def test_complete_lazy_loading_workflow(data_service, synthetic_small_fits):
    """
    Test complete workflow: check size -> load with lazy -> verify -> delete.

    This simulates the full user workflow in the dashboard.
    """
    # Step 1: Check file size
    check_result = data_service.check_file_size(synthetic_small_fits)
    assert check_result["success"] is True

    file_info = check_result["data"]
    print(f"\nFile info: {file_info['file_size_mb']:.2f} MB, risk: {file_info['risk_level']}")

    # Step 2: Get metadata (fast preview)
    metadata_result = data_service.get_file_metadata(synthetic_small_fits)
    assert metadata_result["success"] is True

    metadata = metadata_result["data"]
    print(f"Metadata: ~{metadata['n_events_estimate']} events, {metadata['duration_s']:.1f}s duration")

    # Step 3: Load with lazy method (auto-decides standard vs lazy)
    load_result = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="workflow_test",
        safety_margin=0.5
    )
    assert load_result["success"] is True

    event_list = load_result["data"]
    print(f"Loaded: {len(event_list.time)} events via {load_result['metadata']['method']} method")

    # Step 4: Verify data is accessible
    get_result = data_service.get_event_list("workflow_test")
    assert get_result["success"] is True
    assert get_result["data"] is not None

    # Step 5: List all event lists
    list_result = data_service.list_event_lists()
    assert list_result["success"] is True
    assert len(list_result["data"]) >= 1

    # Step 6: Delete
    delete_result = data_service.delete_event_list("workflow_test")
    assert delete_result["success"] is True

    # Verify deleted
    assert not data_service.state.has_event_data("workflow_test")


def test_multiple_files_mixed_loading(data_service, synthetic_small_fits):
    """Test loading multiple files with different methods."""
    # Load first file with standard method
    result1 = data_service.load_event_list(
        file_path=synthetic_small_fits,
        name="file1",
        fmt="ogip"
    )
    assert result1["success"] is True

    # Load second file with lazy method
    result2 = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="file2",
        safety_margin=0.5
    )
    assert result2["success"] is True

    # Both should be accessible
    assert data_service.state.has_event_data("file1")
    assert data_service.state.has_event_data("file2")

    # List should show both
    list_result = data_service.list_event_lists()
    assert len(list_result["data"]) == 2


# =============================================================================
# Edge Cases
# =============================================================================

def test_empty_file_handling(data_service):
    """Test handling of empty FITS file."""
    fd, tmp_path = tempfile.mkstemp(suffix='.evt')
    os.close(fd)

    try:
        result = data_service.load_event_list_lazy(
            file_path=tmp_path,
            name="empty",
            safety_margin=0.5
        )

        # Should fail (empty file is invalid FITS)
        assert result["success"] is False

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_very_high_safety_margin(data_service, synthetic_small_fits):
    """Test lazy loading with very conservative safety margin."""
    # 99% safety margin means only use 1% of available RAM
    result = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="conservative",
        safety_margin=0.01  # Only use 1% of RAM
    )

    # Should still succeed for small file
    # (might use 'standard_risky' method if safety check fails)
    assert result["success"] is True


def test_zero_safety_margin(data_service, synthetic_small_fits):
    """Test lazy loading with zero safety margin (risky!)."""
    # Safety margin of 0 means no safety checks
    result = data_service.load_event_list_lazy(
        file_path=synthetic_small_fits,
        name="risky",
        safety_margin=0.0
    )

    # Should fail or warn (depends on implementation)
    # Small file should still load
    assert result["success"] is True or "warning" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
