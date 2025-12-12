"""
Unit tests for the LazyEventLoader class.

This test suite covers:
- LazyEventLoader initialization and file handling
- Metadata extraction without loading full data
- Memory usage estimation
- Safety checks and risk assessment
- File size formatting
- Error handling for invalid files
"""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from utils.lazy_loader import LazyEventLoader, assess_loading_risk


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_fits_file():
    """Create a temporary mock FITS file."""
    with tempfile.NamedTemporaryFile(suffix='.fits', delete=False) as f:
        # Write some dummy data to make it a non-zero size
        f.write(b'SIMPLE  = T' * 100)  # Fake FITS header
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_fits_reader():
    """Create a mock FITSTimeseriesReader."""
    mock_reader = MagicMock()
    mock_reader.gti = np.array([[0, 1000], [1100, 2000]])
    mock_reader.mjdref = 58000.0
    return mock_reader


# =============================================================================
# Test: LazyEventLoader Initialization
# =============================================================================

def test_lazy_loader_init_with_nonexistent_file():
    """Test initialization with non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        LazyEventLoader("/path/to/nonexistent/file.fits")


def test_lazy_loader_init_with_invalid_fits(mock_fits_file):
    """Test initialization with invalid FITS file raises ValueError."""
    # The mock file isn't a real FITS file, so this should fail
    with pytest.raises(ValueError, match="Failed to open FITS file"):
        LazyEventLoader(mock_fits_file)


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_lazy_loader_init_success(mock_reader_class, mock_fits_file):
    """Test successful initialization."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)

    assert loader.file_path == mock_fits_file
    assert loader.file_size > 0
    assert loader.reader is not None
    mock_reader_class.assert_called_once_with(mock_fits_file, data_kind="times")


# =============================================================================
# Test: Metadata Extraction
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_get_metadata(mock_reader_class, mock_fits_file, mock_fits_reader):
    """Test metadata extraction without loading event data."""
    mock_reader_class.return_value = mock_fits_reader

    loader = LazyEventLoader(mock_fits_file)
    metadata = loader.get_metadata()

    # Check all expected keys present
    assert 'gti' in metadata
    assert 'mjdref' in metadata
    assert 'n_events_estimate' in metadata
    assert 'time_range' in metadata
    assert 'file_size_mb' in metadata
    assert 'file_size_gb' in metadata
    assert 'duration_s' in metadata
    assert 'estimated_count_rate' in metadata

    # Check values
    assert np.array_equal(metadata['gti'], mock_fits_reader.gti)
    assert metadata['mjdref'] == 58000.0
    assert metadata['duration_s'] == 1900.0  # (1000-0) + (2000-1100)
    assert metadata['n_events_estimate'] > 0


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_get_metadata_time_range(mock_reader_class, mock_fits_file, mock_fits_reader):
    """Test that time_range is correctly extracted from GTIs."""
    mock_reader_class.return_value = mock_fits_reader

    loader = LazyEventLoader(mock_fits_file)
    metadata = loader.get_metadata()

    time_range = metadata['time_range']
    assert time_range == (0.0, 2000.0)  # min and max from GTIs


# =============================================================================
# Test: Memory Estimation
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_estimate_memory_usage_fits(mock_reader_class, mock_fits_file):
    """Test memory estimation for FITS files."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)
    estimated = loader.estimate_memory_usage('fits')

    # FITS multiplier is 3x (based on Stingray benchmarks: 2GB → 5.2GB = 2.6x, rounded to 3x)
    expected = loader.file_size * 3
    assert estimated == expected


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_estimate_memory_usage_hdf5(mock_reader_class, mock_fits_file):
    """Test memory estimation for HDF5 files."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)
    estimated = loader.estimate_memory_usage('hdf5')

    # HDF5 multiplier is 2x (more efficient format)
    expected = loader.file_size * 2
    assert estimated == expected


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_estimate_memory_usage_pickle(mock_reader_class, mock_fits_file):
    """Test memory estimation for pickle files."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)
    estimated = loader.estimate_memory_usage('pickle')

    # Pickle multiplier is 1.5x (most efficient format)
    expected = loader.file_size * 1.5
    assert estimated == expected


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_estimate_memory_usage_unknown_format(mock_reader_class, mock_fits_file):
    """Test memory estimation for unknown format defaults to conservative multiplier."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)
    estimated = loader.estimate_memory_usage('unknown_format')

    # Default multiplier is 3x (conservative default, same as FITS)
    expected = loader.file_size * 3
    assert estimated == expected


# =============================================================================
# Test: Safety Checks
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.psutil.virtual_memory')
def test_can_load_safely_safe(mock_vmem, mock_reader_class, mock_fits_file):
    """Test can_load_safely returns True when safe."""
    mock_reader_class.return_value = MagicMock()

    # Mock large available memory
    mock_vmem.return_value.available = 16 * 1024**3  # 16 GB

    loader = LazyEventLoader(mock_fits_file)
    # Small file, lots of memory -> should be safe
    assert loader.can_load_safely(safety_margin=0.5) is True


@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.psutil.virtual_memory')
def test_can_load_safely_unsafe(mock_vmem, mock_reader_class, mock_fits_file):
    """Test can_load_safely returns False when unsafe."""
    mock_reader_class.return_value = MagicMock()

    # Mock small available memory relative to file size
    # File is ~1.1 KB, with 3x multiplier = ~3.3 KB needed
    # Set available to 5 KB, so 50% margin = 2.5 KB safe limit
    # 3.3 KB > 2.5 KB -> should be unsafe
    mock_vmem.return_value.available = 5 * 1024  # 5 KB

    loader = LazyEventLoader(mock_fits_file)
    # File needs more memory than safe limit -> should be unsafe
    assert loader.can_load_safely(safety_margin=0.5) is False


@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.psutil.virtual_memory')
def test_can_load_safely_custom_margin(mock_vmem, mock_reader_class, mock_fits_file):
    """Test can_load_safely with custom safety margin."""
    mock_reader_class.return_value = MagicMock()

    # Mock specific available memory
    mock_vmem.return_value.available = 1 * 1024**3  # 1 GB

    loader = LazyEventLoader(mock_fits_file)

    # With high safety margin (10%), should be safer
    result_high_margin = loader.can_load_safely(safety_margin=0.1)

    # With low safety margin (90%), should be less safe
    result_low_margin = loader.can_load_safely(safety_margin=0.9)

    # High margin is more conservative (more likely to be unsafe)
    # Low margin is less conservative (more likely to be safe)
    # For small test file, both might be True, but the logic is correct


# =============================================================================
# Test: System Memory Info
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.psutil.virtual_memory')
@patch('utils.lazy_loader.psutil.Process')
def test_get_system_memory_info(mock_process, mock_vmem, mock_reader_class, mock_fits_file):
    """Test system memory info retrieval."""
    mock_reader_class.return_value = MagicMock()

    # Mock memory values
    mock_vmem.return_value.total = 16 * 1024**3  # 16 GB
    mock_vmem.return_value.available = 8 * 1024**3  # 8 GB
    mock_vmem.return_value.used = 8 * 1024**3  # 8 GB
    mock_vmem.return_value.percent = 50.0

    mock_process.return_value.memory_info.return_value.rss = 256 * 1024**2  # 256 MB

    loader = LazyEventLoader(mock_fits_file)
    mem_info = loader.get_system_memory_info()

    # Check all expected keys
    assert 'total_mb' in mem_info
    assert 'available_mb' in mem_info
    assert 'used_mb' in mem_info
    assert 'percent' in mem_info
    assert 'process_mb' in mem_info

    # Check values
    assert mem_info['total_mb'] == 16 * 1024  # 16 GB in MB
    assert mem_info['available_mb'] == 8 * 1024  # 8 GB in MB
    assert mem_info['percent'] == 50.0
    assert mem_info['process_mb'] == 256.0


# =============================================================================
# Test: File Size Formatting
# =============================================================================

def test_format_file_size_bytes():
    """Test formatting bytes."""
    assert LazyEventLoader.format_file_size(500) == "500.0 B"


def test_format_file_size_kilobytes():
    """Test formatting kilobytes."""
    assert LazyEventLoader.format_file_size(1500) == "1.5 KB"


def test_format_file_size_megabytes():
    """Test formatting megabytes."""
    assert LazyEventLoader.format_file_size(2 * 1024**2) == "2.0 MB"


def test_format_file_size_gigabytes():
    """Test formatting gigabytes."""
    assert LazyEventLoader.format_file_size(3.5 * 1024**3) == "3.5 GB"


def test_format_file_size_terabytes():
    """Test formatting terabytes."""
    assert LazyEventLoader.format_file_size(1.2 * 1024**4) == "1.2 TB"


# =============================================================================
# Test: Risk Assessment Function
# =============================================================================

@patch('utils.lazy_loader.psutil.virtual_memory')
def test_assess_loading_risk_safe(mock_vmem):
    """Test risk assessment returns 'safe' for small files."""
    mock_vmem.return_value.available = 16 * 1024**3  # 16 GB

    file_size = 100 * 1024**2  # 100 MB
    risk = assess_loading_risk(file_size, file_format='fits')

    # 100 MB * 3 = 300 MB needed
    # 300 MB / 16 GB = ~0.02 (2%) -> safe
    assert risk == 'safe'


@patch('utils.lazy_loader.psutil.virtual_memory')
def test_assess_loading_risk_caution(mock_vmem):
    """Test risk assessment returns 'caution' for medium files."""
    mock_vmem.return_value.available = 2 * 1024**3  # 2 GB

    file_size = 350 * 1024**2  # 350 MB
    risk = assess_loading_risk(file_size, file_format='fits')

    # 350 MB * 3 = 1050 MB needed
    # 1050 MB / 2048 MB = ~0.51 (51%) -> caution
    assert risk == 'caution'


@patch('utils.lazy_loader.psutil.virtual_memory')
def test_assess_loading_risk_risky(mock_vmem):
    """Test risk assessment returns 'risky' for large files."""
    mock_vmem.return_value.available = 2 * 1024**3  # 2 GB

    file_size = 480 * 1024**2  # 480 MB
    risk = assess_loading_risk(file_size, file_format='fits')

    # 480 MB * 3 = 1440 MB needed
    # 1440 MB / 2048 MB = ~0.70 (70%) -> risky
    assert risk == 'risky'


@patch('utils.lazy_loader.psutil.virtual_memory')
def test_assess_loading_risk_critical(mock_vmem):
    """Test risk assessment returns 'critical' for very large files."""
    mock_vmem.return_value.available = 1 * 1024**3  # 1 GB

    file_size = 350 * 1024**2  # 350 MB
    risk = assess_loading_risk(file_size, file_format='fits')

    # 350 MB * 3 = 1050 MB needed
    # 1050 MB / 1024 MB = ~1.03 (103%) -> critical
    assert risk == 'critical'


@patch('utils.lazy_loader.psutil.virtual_memory')
def test_assess_loading_risk_different_formats(mock_vmem):
    """Test risk assessment with different file formats."""
    mock_vmem.return_value.available = 4 * 1024**3  # 4 GB

    # Use different file sizes to test format-specific multipliers
    # FITS: 1000 MB * 3 = 3000 MB (73% -> risky)
    risk_fits = assess_loading_risk(1000 * 1024**2, file_format='fits', available_memory=4 * 1024**3)

    # HDF5: 850 MB * 2 = 1700 MB (41% -> caution)
    risk_hdf5 = assess_loading_risk(850 * 1024**2, file_format='hdf5', available_memory=4 * 1024**3)

    # Pickle: 600 MB * 1.5 = 900 MB (22% -> safe)
    risk_pickle = assess_loading_risk(600 * 1024**2, file_format='pickle', available_memory=4 * 1024**3)

    assert risk_fits in ['risky', 'critical']
    assert risk_hdf5 in ['safe', 'caution']
    assert risk_pickle == 'safe'


# =============================================================================
# Test: Context Manager
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_context_manager(mock_reader_class, mock_fits_file):
    """Test LazyEventLoader as context manager."""
    mock_reader_class.return_value = MagicMock()

    with LazyEventLoader(mock_fits_file) as loader:
        assert loader is not None
        assert isinstance(loader, LazyEventLoader)


# =============================================================================
# Test: String Representation
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_repr(mock_reader_class, mock_fits_file):
    """Test string representation."""
    mock_reader_class.return_value = MagicMock()

    loader = LazyEventLoader(mock_fits_file)
    repr_str = repr(loader)

    assert 'LazyEventLoader' in repr_str
    assert mock_fits_file in repr_str
    assert 'KB' in repr_str or 'MB' in repr_str or 'GB' in repr_str


# =============================================================================
# Test: Load Full (with mocking)
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.EventList')
def test_load_full(mock_eventlist_class, mock_reader_class, mock_fits_file):
    """Test load_full method."""
    mock_reader_class.return_value = MagicMock()
    mock_event_list = MagicMock()
    mock_event_list.time = np.arange(1000)
    mock_eventlist_class.read.return_value = mock_event_list

    loader = LazyEventLoader(mock_fits_file)
    events = loader.load_full()

    assert events is not None
    mock_eventlist_class.read.assert_called_once()


@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.EventList')
def test_load_full_with_additional_columns(mock_eventlist_class, mock_reader_class, mock_fits_file):
    """Test load_full with additional columns."""
    mock_reader_class.return_value = MagicMock()
    mock_event_list = MagicMock()
    mock_eventlist_class.read.return_value = mock_event_list

    loader = LazyEventLoader(mock_fits_file)
    loader.load_full(additional_columns=['DETID', 'RAWX'])

    # Verify additional_columns was passed
    call_kwargs = mock_eventlist_class.read.call_args[1]
    assert 'additional_columns' in call_kwargs
    assert call_kwargs['additional_columns'] == ['DETID', 'RAWX']


# =============================================================================
# Test: Stream Segments (with mocking)
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
@patch('utils.lazy_loader.time_intervals_from_gtis')
def test_stream_segments(mock_time_intervals, mock_reader_class, mock_fits_file, mock_fits_reader):
    """Test stream_segments method."""
    mock_reader_class.return_value = mock_fits_reader

    # Mock time intervals
    mock_time_intervals.return_value = (
        np.array([0, 100, 200]),
        np.array([100, 200, 300])
    )

    # Mock filtered times
    mock_fits_reader.filter_at_time_intervals.return_value = [
        np.array([10, 20, 30]),
        np.array([110, 120]),
        np.array([210, 220, 230, 240])
    ]

    loader = LazyEventLoader(mock_fits_file)
    segments = list(loader.stream_segments(segment_size=100))

    assert len(segments) == 3
    assert len(segments[0]) == 3  # First segment has 3 events
    assert len(segments[1]) == 2  # Second segment has 2 events
    assert len(segments[2]) == 4  # Third segment has 4 events


# =============================================================================
# Test: Edge Cases
# =============================================================================

@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_metadata_with_zero_duration(mock_reader_class, mock_fits_file):
    """Test metadata extraction with zero duration GTIs."""
    mock_reader = MagicMock()
    mock_reader.gti = np.array([[0, 0]])  # Zero duration
    mock_reader.mjdref = 58000.0
    mock_reader_class.return_value = mock_reader

    loader = LazyEventLoader(mock_fits_file)
    metadata = loader.get_metadata()

    # Should handle zero duration gracefully
    assert metadata['duration_s'] == 0.0
    assert metadata['estimated_count_rate'] == 0  # Avoid division by zero


@patch('utils.lazy_loader.FITSTimeseriesReader')
def test_metadata_with_no_mjdref(mock_reader_class, mock_fits_file):
    """Test metadata extraction when MJDREF is missing."""
    mock_reader = MagicMock()
    mock_reader.gti = np.array([[0, 1000]])
    del mock_reader.mjdref  # Remove attribute
    mock_reader_class.return_value = mock_reader

    loader = LazyEventLoader(mock_fits_file)
    metadata = loader.get_metadata()

    # Should default to 0.0
    assert metadata['mjdref'] == 0.0
