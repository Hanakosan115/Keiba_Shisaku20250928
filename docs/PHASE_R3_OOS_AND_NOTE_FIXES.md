# 作業レポート：2025 OOS バックテスト & note.com 投稿システム修正

> 作成日: 2026-03-08

---

## 1. 実施内容

### 1-1. note.com 自動投稿システム修正（`note_publisher/`）

#### ✅ 有料エリア境界ボタン選択の修正（`post_to_note.py`）

**問題**: 「ラインをこの場所に変更」ボタンが常に最上部のものを選択してしまい、記事全体が有料になっていた。

**原因の変遷**:
- 旧実装: JS `evaluate()` + `compareDocumentPosition` → `rankEl` がコンテナdivにマッチして比較が失敗
- 中間実装: JS `evaluate()` + `absTop()` → offsetParentチェーンが想定外の値を返していた可能性

**最終解決策**:
- JS `evaluate()` を廃止し、Playwright ネイティブの `get_by_text()` に統一
- `page.frames` を全走査してiframe内のボタンにも対応（フレームまたぎ検索）
- アンカーを「【予測ランキング】の直前」から「**── 以下、全印付き馬を掲載 ──** の直後の最初のボタン」に変更
- `getBoundingClientRect().top + window.scrollY` で絶対Y座標を比較

**デバッグ出力**（実行時ログ）:
```
ラインボタン数（メインフレーム）: 2
セパレータ absY=490
ボタン[0] absY=707   ← セパレータ直後 → 正しいターゲット
ボタン[1] absY=1143
★ターゲット決定: ボタン[0]（全2個）
クリック完了
```

**動作確認**: `test_boundary_after_202606020311.png` でスクリーンショット確認済み。
- 無料エリア: レース情報 + マスクプレビュー（??番）+ 全印付き馬セパレータ
- 有料エリア: 【予測ランキング】以降（実際の馬名・馬番）

---

#### ✅ 記事フォーマットへの発走時間追加（`format_article.py`, `run_auto_post.py`）

- タイトル例: `【6月2日（火） 中山 11R 14:05発走｜フローラS】競馬予想 芝1800m`
- 本文ヘッダー例: `■ 6月2日（火）　中山競馬場　11R　14:05発走`
- `run_auto_post.py` で `race_schedule` テーブルの `start_time` を `race_info` に注入するよう修正

---

#### ✅ 記事ランキング表示の改善（`format_article.py`）

- `★条件A/B` ラベルを削除（読者には不要）
- 印の順番を明示的にソート: ◎ > ○ > ▲ > △ > ✕/☆/注
- 無料プレビュー部分も同様の順序で表示

---

#### ❌ ヘッダー画像アップロード（未解決）

- `_upload_header_image()` でセレクタ・座標クリック・file input 直接セットの3段階を試みるが全て失敗
- note.com エディタのヘッダー画像エリアの正確なセレクタが不明
- **現状**: スキップして投稿は継続する（記事内容には影響なし）
- **調査方法候補**: `note_publisher/inspect_note.py` を改造してエディタ上部のDOM構造を調査

---

#### ✅ テスト用スクリプト作成（`note_publisher/test_boundary.py`）

- 投稿直前まで自動で進んで停止するデバッグスクリプト
- `py note_publisher/test_boundary.py <race_id>` で実行
- スクリーンショット: `test_boundary_open_*.png` / `test_boundary_after_*.png`

---

### 1-2. 2025 OOS バックテスト（Phase R2-Optuna）

#### ✅ R2-Optuna 2025 OOS バックテスト完了

**結果**:

| 指標 | 2024 OOS | **2025 OOS** | 変化 |
|------|---------|-------------|------|
| Rule4件数 | 5,730件 | 5,372件 | ▼358件 |
| 的中率 | 17.7% | **19.9%** | +2.2pt |
| ROI | 148.0% | **174.7%** | **+26.7pt** |
| 純損益 | +274,879円 | **+401,142円** | **+126,263円** |
| 条件A ROI | 126.7% | 142.4% | +15.7pt |
| 条件B ROI | 163.2% | **196.9%** | +33.7pt |
| 50x超 ROI | 289.2% | **334.2%** | +45.0pt |

**月次**: 全10ヶ月プラス（最低: 2025-04 ROI 148.7%）

**競馬場別**: 全10競馬場プラス（最高: 函館 ROI 292.1%、小倉 246.3%）

**評価**: 2年連続 OOS でプラス、かつ 2025 は大幅改善。モデルの汎化性能は高い。

---

#### ❌ R2-Optuna vs R3 比較（失敗）

**原因**: `models/phase_r3/` のモデルファイル（model_win.txt / model_place.txt / feature_list.pkl）が `models/phase_r2_optuna/` と完全同一（MD5ハッシュ一致）。

**判明した事実**:
- `models/phase_r3/metadata.json` は R3 パラメータを正しく記録（CV AUC 0.8289、Val AUC 0.7660、LR 0.0102、num_leaves 48）
- しかしモデルファイル本体は R2-Optuna のまま（保存処理のバグ）
- R3 の実モデルは消失

**対応**: R3 の再訓練は省略（2024 OOS で ROI 138.1% と R2-Optuna の 148.0% を下回ることが既知のため）

---

## 2. 気づき・課題

### note.com 自動投稿

| 課題 | 詳細 |
|------|------|
| JS evaluate() はメインフレームのみ | iframeがあると検索できない。Playwright locator を使うべき |
| compareDocumentPosition の罠 | コンテナdivがanchorより先にマッチすると全ての子ノードが「含まれる」と判定される |
| `getBoundingClientRect()` は要スクロール | off-screen要素は値が不安定。`scrollIntoView` 後か、`top + window.scrollY` で絶対座標化 |
| ヘッダー画像エリアは要DOM調査 | note.com のReactコンポーネントはハッシュ化クラス名のため予測困難。`inspect_note.py` で実DOM確認が必要 |
| `--test` モードは投稿済みにならない | 同レースを繰り返し投稿してしまう。テスト時は `test_boundary.py` を使う |

### モデル管理

| 課題 | 詳細 |
|------|------|
| Phase R3 モデル消失 | 訓練後の保存処理でモデルファイルが上書きされなかった。保存時のパス確認が重要 |
| AUC改善 ≠ ROI改善 | R3: Val AUC +0.0004 でも ROI ▼9.9pt。評価指標としてはROI/実損益の方が重要 |
| `models/phase_r3/metadata.json` の phase フィールドが "R2_Optuna" | 保存スクリプトで phase 名の更新を忘れた |

---

## 3. 現在のモデルステータス

| フェーズ | ファイル | Val AUC | ROI(2024) | ROI(2025) | 状態 |
|---------|---------|---------|----------|----------|------|
| R2-Optuna | `phase14_model_*.txt` | 0.7656 | 148.0% | **174.7%** | ✅ 有効（現行） |
| R3 | `models/phase_r3/` | ※同上 | ※同上 | ※同上 | ❌ 消失（R2-Optunaと同一） |

---

## 4. 次のアクション候補

| 優先度 | タスク | 概要 |
|--------|--------|------|
| ★★ | **Phase R4: レース内相対特徴量** | 同レース内での馬間比較（オッズ相対値、予測確率の相対ランクなど）。ROIに直接効く可能性 |
| ★★ | note.com ヘッダー画像調査 | `inspect_note.py` でエディタ上部の DOM 構造を確認、正確なセレクタを特定 |
| ★ | Phase R3 再訓練（任意） | `train_phase12.py` 等で R3 特徴量で再訓練 → `models/phase_r3/` に正しく保存 |
| ★ | ペーパートレード月次レビュー | `py paper_trade_review.py` で GO/NO-GO 判定 |

---

## 5. ファイル変更サマリー

| ファイル | 変更内容 |
|---------|---------|
| `note_publisher/post_to_note.py` | 境界ボタン選択ロジック全面刷新（Playwright locator + フレーム検索）、ヘッダー画像アップロード強化 |
| `note_publisher/format_article.py` | 発走時間追加（タイトル・本文ヘッダー）、★条件A/B削除、印順ソート |
| `note_publisher/run_auto_post.py` | `start_time` を `race_info` に注入 |
| `note_publisher/test_boundary.py` | 新規作成（境界ボタンデバッグ用テストスクリプト） |
| `CLAUDE.md` | 2025 OOS 結果追記、次のアクション更新 |

---

_最終更新: 2026-03-08_
