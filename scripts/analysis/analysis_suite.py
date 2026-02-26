"""
統合分析スイート
すべての分析ツールを一箇所から実行
"""
import subprocess
import sys
import os
from datetime import datetime

def print_banner(text):
    """バナー表示"""
    print()
    print("="*80)
    print(f" {text}")
    print("="*80)
    print()

def run_script(script_name, description):
    """スクリプト実行"""
    print(f"実行中: {description}...")
    print(f"スクリプト: {script_name}")
    print("-"*80)

    try:
        result = subprocess.run([sys.executable, script_name], capture_output=False)
        if result.returncode == 0:
            print("-"*80)
            print(f"完了: {description}")
            return True
        else:
            print("-"*80)
            print(f"エラー: {description} (終了コード: {result.returncode})")
            return False
    except Exception as e:
        print("-"*80)
        print(f"エラー: {e}")
        return False

def launch_dashboard():
    """ダッシュボード起動"""
    print("EDAダッシュボードを起動中...")
    print("ブラウザで開きます。終了するにはCtrl+Cを押してください。")
    print("-"*80)

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "eda_dashboard.py"])
    except KeyboardInterrupt:
        print()
        print("ダッシュボードを終了しました。")
    except Exception as e:
        print(f"エラー: {e}")

def main():
    """メイン処理"""
    print_banner("競馬データ統合分析スイート")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # データベース存在確認
    db_path = 'netkeiba_data_2020_2024_enhanced.csv'
    if not os.path.exists(db_path):
        print(f"エラー: データベースファイルが見つかりません: {db_path}")
        print("先にデータ収集を完了してください。")
        return

    print("データベースファイル確認: OK")
    print()

    # メニュー表示
    while True:
        print_banner("メニュー")
        print("1. データ品質レポート生成")
        print("2. EDAダッシュボード起動")
        print("3. ベースラインモデル学習")
        print("4. 全自動分析（1→3を順次実行）")
        print("5. 進捗モニター")
        print("6. 新旧データベース比較")
        print("0. 終了")
        print()

        choice = input("選択してください (0-6): ").strip()

        if choice == '1':
            print_banner("データ品質レポート")
            success = run_script('data_quality_report.py', 'データ品質レポート生成')
            if success:
                input("\nEnterキーを押して続行...")

        elif choice == '2':
            print_banner("EDAダッシュボード")
            launch_dashboard()

        elif choice == '3':
            print_banner("ベースラインモデル学習")
            success = run_script('baseline_model.py', 'ベースラインモデル学習')
            if success:
                input("\nEnterキーを押して続行...")

        elif choice == '4':
            print_banner("全自動分析開始")
            print("以下を順次実行します:")
            print("  1. データ品質レポート")
            print("  2. ベースラインモデル学習")
            print()
            confirm = input("実行しますか？ (y/n): ").strip().lower()

            if confirm == 'y':
                # ステップ1: データ品質レポート
                print_banner("ステップ1/2: データ品質レポート")
                success1 = run_script('data_quality_report.py', 'データ品質レポート')

                if success1:
                    # ステップ2: ベースラインモデル
                    print_banner("ステップ2/2: ベースラインモデル学習")
                    success2 = run_script('baseline_model.py', 'ベースラインモデル')

                    if success2:
                        print_banner("全自動分析完了")
                        print("すべての分析が正常に完了しました。")
                        print()
                        print("次のステップ:")
                        print("  - EDAダッシュボード (オプション2) でデータを探索")
                        print("  - ベースラインモデルの結果を確認")
                        print("  - 特徴量エンジニアリングを改善")
                        print()
                    else:
                        print("ベースラインモデル学習でエラーが発生しました。")
                else:
                    print("データ品質レポートでエラーが発生しました。")

                input("\nEnterキーを押して続行...")
            else:
                print("キャンセルしました。")

        elif choice == '5':
            print_banner("進捗モニター")
            success = run_script('monitor_progress.py', '進捗モニター')
            if success:
                input("\nEnterキーを押して続行...")

        elif choice == '6':
            print_banner("新旧データベース比較")
            if os.path.exists('netkeiba_data_OLD_BROKEN_20251217.csv'):
                success = run_script('compare_old_new_db.py', '新旧データベース比較')
                if success:
                    input("\nEnterキーを押して続行...")
            else:
                print("旧データベースファイルが見つかりません。")
                input("\nEnterキーを押して続行...")

        elif choice == '0':
            print_banner("終了")
            print("分析スイートを終了します。")
            break

        else:
            print()
            print("無効な選択です。0-6の数字を入力してください。")
            print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("="*80)
        print(" ユーザーによって中断されました")
        print("="*80)
    except Exception as e:
        print()
        print("="*80)
        print(f" エラーが発生しました: {e}")
        print("="*80)
