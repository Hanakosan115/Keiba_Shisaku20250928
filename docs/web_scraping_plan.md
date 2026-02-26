# Webスクレイピング追加データ取得計画

## 目的
現在のCSVデータに無い、リアルタイムデータや詳細情報を取得して予測精度を向上

## 取得対象データと実装優先度

### 【優先度: 高】即効性のあるデータ

#### 1. リアルタイムオッズ（前日～当日）
**取得元**: netkeiba.com 出馬表ページ
**URL例**: `https://race.netkeiba.com/race/shutuba.html?race_id=202406010101`

**取得項目**:
- 単勝オッズ（リアルタイム更新）
- 複勝オッズ
- オッズ変動（前日→当日の変化）

**活用方法**:
- 直前のオッズ急降下 = インサイダー情報の可能性
- 直前のオッズ急上昇 = ネガティブ情報（馬体不安など）
- 期待値計算に使用

**実装難易度**: ★☆☆☆☆（簡単）

#### 2. 調教タイム
**取得元**: netkeiba.com 調教情報ページ
**URL例**: `https://race.netkeiba.com/race/oikiri.html?race_id=202406010101`

**取得項目**:
- 最終追い切りタイム
- 調教評価（A, B, C）
- 調教内容（強め、馬なり等）

**活用方法**:
- 仕上がり具合の判定
- 調教タイムが速い = 好調
- 「強めでタイム平凡」= 余力あり

**実装難易度**: ★★☆☆☆（普通）

#### 3. 馬場指数（馬場の硬さ）
**取得元**: JRA公式サイト または 専門サイト
**URL例**: `https://www.jra.go.jp/keiba/baba/`

**取得項目**:
- 馬場状態（良/稍重/重/不良）※既にあり
- 馬場指数（数値化した硬さ）
- 開催週（1週目/2週目/3週目）

**活用方法**:
- 開幕週 = 硬い → 逃げ・先行有利
- 後半週 = 荒れてる → 差し・追込有利
- 馬場指数で脚質バイアスを数値化

**実装難易度**: ★★★☆☆（中級）

### 【優先度: 中】精度向上データ

#### 4. パドック評価
**取得元**: netkeiba.com パドック映像ページ
**URL例**: 動画ページまたは専門家コメント

**取得項目**:
- 馬体評価（専門家の点数）
- 気配（イレ込み、リラックス等）
- 発汗状況

**活用方法**:
- 馬体が良い = プラス評価
- イレ込んでる = 力を出せない可能性
- 発汗多い = 体調不安

**実装難易度**: ★★★★☆（難しい・画像解析必要）

#### 5. 血統詳細データ
**取得元**: netkeiba.com 血統表ページ
**URL例**: `https://db.netkeiba.com/horse/ped/[horse_id]/`

**取得項目**:
- 母父（既にあり）
- 母母父、曾祖父
- インブリード情報
- 距離別・芝ダート別の血統適性指数

**活用方法**:
- ディープインパクト産駒 = 芝・中距離◎
- キングカメハメハ産駒 = ダート◎
- 血統から距離適性を推定

**実装難易度**: ★★☆☆☆（普通）

#### 6. ラップタイム
**取得元**: 専門サイト（keiba.go.jp、netkeiba有料会員）
**URL例**: 有料データ

**取得項目**:
- 200m毎のラップタイム
- 前半3F・後半3Fのタイム
- ペースの緩急度合い

**活用方法**:
- ハイペース/スローペースの定量判定
- ペースが合う馬を抽出
- 展開予想の精度向上

**実装難易度**: ★★★★☆（有料データ・解析必要）

### 【優先度: 低】長期的な改善データ

#### 7. 騎手コメント
**取得元**: スポーツ新聞サイト、netkeiba
**URL例**: レース後のインタビュー記事

**取得項目**:
- 前走の反省コメント
- 今回の作戦・狙い

**活用方法**:
- 自然言語処理でポジティブ/ネガティブ判定
- 「今回は展開が向く」= プラス材料

**実装難易度**: ★★★★★（自然言語処理必要）

#### 8. 厩舎情報
**取得元**: 厩舎リポート、netkeiba

**取得項目**:
- 厩舎コメント（調子、狙いなど）
- 厩舎の最近の成績

**活用方法**:
- 好調厩舎の馬を重視
- コメントから本気度を判定

**実装難易度**: ★★★★☆（難しい）

## 実装ロードマップ

### Phase 1: 基本スクレイピング（1-2週間）
1. ✅ netkeiba.com の出馬表ページから基本情報取得
2. ⏳ リアルタイムオッズ取得
3. ⏳ 調教タイム取得
4. ⏳ データベースに保存

### Phase 2: 高度なデータ取得（2-4週間）
1. ⏳ 馬場指数の取得・計算
2. ⏳ 血統詳細データ取得
3. ⏳ ラップタイム取得（可能なら）

### Phase 3: AI解析（1-2ヶ月）
1. ⏳ パドック映像解析（画像認識）
2. ⏳ 騎手コメント解析（NLP）

## 技術スタック

### 必要なライブラリ
```python
# Webスクレイピング
import requests
from bs4 import BeautifulSoup
import selenium  # 動的ページ用

# データ処理
import pandas as pd
import numpy as np

# データベース
import sqlite3  # またはMySQL

# 画像解析（将来）
import cv2
from PIL import Image
import torch  # ディープラーニング

# 自然言語処理（将来）
from transformers import BertModel
```

### 注意事項
1. **利用規約遵守**: スクレイピングは各サイトの規約を確認
2. **アクセス頻度**: 過度なリクエストは避ける（1秒に1リクエスト程度）
3. **User-Agent**: 適切なUser-Agentを設定
4. **robots.txt確認**: 許可されているか確認

## サンプルコード: リアルタイムオッズ取得

```python
import requests
from bs4 import BeautifulSoup
import time

def get_realtime_odds(race_id):
    """
    netkeibaからリアルタイムオッズを取得
    """
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'EUC-JP'  # netkeibaの文字コード
        soup = BeautifulSoup(response.text, 'html.parser')

        # オッズテーブルを解析
        odds_table = soup.find('table', class_='Shutuba_Table')

        odds_data = []
        for row in odds_table.find_all('tr')[1:]:  # ヘッダーをスキップ
            cols = row.find_all('td')

            umaban = cols[0].text.strip()
            horse_name = cols[3].text.strip()
            odds = cols[12].text.strip()  # オッズ列
            ninki = cols[13].text.strip()  # 人気列

            odds_data.append({
                'umaban': umaban,
                'horse_name': horse_name,
                'odds': float(odds) if odds != '---' else None,
                'ninki': int(ninki) if ninki.isdigit() else None
            })

        return odds_data

    except Exception as e:
        print(f"Error scraping {race_id}: {e}")
        return None

    finally:
        time.sleep(1)  # 1秒待機

# 使用例
race_id = "202406010101"
odds = get_realtime_odds(race_id)
for horse in odds:
    print(f"{horse['umaban']}番 {horse['horse_name']}: {horse['odds']}倍 ({horse['ninki']}人気)")
```

## 期待される効果

### オッズ取得による改善
- **予想精度**: +3-5%（直前情報の活用）
- **回収率**: +10-15%（期待値の高い馬を識別）

### 調教タイム活用
- **新馬戦の精度**: +10-20%（過去データが無い馬の評価が可能に）
- **復帰戦の精度**: +5-10%（休養明けの仕上がり判定）

### 馬場指数活用
- **展開予想精度**: +5-10%（脚質バイアスの定量化）
- **3連系的中率**: +2-3%（展開が読めるようになる）

## 次のステップ
1. まずは次世代モデルのバックテスト結果を確認
2. 結果が良ければ、Phase 1のスクレイピング実装を開始
3. 段階的にデータを追加して精度向上を図る
