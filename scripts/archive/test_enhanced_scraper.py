"""
Enhanced scraper test script
Tests the integrated functionality from horse_racing_analyzer.py
"""

import sys
import os

# Import the enhanced ListBasedUpdater
from update_from_list import ListBasedUpdater

def main():
    print("="*60)
    print("Enhanced Scraper Test")
    print("="*60)

    # Create temporary test database
    test_db = 'test_netkeiba_enhanced.csv'

    # Remove old test database if exists
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"Removed old test database: {test_db}\n")

    # Initialize updater with test database
    updater = ListBasedUpdater(db_path=test_db)

    print(f"Test configuration:")
    print(f"  - Race ID file: test_race_ids.txt")
    print(f"  - Test database: {test_db}")
    print(f"  - VPN: Connected (required)")
    print()

    # Run update
    updater.update_from_file('test_race_ids.txt')

    print("\n" + "="*60)
    print("Test completed! Checking results...")
    print("="*60)

    # Verify results
    if os.path.exists(test_db):
        import pandas as pd
        df = pd.read_csv(test_db, encoding='utf-8')

        print(f"\nTotal records: {len(df)}")
        print(f"Columns: {len(df.columns)}")
        print(f"\nColumn list:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")

        print(f"\nSample data (first race):")
        if len(df) > 0:
            first_row = df.iloc[0]
            important_fields = [
                'race_id', 'race_name', 'race_num', 'course_type', 'distance',
                'weather', 'track_condition', 'start_time', 'date',
                'horse_name', 'father', 'mother_father', 'jockey',
                'odds', 'popularity'
            ]
            for field in important_fields:
                if field in df.columns:
                    print(f"  {field}: {first_row[field]}")

        print(f"\nBackup files created:")
        backup_files = [f for f in os.listdir('.') if f.startswith('test_netkeiba_enhanced_backup_')]
        for backup in backup_files:
            print(f"  - {backup}")
    else:
        print("\n[ERROR] Test database was not created!")

    print("\n" + "="*60)
    print("Test finished")
    print("="*60)

if __name__ == '__main__':
    main()
