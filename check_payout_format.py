"""配当データの形式を確認"""
import pickle

cache = pickle.load(open(r'C:\Users\bu158\Keiba_Shisaku20250928\payout_cache.pkl', 'rb'))

print("サンプル3レース:")
for idx, (rid, data) in enumerate(list(cache.items())[:3]):
    print(f"\n{'='*60}")
    print(f"レース {rid}:")
    for bet_type, payouts in data.items():
        if bet_type != 'race_id':
            print(f"\n  [{bet_type}]")
            if isinstance(payouts, list):
                for item in payouts[:3]:  # 最初の3件
                    print(f"    馬番: {item.get('馬番', 'N/A')} → 払戻: {item.get('払戻', 'N/A')}")
            else:
                print(f"    {payouts}")
