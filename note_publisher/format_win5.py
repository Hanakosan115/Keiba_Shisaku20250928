# -*- coding: utf-8 -*-
"""
format_win5.py — GUI の Win5 出力 → note.com 記事テキスト生成

入力データ（GUIの predict_win5() と同形式）:
  leg_results : list[dict] × 5
      {'race_id': str, 'df_pred': pd.DataFrame, 'race_info': dict}
      df_pred 列: 馬番 / 枠番 / 馬名 / 騎手 / オッズ / 勝率予測 / 複勝予測 / 期待値
      ※ 勝率予測の降順でソート済み

  strategies : dict  (_calculate_win5_strategy() の出力)
      {
        'probas': [float × 5],
        'dynamic':  {'picks': [int × 5], 'total': int, 'cost': int},
        'fixed_3':  {'picks': [int × 5], 'total': int, 'cost': int},
        'fixed_5':  {'picks': [int × 5], 'total': int, 'cost': int},
        'recommended': 'dynamic' | 'fixed_3' | 'fixed_5',
      }

記事構成:
  [無料] 日付・WIN5対象レース一覧・各レグ推奨頭数（馬名は隠す）
  [有料] 各レグ推奨馬の詳細 / 購入戦略3種 / 投資額目安
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
MARKS  = ['◎', '○', '▲', '△', '☆']

STRATEGY_LABELS = {
    'dynamic': '動的配分（AI推奨）',
    'fixed_3': '固定3段階',
    'fixed_5': '固定5頭',
}


# ── ヘルパー ─────────────────────────────────────────────────────

def _venue_from_race_id(race_id: str) -> str:
    code = str(race_id)[4:6]
    return VENUE_MAP.get(code, f'会場{code}')


def _race_num_from_race_id(race_id: str) -> str:
    try:
        return str(int(str(race_id)[10:12]))
    except Exception:
        return ''


def _clean_race_name(raw: str) -> str:
    if not raw:
        return ''
    s = re.sub(r'^\d+R', '', raw)
    s = re.sub(r'\d+:\d+', '', s)
    s = re.sub(r'[芝ダ障]\d+m\d*頭?', '', s)
    return s.strip()


def _date_label(date_str: str) -> str:
    if not date_str or len(date_str) < 10:
        return date_str or ''
    try:
        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return f'{dt.month}月{dt.day}日（{DOW_JA[dt.weekday()]}）'
    except Exception:
        return date_str[:10]


def _leg_picks(df: pd.DataFrame, n: int) -> list[dict]:
    """
    df_pred（勝率降順ソート済み）から上位 n 頭を返す。
    各要素: {mark, umaban, name, jockey, pred_win, pred_place, odds}
    """
    if df is None or df.empty:
        return []
    d = df.copy()
    d['_win'] = pd.to_numeric(d.get('勝率予測', 0), errors='coerce').fillna(0)
    d['_plc'] = pd.to_numeric(d.get('複勝予測', 0), errors='coerce').fillna(0)
    d['_ods'] = pd.to_numeric(d.get('オッズ',   0), errors='coerce').fillna(0)
    d = d.sort_values('_win', ascending=False).reset_index(drop=True)

    picks = []
    for i in range(min(n, len(d))):
        row = d.iloc[i]
        picks.append({
            'mark':       MARKS[i] if i < len(MARKS) else f'{i+1}位',
            'umaban':     str(row.get('馬番', '')),
            'name':       str(row.get('馬名', '')),
            'jockey':     str(row.get('騎手', '')),
            'pred_win':   float(row['_win']),
            'pred_place': float(row['_plc']),
            'odds':       float(row['_ods']),
        })
    return picks


# ── メイン関数 ───────────────────────────────────────────────────

def format_win5(
    leg_results: list[dict],
    strategies:  dict,
    date_str:    str = '',
    budget:      int = 10000,
) -> dict:
    """
    GUI の Win5 出力から note.com 記事テキストを生成する。

    Parameters
    ----------
    leg_results : list of dict, len=5
        各要素: {'race_id': str, 'df_pred': DataFrame, 'race_info': dict}
    strategies  : dict
        _calculate_win5_strategy() の戻り値
    date_str    : str  'YYYY-MM-DD' または 'YYYYMMDD'
    budget      : int  購入予算（円）

    Returns
    -------
    dict: title, free_body, paid_body, price, race_id='win5_{date}'
    """
    if len(leg_results) != 5:
        return {}

    # ── 日付正規化 ───────────────────────────────────────────────
    if date_str and len(date_str) == 8:
        date_str = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
    date_label = _date_label(date_str)

    # ── 推奨戦略の picks（何頭ずつ選ぶか）を取得 ─────────────────
    rec_key   = strategies.get('recommended', 'dynamic')
    rec_strat = strategies.get(rec_key, {})
    rec_picks = rec_strat.get('picks', [3, 3, 3, 3, 3])  # フォールバック
    probas    = strategies.get('probas', [0.0] * 5)

    # ── レグごとの基本情報と推奨馬を収集 ─────────────────────────
    legs = []
    for i, ld in enumerate(leg_results):
        rid      = ld.get('race_id', '')
        ri       = ld.get('race_info') or {}
        df       = ld.get('df_pred')
        n_pick   = rec_picks[i] if i < len(rec_picks) else 3

        venue      = ri.get('track_name') or _venue_from_race_id(rid)
        race_num   = ri.get('race_num', '') or _race_num_from_race_id(rid)
        race_name  = _clean_race_name(ri.get('race_name', ''))
        distance   = ri.get('distance', '')
        ctype      = ri.get('course_type', '')
        start_time = ri.get('start_time', '')
        dist_label = f'{ctype}{distance}m' if distance else ''
        top1_prob  = probas[i] if i < len(probas) else 0.0

        legs.append({
            'leg_no':     i + 1,
            'race_id':    rid,
            'venue':      venue,
            'race_num':   race_num,
            'race_name':  race_name,
            'dist_label': dist_label,
            'start_time': start_time,
            'top1_prob':  top1_prob,
            'n_pick':     n_pick,
            'picks':      _leg_picks(df, n_pick),
        })

    # ── タイトル ─────────────────────────────────────────────────
    venues_str = '・'.join(sorted({lg['venue'] for lg in legs}))
    title = f'【{date_label} WIN5予想】{venues_str} 推奨馬＆買い目'

    # ── 無料部分 ─────────────────────────────────────────────────
    free_lines = []
    free_lines.append(f'■ {date_label}　WIN5予想')
    free_lines.append('')

    free_lines.append('▼ WIN5対象レース')
    for lg in legs:
        time_part  = f'  {lg["start_time"]}発走' if lg['start_time'] else ''
        rname_part = f'  {lg["race_name"]}' if lg['race_name'] else ''
        free_lines.append(
            f'  第{lg["leg_no"]}レグ: {lg["venue"]}  {lg["race_num"]}R'
            f'{time_part}  {lg["dist_label"]}{rname_part}'
        )

    free_lines.append('')
    free_lines.append('▼ 各レグ推奨頭数（馬名・馬番は有料）')
    for lg in legs:
        free_lines.append(
            f'  第{lg["leg_no"]}レグ {lg["venue"]} {lg["race_num"]}R: {lg["n_pick"]}頭'
        )

    # 推奨購入金額を無料欄に掲載
    free_lines.append('')
    free_lines.append('▼ 推奨購入金額')
    rec_st = strategies.get(rec_key, {})
    picks_str_rec = '×'.join(str(p) for p in rec_st.get('picks', []))
    free_lines.append(
        f'  {picks_str_rec} = {rec_st.get("total", 0)}点  {rec_st.get("cost", 0):,}円'
    )

    free_lines.append('')
    free_lines.append('')
    free_body = '\n'.join(free_lines)

    # ── 有料部分 ─────────────────────────────────────────────────
    paid_lines = []
    paid_lines.append('═' * 44)
    paid_lines.append('  WIN5 推奨馬（各レグ詳細）')
    paid_lines.append('═' * 44)
    paid_lines.append('')

    for lg in legs:
        time_part  = f' {lg["start_time"]}発走' if lg['start_time'] else ''
        rname_part = f'  {lg["race_name"]}' if lg['race_name'] else ''
        paid_lines.append(
            f'■ {lg["venue"]} {lg["race_num"]}R{time_part}'
            f'{rname_part}  {lg["dist_label"]}'
        )
        paid_lines.append(f'  （推奨{lg["n_pick"]}頭）')

        if not lg['picks']:
            paid_lines.append('  ※ データ取得失敗 → このレグは全頭流しを推奨')
        else:
            for pk in lg['picks']:
                paid_lines.append(
                    f'  {pk["umaban"]}番 {pk["name"]}'
                )
        paid_lines.append('')

    paid_body = '\n'.join(paid_lines)

    date_tag = date_str[:10].replace('-', '') if date_str else 'unknown'
    return {
        'title':     title,
        'free_body': free_body,
        'paid_body': paid_body,
        'price':     300,
        'race_id':   f'win5_{date_tag}',
        'sep_label': 'WIN5 推奨馬（各レグ詳細）',
    }
