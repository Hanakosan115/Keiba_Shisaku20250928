"""
モデルバージョン切り替えスクリプト

使い方:
    py restore_model.py                    # 現在のバージョンを確認
    py restore_model.py phase14_baseline   # Phase 14 ベースラインに戻す
    py restore_model.py phase_r1           # Phase R1 モデルに切り替え
    py restore_model.py --list             # 利用可能なバージョン一覧
"""

import sys
import shutil
import os
from pathlib import Path

ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models"

# GUI が読み込むモデルファイルのパス（ルートに置く）
TARGETS = {
    "model_win.txt":   ROOT / "phase14_model_win.txt",
    "model_place.txt": ROOT / "phase14_model_place.txt",
    "feature_list.pkl":ROOT / "phase14_feature_list.pkl",
}

VERSION_FILE = ROOT / ".model_version"


def get_current_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "phase14_baseline (default)"


def list_versions():
    versions = [d.name for d in MODELS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
    return sorted(versions)


def restore(version: str):
    src_dir = MODELS_DIR / version
    if not src_dir.exists():
        print(f"[ERROR] バージョン '{version}' が見つかりません。")
        print(f"利用可能: {list_versions()}")
        sys.exit(1)

    print(f"=== {version} に切り替えます ===")
    for fname, dst in TARGETS.items():
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  {fname} → {dst.name} ✓")
        else:
            print(f"  {fname} → 見つかりません（スキップ）")

    VERSION_FILE.write_text(version)
    print(f"\n現在のバージョン: {version}")
    print("GUI を再起動してください。")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "--list":
        print(f"現在のバージョン : {get_current_version()}")
        print(f"利用可能なバージョン:")
        for v in list_versions():
            marker = " ← 現在" if v == get_current_version() else ""
            print(f"  {v}{marker}")

    else:
        restore(args[0])
