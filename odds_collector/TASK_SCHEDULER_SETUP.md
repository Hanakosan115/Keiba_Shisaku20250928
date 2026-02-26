# Windowsタスクスケジューラ設定ガイド

**目的**: `schedule_fetch.py`（朝7:00）と `odds_snapshot.py`（レース前）を
土日に自動実行する。

---

## 設定手順（GUIで操作）

### 手順1: タスクスケジューラを開く

```
Win + R → taskschd.msc → Enter
```

または「スタート」→「タスクスケジューラ」で検索。

---

### 手順2: タスク1「競馬スケジュール取得」を作成

**右クリック「タスクスケジューラ ライブラリ」→「タスクの作成」**

#### 全般タブ
- 名前: `keiba_schedule_fetch`
- 説明: `競馬レーススケジュール取得（毎週土日7:00）`
- セキュリティオプション: 「ユーザーがログオンしているときのみ実行する」

#### トリガータブ → 「新規」
- 開始: 毎週
- 曜日: ✅ 土曜日  ✅ 日曜日
- 時刻: 07:00:00
- 有効: ✅

#### 操作タブ → 「新規」
- 操作: プログラムの開始
- プログラム: `py`
- 引数の追加:
  ```
  C:/Users/bu158/Keiba_Shisaku20250928/odds_collector/schedule_fetch.py
  ```
- 開始（作業フォルダ）:
  ```
  C:\Users\bu158\Keiba_Shisaku20250928
  ```

#### 条件タブ
- 「コンピューターをAC電源で使用している場合のみタスクを開始する」: ✅（任意）

→ **OK** でタスクを保存。

---

### 手順3: タスク2「競馬オッズ取得（午前）」を作成

同様に「タスクの作成」:

#### 全般タブ
- 名前: `keiba_odds_morning`
- 説明: `午前レース オッズ取得（30分前: 9:00頃）`

#### トリガータブ
- 毎週 土・日曜日  **09:00**

#### 操作タブ
- プログラム: `py`
- 引数:
  ```
  C:/Users/bu158/Keiba_Shisaku20250928/odds_collector/odds_snapshot.py --timing 30min_before
  ```

---

### 手順4: タスク3「競馬オッズ取得（午後）」を作成

- 名前: `keiba_odds_afternoon`
- トリガー: 毎週 土・日曜日 **14:30**
- 引数: `odds_snapshot.py --timing 30min_before`

> **注意**: 発走時刻は各レース異なるため、30分前に一括で取得して記録する。
> 5分前オッズは手動で補完すること。

---

## コマンドラインで設定する場合（管理者PowerShell）

```powershell
# タスク1: スケジュール取得
$action = New-ScheduledTaskAction `
    -Execute "py" `
    -Argument "C:/Users/bu158/Keiba_Shisaku20250928/odds_collector/schedule_fetch.py" `
    -WorkingDirectory "C:\Users\bu158\Keiba_Shisaku20250928"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday,Sunday -At 07:00

Register-ScheduledTask `
    -TaskName "keiba_schedule_fetch" `
    -Action $action `
    -Trigger $trigger `
    -Description "競馬レーススケジュール取得（毎週土日7:00）"
```

---

## 動作確認

設定後、「右クリック → 実行」でテスト実行できる。

```bash
# 手動でも確認可能
py odds_collector/schedule_fetch.py
py odds_collector/odds_snapshot.py --timing 30min_before
```

ログは標準出力に表示される。必要に応じてリダイレクトで保存:

```bash
py odds_collector/schedule_fetch.py >> odds_collector/schedule_fetch.log 2>&1
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| タスクが起動しない | PC がスリープ中 | 「スリープ解除してタスクを実行」を有効に |
| `py` が認識されない | PATH未設定 | `py` を `python` に変更、またはフルパス指定 |
| ネットワークエラー | Wi-Fi未接続 | 「ネットワーク接続が利用可能な場合のみ」条件を追加 |
| DBが壊れた | 同時書き込み | タスクの実行間隔を15分以上あける |
