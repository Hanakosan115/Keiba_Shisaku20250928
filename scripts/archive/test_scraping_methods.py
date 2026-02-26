"""
Direct test of enhanced scraping methods
Tests get_result_table() and _get_pedigree_info()
"""

from update_from_list import ListBasedUpdater
import pandas as pd

def test_single_race(race_id):
    """Test scraping a single race"""
    print(f"\n{'='*60}")
    print(f"Testing race_id: {race_id}")
    print(f"{'='*60}")

    updater = ListBasedUpdater()

    # Test get_result_table
    print(f"\n1. Testing get_result_table()...")
    try:
        race_info, result_table = updater.get_result_table(race_id)

        print(f"\n   Race Information:")
        for key, value in race_info.items():
            print(f"     {key}: {value}")

        print(f"\n   Result Table:")
        print(f"     Headers: {result_table[0]}")
        print(f"     Rows: {len(result_table) - 1}")

        if len(result_table) > 1:
            print(f"     First horse data sample:")
            for i, (header, value) in enumerate(zip(result_table[0][:10], result_table[1][:10])):
                print(f"       {header}: {value}")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test scrape_race_result (which includes pedigree)
    print(f"\n2. Testing scrape_race_result()...")
    try:
        df = updater.scrape_race_result(race_id)

        if df is not None and len(df) > 0:
            print(f"\n   DataFrame created successfully!")
            print(f"     Shape: {df.shape}")
            print(f"     Columns: {len(df.columns)}")

            # Show important columns
            important_cols = [
                'race_id', 'race_name', 'race_num', 'distance', 'course_type',
                'weather', 'track_condition', 'start_time', 'date',
                'horse_name', 'horse_id', 'father', 'mother_father',
                'jockey', 'odds', 'popularity'
            ]

            print(f"\n   Sample data (first horse):")
            for col in important_cols:
                if col in df.columns:
                    print(f"     {col}: {df.iloc[0][col]}")

            return True
        else:
            print(f"   ERROR: DataFrame is None or empty")
            return False

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("Enhanced Scraping Methods Test")
    print("="*60)
    print("\nNote: VPN connection required!")
    print()

    # Test with a known race ID from CSV
    test_race_id = '202507050211'  # User mentioned this race exists

    success = test_single_race(test_race_id)

    print(f"\n{'='*60}")
    if success:
        print("TEST PASSED: All methods working correctly!")
    else:
        print("TEST FAILED: Check errors above")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
