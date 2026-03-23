# -*- coding: utf-8 -*-
"""
format_article.py — predict_core() の出力 → note.com 記事テキスト変換

記事構成:
  [無料] レース情報 / 展開予測 / 本命の推奨理由（文章）
  [有料] 推奨買い目 / 全馬予測ランキング
"""
import re
import pandas as pd
from datetime import datetime

# ── 定数 ─────────────────────────────────────────────────────────

VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}

DOW_JA = ['月', '火', '水', '木', '金', '土', '日']

# SHAP特徴量 → 自然な推奨理由文
FEAT_REASON_POS = {
    'avg_last_3f':               '末脚の速さが際立っており、直線での伸びに期待できる',
    'jockey_win_rate':           '鞍上の腕前も確かで、好判断が見込める',
    'jockey_top3_rate':          '鞍上は複勝率も高く、安定した騎乗が期待できる',
    'total_win_rate':            'これまでの通算成績が安定しており、実力は証明済み',
    'distance_similar_win_rate': '同距離での実績があり、コース適性は申し分なし',
    'track_win_rate':            'この馬場状態への適性が高く、コンディション面も問題なさそう',
    'track_top3_rate':           'この馬場では安定して上位に来ており、信頼できる一頭',
    'prev_race_rank':            '前走の内容が良く、上昇ムードに乗っている',
    'days_since_last_race':      '適度な間隔で使われており、状態面に不安はなさそう',
    'trainer_win_rate':          '管理調教師の勝率も高く、仕上がりに信頼が置ける',
    'trainer_top3_rate':         '厩舎の複勝率も高く、堅実なレースが期待できる',
    'avg_first_corner':          '先行できる脚質で、今回の展開が向きそう',
    'avg_passage_position':      '道中のポジション取りが上手く、展開に左右されにくい',
    'avg_position_change':       '後方からの追い込みが得意で、上がり性能の高さが武器',
    'father_win_rate':           '血統的な適性もあり、今回の条件に合っている',
    'father_top3_rate':          '父系の複勝率が高く、堅実な血統背景あり',
    'total_earnings':            'これまでの賞金実績からも、格の違いを見せられる存在',
    'class_change':              '今回はクラス的にも戦いやすい条件で、力を発揮しやすい',
    'current_class':             '現在のクラスでの実績が豊富で、慣れた舞台での戦いになる',
    'grade_race_starts':         '重賞経験も豊富で、場慣れした精神面は強み',
    'avg_diff_seconds':          '平均的なタイム差の面でも他馬をリードしている',
}

FEAT_REASON_NEG = {
    'prev_race_rank':            '前走は着外だが、今回の条件で巻き返しに期待',
    'days_since_last_race':      '休み明けという点は割り引き必要だが、仕上がりには期待できる',
    'class_change':              'クラスが上がる一戦だが、ポテンシャルは十分',
    'avg_last_3f':               '上がりが遅めだが、先行力でカバーできそう',
}


# ── ヘルパー ─────────────────────────────────────────────────────

def _venue_from_race_id(race_id: str) -> str:
    code = str(race_id)[4:6]
    return VENUE_MAP.get(code, f'会場{code}')


def _clean_race_name(raw: str) -> str:
    """'9R唐戸特別14:05芝2000m18頭' → '唐戸特別'"""
    if not raw:
        return ''
    s = re.sub(r'^\d+R', '', raw)          # 先頭の「9R」などを除去
    s = re.sub(r'\d+:\d+', '', s)          # 時刻「14:05」を除去
    s = re.sub(r'[芝ダ障]\d+m\d*頭?', '', s)  # 「芝2000m18頭」などを除去
    return s.strip()


def _date_label(date_str: str) -> str:
    """'2026-03-01' → '3月1日（土）'"""
    if not date_str or len(date_str) < 10:
        return date_str or ''
    try:
        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return f'{dt.month}月{dt.day}日（{DOW_JA[dt.weekday()]}）'
    except Exception:
        return date_str[:10]


def _race_num_label(race_num) -> str:
    try:
        return f'{int(race_num)}R'
    except Exception:
        return f'{race_num}R' if race_num else ''


def _rule4_judge(pred_win: float, odds: float) -> str:
    if pd.isna(odds) or odds <= 0:
        return ''
    if pred_win >= 0.10 and odds >= 10.0:
        return '★条件B'
    if pred_win >= 0.20 and 2.0 <= odds < 10.0:
        return '★条件A'
    return ''


def _pace_prediction(df: pd.DataFrame) -> tuple:
    """
    各馬の shap_top5 からフィールド全体のペース傾向を推定。
    前走での位置取り系特徴量が多くの馬でプラスなら先行型が多い → ハイ傾向
    末脚系特徴量が多くの馬でプラスなら差し型が多い → スロー傾向
    Returns: (ペース名, 説明文)
    """
    front_score = 0
    close_score = 0

    FRONT_FEATS = {'avg_first_corner', 'avg_passage_position', 'frame_number'}
    CLOSE_FEATS = {'avg_last_3f', 'avg_position_change', 'avg_last_corner'}

    for _, row in df.iterrows():
        shap = row.get('shap_top5', []) or []
        for feat, val in shap:
            if val > 0 and feat in FRONT_FEATS:
                front_score += 1
            elif val > 0 and feat in CLOSE_FEATS:
                close_score += 1

    if front_score >= close_score + 3:
        return ('ハイペース想定',
                '前に行きたい先行タイプが揃っており、序盤から速い流れになりそう。'
                '差し・追い込み馬の台頭に注目。')
    elif close_score >= front_score + 3:
        return ('スロー想定',
                '末脚に秀でた追い込みタイプが多く、ペースは落ち着いた展開が予想される。'
                '前に付けられる先行馬が最終コーナーで粘り込む可能性あり。')
    else:
        return ('ミドルペース想定',
                '先行・差し馬がバランスよく揃い、平均的な流れになりそう。'
                '実力通りの決着になりやすい展開。')


def _natural_reason(honmei: pd.Series) -> str:
    """
    本命馬の shap_top5 を自然な文章（AIっぽさなし）に変換。
    最大3文を生成。データがない場合は数値ベースのフォールバック文。
    """
    shap = honmei.get('shap_top5', []) or []
    win_pct = honmei['_win'] * 100
    plc_pct = honmei['_plc'] * 100

    sentences = []
    used = set()

    for feat, val in shap:
        if feat in used:
            continue
        used.add(feat)
        if val > 0 and feat in FEAT_REASON_POS:
            sentences.append(FEAT_REASON_POS[feat])
        elif val < 0 and feat in FEAT_REASON_NEG:
            # マイナス要因は注意書きとして1つだけ
            if len([s for s in sentences if 'だが' in s]) == 0:
                sentences.append(FEAT_REASON_NEG[feat])
        if len(sentences) >= 3:
            break

    if not sentences:
        sentences.append(
            'このメンバー構成の中では勝率・複勝率ともにトップクラスの数字が出ており、'
            '総合力で一枚上手の存在'
        )

    return '。'.join(sentences) + '。'


# ── メイン関数 ───────────────────────────────────────────────────

def format_article(race_id: str, df_pred: pd.DataFrame, race_info: dict) -> dict:
    """
    predict_core() の出力 df_pred から note.com 記事テキストを生成する。

    Returns:
        dict: title, free_body, paid_body, price, race_id
    """
    if df_pred is None or df_pred.empty:
        return {}

    # ── 基本情報 ────────────────────────────────────────────────
    venue     = race_info.get('track_name') or _venue_from_race_id(race_id)
    race_name = _clean_race_name(race_info.get('race_name', ''))
    distance  = race_info.get('distance', '')
    ctype     = race_info.get('course_type', '')
    condition = race_info.get('track_condition', '')
    date_str  = race_info.get('date', '')[:10] if race_info.get('date') else ''

    # race_num が race_info にない場合は race_id[10:12] から抽出
    race_num = race_info.get('race_num', '')
    if not race_num and len(str(race_id)) >= 12:
        race_num = str(int(str(race_id)[10:12]))  # '01' → '1'

    start_time = race_info.get('start_time', '')  # 例: '14:05'

    date_label = _date_label(date_str)
    race_num_label = _race_num_label(race_num)
    dist_label = f'{ctype}{distance}m' if distance else ''

    # ── 予測ランキング（勝率降順） ─────────────────────────────
    df = df_pred.copy()
    df['_win']  = pd.to_numeric(df.get('勝率予測', 0), errors='coerce').fillna(0)
    df['_plc']  = pd.to_numeric(df.get('複勝予測', 0), errors='coerce').fillna(0)
    df['_odds'] = pd.to_numeric(df.get('オッズ',   0), errors='coerce').fillna(0)
    df = df.sort_values('_win', ascending=False).reset_index(drop=True)

    honmei = df.iloc[0]
    honmei_name   = str(honmei.get('馬名', ''))
    honmei_win    = honmei['_win']
    honmei_plc    = honmei['_plc']
    honmei_mark   = str(honmei.get('印', '◎'))
    honmei_jockey = str(honmei.get('騎手', ''))

    # ── タイトル（馬名・馬番は含めない） ──────────────────────
    time_label = f' {start_time}発走' if start_time else ''
    if race_name:
        title = f'【{date_label} {venue} {race_num_label}{time_label}｜{race_name}】競馬予想 {dist_label}'
    else:
        title = f'【{date_label} {venue} {race_num_label}{time_label}】競馬予想 {dist_label}'

    # ── ペース予測 ────────────────────────────────────────────
    pace_name, pace_desc = _pace_prediction(df)

    # ── 本命推奨理由（自然な文章） ─────────────────────────────
    reason = _natural_reason(honmei)

    # ── 無料プレビュー部分 ───────────────────────────────────
    free_lines = []

    # レース情報ヘッダー
    header_line = f'■ {date_label}　{venue}競馬場　{race_num_label}'
    if start_time:
        header_line += f'　{start_time}発走'
    free_lines.append(header_line)
    if race_name:
        free_lines.append(f'　{race_name}　{dist_label}')
    else:
        free_lines.append(f'　{dist_label}')
    if condition:
        free_lines.append(f'　馬場状態: {condition}')
    free_lines.append('')


    # 有料パートのマスクプレビュー
    _MARK_ORDER = {'◎': 0, '○': 1, '▲': 2, '△': 3, '✕': 4, '☆': 4, '注': 4}
    _MARKS = set(_MARK_ORDER.keys())
    _free_marked = df[df['印'].astype(str).isin(_MARKS)].copy()
    _free_marked['_mo'] = _free_marked['印'].astype(str).map(_MARK_ORDER)
    _free_marked = _free_marked.sort_values('_mo').reset_index(drop=True)

    free_lines.append('【有料パートの内容（馬番・馬名は有料）】')
    for prank, (_, row) in enumerate(_free_marked.iterrows(), 1):
        mark = str(row.get('印', ''))
        w = row['_win']
        p = row['_plc']
        free_lines.append(
            f'  {prank}位　{mark} ??番 ??????????　勝率{w*100:.0f}% / 複勝{p*100:.0f}%'
        )
        if prank == 3:
            free_lines.append('  ─── 以下、全印付き馬を掲載 ───')
            break
    # 空行2つで有料エリアの区切り位置を確実に作る
    free_lines.append('')
    free_lines.append('')

    free_body = '\n'.join(free_lines)

    # ── 有料部分 ─────────────────────────────────────────────
    paid_lines = []

    # 印付き馬の予測ランキング（印の強さ順）
    MARK_ORDER = {'◎': 0, '○': 1, '▲': 2, '△': 3, '✕': 4, '☆': 4, '注': 4}
    VALID_MARKS = set(MARK_ORDER.keys())
    marked = df[df['印'].astype(str).isin(VALID_MARKS)].copy()
    marked['_mark_order'] = marked['印'].astype(str).map(MARK_ORDER)
    marked = marked.sort_values('_mark_order').reset_index(drop=True)

    paid_lines.append('【予測ランキング】')
    for rank, (_, row) in enumerate(marked.iterrows(), 1):
        mark = str(row.get('印', ''))
        uma  = str(row.get('馬番', ''))
        name = str(row.get('馬名', ''))
        w    = row['_win']
        p    = row['_plc']
        paid_lines.append(
            f'  {rank}位　{mark} {uma}番 {name}'
            f'　勝率{w*100:.0f}% / 複勝{p*100:.0f}%'
        )

    paid_body = '\n'.join(paid_lines)

    return {
        'title':      title,
        'free_body':  free_body,
        'paid_body':  paid_body,
        'price':      100,
        'race_id':    race_id,
    }
