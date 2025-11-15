import os
from fetch_actual_payouts import get_payout_data

# キャッシュ削除
if os.path.exists('payout_cache.pkl'):
    os.remove('payout_cache.pkl')
    print("キャッシュ削除完了\n")

# テスト取得
print("配当データ取得テスト（1レース）")
print("=" * 60)
data = get_payout_data('202006010101')

if data:
    print(f"\n取得成功！")
    for bet_type, payouts in data.items():
        if bet_type != 'race_id':
            print(f"\n[{bet_type}]")
            for item in payouts[:2]:  # 最初の2件だけ表示
                print(f"  {item}")
else:
    print("取得失敗")
