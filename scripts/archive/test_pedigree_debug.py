"""
Debug pedigree extraction by inspecting the actual HTML
"""

import requests
from bs4 import BeautifulSoup
import time

def main():
    print("="*60)
    print("Debug pedigree HTML structure")
    print("="*60)

    horse_id = '2021105700'
    url = f'https://db.netkeiba.com/horse/{horse_id}/'

    print(f"\nFetching URL: {url}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        time.sleep(1)
        r = session.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding

        print(f"Status code: {r.status_code}")
        print(f"Content length: {len(r.content)} bytes")

        soup = BeautifulSoup(r.content, 'lxml')

        # Try to find the blood_table
        blood_table = soup.select_one('table.blood_table')
        print(f"\nblood_table found: {blood_table is not None}")

        if not blood_table:
            # Look for all tables
            all_tables = soup.find_all('table')
            print(f"\nTotal tables found: {len(all_tables)}")
            for i, table in enumerate(all_tables[:5]):  # Show first 5 tables
                classes = table.get('class', [])
                print(f"  Table {i+1}: classes={classes}")

            # Check for different possible selectors
            print(f"\nTrying different selectors:")
            print(f"  'table.blood-table': {soup.select_one('table.blood-table') is not None}")
            print(f"  'table[summary*=\"血統\"]': {soup.select_one('table[summary*=\"血統\"]') is not None}")
            print(f"  '.blood_table': {soup.select_one('.blood_table') is not None}")

        else:
            print(f"\nblood_table found! Extracting data...")

            # Try to extract father
            father_tag = blood_table.select_one('tr:nth-of-type(1) td:nth-of-type(1) a')
            print(f"Father tag found: {father_tag is not None}")
            if father_tag:
                print(f"  Father: {father_tag.get_text(strip=True)}")

            # Try to extract mother_father
            mother_father_tag = blood_table.select_one('tr:nth-of-type(3) td:nth-of-type(2) a')
            print(f"Mother_father tag found: {mother_father_tag is not None}")
            if mother_father_tag:
                print(f"  Mother_father: {mother_father_tag.get_text(strip=True)}")

            # Show first few rows
            rows = blood_table.find_all('tr')[:5]
            print(f"\nFirst {len(rows)} rows structure:")
            for i, row in enumerate(rows):
                tds = row.find_all(['td', 'th'])
                print(f"  Row {i+1}: {len(tds)} cells")
                for j, cell in enumerate(tds[:3]):  # First 3 cells
                    text = cell.get_text(strip=True)[:30]
                    print(f"    Cell {j+1}: {text}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
