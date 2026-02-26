"""
Test pedigree extraction directly
"""

from update_from_list import ListBasedUpdater

def main():
    print("="*60)
    print("Testing _get_pedigree_info() directly")
    print("="*60)

    updater = ListBasedUpdater()

    horse_id = '2021105700'
    print(f"\nTesting with horse_id: {horse_id}")
    print(f"URL: https://db.netkeiba.com/horse/{horse_id}/")

    pedigree = updater._get_pedigree_info(horse_id)

    print(f"\nPedigree info returned:")
    print(f"  Type: {type(pedigree)}")
    print(f"  Content: {pedigree}")

    if pedigree:
        print(f"\n  father: {pedigree.get('father')}")
        print(f"  mother_father: {pedigree.get('mother_father')}")

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
