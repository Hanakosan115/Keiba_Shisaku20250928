"""
_save_dataメソッドのロジックをシミュレーション
"""
import pandas as pd

print("Simulating _save_data logic...")
print()

# 既存データ（Umaban列を使用）
existing_df = pd.DataFrame([
    {'race_id': 'R001', 'Umaban': 1, 'HorseName': 'Horse_A_Old', 'Rank': 1},
    {'race_id': 'R001', 'Umaban': 2, 'HorseName': 'Horse_B_Old', 'Rank': 2},
    {'race_id': 'R002', 'Umaban': 1, 'HorseName': 'Horse_C_Old', 'Rank': 1},
])

print("Existing data (Umaban column):")
print(existing_df)
print()

# 新データ（馬番列を使用）
new_df = pd.DataFrame([
    {'race_id': 'R003', '馬番': 1, 'HorseName': 'Horse_D_New', 'Rank': 1},
    {'race_id': 'R003', '馬番': 2, 'HorseName': 'Horse_E_New', 'Rank': 2},
    {'race_id': 'R003', '馬番': 3, 'HorseName': 'Horse_F_New', 'Rank': 3},
])

print("New data (馬番 column):")
print(new_df)
print()

# 列の統一（_save_dataメソッドの1294-1301行）
for col in new_df.columns:
    if col not in existing_df.columns:
        existing_df[col] = None

for col in existing_df.columns:
    if col not in new_df.columns:
        new_df[col] = None

# 列順を既存データに合わせる
new_df = new_df[existing_df.columns]

print("After column unification:")
print("existing_df columns:", existing_df.columns.tolist())
print("new_df columns:", new_df.columns.tolist())
print()

# 結合
combined_df = pd.concat([existing_df, new_df], ignore_index=True)

print("Combined data (before deduplication):")
print(combined_df)
print()

# 重複削除ロジック（1310-1316行）
if '馬番' in combined_df.columns:
    print("Using '馬番' for deduplication")
    combined_df_dedup = combined_df.drop_duplicates(subset=['race_id', '馬番'], keep='last')
elif 'Umaban' in combined_df.columns:
    print("Using 'Umaban' for deduplication")
    combined_df_dedup = combined_df.drop_duplicates(subset=['race_id', 'Umaban'], keep='last')
else:
    print("Using 'race_id' only for deduplication")
    combined_df_dedup = combined_df.drop_duplicates(subset=['race_id'], keep='last')

print()
print("After deduplication:")
print(combined_df_dedup)
print()
print(f"Original rows: {len(combined_df)}")
print(f"After dedup: {len(combined_df_dedup)}")
print(f"Rows removed: {len(combined_df) - len(combined_df_dedup)}")
