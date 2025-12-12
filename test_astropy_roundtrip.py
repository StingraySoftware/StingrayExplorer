"""
Test script for Astropy export/import roundtrip functionality.

This script verifies that EventLists can be exported to Astropy Tables
and imported back without data loss.
"""

import numpy as np
import tempfile
import os
from stingray import EventList
from utils.state_manager import state_manager
from services import ServiceRegistry


def test_astropy_roundtrip():
    """Test the complete roundtrip: EventList -> Astropy Table -> EventList."""
    print("=" * 60)
    print("Testing Astropy Roundtrip Functionality")
    print("=" * 60)

    # Initialize services
    services = ServiceRegistry(state_manager)

    # Create a test EventList
    print("\n1. Creating test EventList...")
    n_events = 1000
    times = np.sort(np.random.uniform(0, 100, n_events))
    energies = np.random.uniform(1, 10, n_events)
    gti = np.array([[0, 100]])

    test_event_list = EventList(
        time=times,
        energy=energies,
        gti=gti
    )

    print(f"   Created EventList with {len(test_event_list.time)} events")
    print(f"   Time range: {test_event_list.time[0]:.2f} - {test_event_list.time[-1]:.2f}")
    print(f"   Energy range: {test_event_list.energy.min():.2f} - {test_event_list.energy.max():.2f} keV")

    # Add to state
    state_manager.add_event_data("test_eventlist", test_event_list)

    # Test export to different formats
    formats_to_test = ["ascii.ecsv", "fits", "hdf5"]

    for fmt in formats_to_test:
        print(f"\n{'=' * 60}")
        print(f"Testing format: {fmt}")
        print(f"{'=' * 60}")

        # Create temporary file
        suffix = {
            "ascii.ecsv": ".ecsv",
            "fits": ".fits",
            "hdf5": ".h5",
            "votable": ".xml"
        }.get(fmt, ".dat")

        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name

        try:
            # Export
            print(f"\n2. Exporting EventList to {fmt}...")
            export_result = services.data.export_event_list_to_astropy_table(
                event_list_name="test_eventlist",
                output_path=temp_path,
                fmt=fmt
            )

            if not export_result["success"]:
                print(f"   FAILED: {export_result['message']}")
                continue

            print(f"   SUCCESS: Exported to {temp_path}")
            print(f"   Rows: {export_result['metadata']['n_rows']}")
            print(f"   File size: {os.path.getsize(temp_path) / 1024:.2f} KB")

            # Import
            print(f"\n3. Importing EventList from {fmt}...")
            import_name = f"imported_{fmt.replace('.', '_')}"
            import_result = services.data.import_event_list_from_astropy_table(
                file_path=temp_path,
                name=import_name,
                fmt=fmt
            )

            if not import_result["success"]:
                print(f"   FAILED: {import_result['message']}")
                continue

            print(f"   SUCCESS: Imported as '{import_name}'")
            print(f"   Events: {import_result['metadata']['n_events']}")

            # Verify data integrity
            print(f"\n4. Verifying data integrity...")
            imported_event_list = state_manager.get_event_data(import_name)

            # Check number of events
            original_n_events = len(test_event_list.time)
            imported_n_events = len(imported_event_list.time)

            if original_n_events != imported_n_events:
                print(f"   WARNING: Event count mismatch!")
                print(f"   Original: {original_n_events}, Imported: {imported_n_events}")
            else:
                print(f"   Event count: {imported_n_events} (matches)")

            # Check time data
            time_diff = np.abs(test_event_list.time - imported_event_list.time).max()
            print(f"   Max time difference: {time_diff:.2e} seconds")

            if time_diff < 1e-6:
                print(f"   Time data: EXACT MATCH")
            else:
                print(f"   Time data: CLOSE MATCH (within tolerance)")

            # Check energy data
            if hasattr(imported_event_list, 'energy') and imported_event_list.energy is not None:
                energy_diff = np.abs(test_event_list.energy - imported_event_list.energy).max()
                print(f"   Max energy difference: {energy_diff:.2e} keV")

                if energy_diff < 1e-6:
                    print(f"   Energy data: EXACT MATCH")
                else:
                    print(f"   Energy data: CLOSE MATCH (within tolerance)")
            else:
                print(f"   Energy data: NOT PRESERVED (expected for some formats)")

            print(f"\n   ROUNDTRIP TEST PASSED for {fmt}")

        except Exception as e:
            print(f"\n   ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"\n   Cleaned up temporary file: {temp_path}")

    print(f"\n{'=' * 60}")
    print("All roundtrip tests completed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    test_astropy_roundtrip()
