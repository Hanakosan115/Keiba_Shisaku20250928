# -*- coding: utf-8 -*-
"""
test_boundary.py — 境界ボタン選択のテスト（投稿直前で停止）

使い方:
  py note_publisher/test_boundary.py 202606020311
"""
import sys, os, asyncio, tkinter as tk
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from datetime import date
from note_publisher.format_article   import format_article
from note_publisher.post_to_note     import (
    _login, _goto_editor, _paste_text, _upload_header_image,
    HEADER_IMAGE_PATH, NOTE_EMAIL, NOTE_PASSWORD,
)
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

RACE_ID    = sys.argv[1] if len(sys.argv) > 1 else '202606020311'
TODAY_ISO  = f'{RACE_ID[:4]}-{RACE_ID[4:6]}-{RACE_ID[6:8]}'
BTN_LABEL  = 'ラインをこの場所に変更'
SEP_LABEL  = '全印付き馬'


def build_and_predict(race_id, today_iso):
    from keiba_prediction_gui_v3 import KeibaGUIv3
    root = tk.Tk()
    root.withdraw()
    gui  = KeibaGUIv3(root)

    scraped, r_info = gui.scrape_shutuba(race_id)
    if scraped:
        horses, race_info = scraped, (r_info or {})
    else:
        horses, race_info = gui.get_race_from_database(race_id)

    if not horses:
        print('[ERROR] データなし')
        return None, None

    has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)
    if not has_odds:
        db_odds = gui._get_odds_from_snapshot_db(race_id)
        if db_odds:
            for h in horses:
                uma = str(h.get('馬番', ''))
                if uma in db_odds:
                    h['単勝オッズ'] = db_odds[uma]
            has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

    df_pred = gui.predict_core(race_id, horses, race_info, has_odds,
                               current_date=today_iso)
    if not race_info.get('date'):
        race_info['date'] = today_iso
    return df_pred, race_info


async def main():
    print(f'=== 境界ボタンテスト  race_id={RACE_ID} ===')

    # 予測 & 記事生成
    df_pred, race_info = build_and_predict(RACE_ID, TODAY_ISO)
    if df_pred is None:
        return
    article = format_article(RACE_ID, df_pred, race_info)
    if not article:
        print('[ERROR] 記事生成失敗')
        return
    print(f'タイトル: {article["title"]}')

    # ブラウザ起動
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        ctx = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ja-JP',
            permissions=['clipboard-read', 'clipboard-write'],
        )
        page = await ctx.new_page()

        await _login(page)
        await _goto_editor(page)
        await _upload_header_image(page, HEADER_IMAGE_PATH)

        # タイトル・本文入力
        await page.fill('textarea[placeholder="記事タイトル"]', article['title'])
        await page.click('.ProseMirror')
        await page.wait_for_timeout(400)
        await _paste_text(page, article['free_body'])
        for _ in range(2):
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(80)
        await _paste_text(page, article['paid_body'])

        # 公開設定パネルを開く
        await page.locator('button:has-text("公開に進む")').first.click(timeout=10_000)
        await page.wait_for_timeout(2000)

        # 有料ラジオ選択
        try:
            await page.locator('label[for="paid"]').click(timeout=5_000)
            await page.wait_for_timeout(1500)
        except PWTimeout:
            print('  有料ラジオ未検出')

        # 価格入力
        try:
            price_inp = page.locator('input#price').first
            await price_inp.wait_for(state='visible', timeout=5_000)
            await price_inp.fill(str(article.get('price', 100)))
            print(f'  価格: {article.get("price", 100)}円')
        except PWTimeout:
            print('  価格フィールド未検出')

        await page.wait_for_timeout(1000)

        # 有料エリア設定を開く
        area_btn = page.locator('button:has-text("有料エリア設定")')
        if await area_btn.count() == 0:
            print('  「有料エリア設定」ボタンなし → スキップ')
        else:
            await area_btn.click(timeout=5_000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'test_boundary_open_{RACE_ID}.png')
            print(f'  有料エリア設定を開いた → test_boundary_open_{RACE_ID}.png')

            # スクロール
            await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(800)

            # ボタン検索（フレームまたぎ）
            btn_ctx   = None
            btn_count = await page.get_by_text(BTN_LABEL, exact=False).count()
            print(f'  ラインボタン数（メインフレーム）: {btn_count}')
            if btn_count > 0:
                btn_ctx = page
            else:
                for frame in page.frames:
                    try:
                        fc = await frame.get_by_text(BTN_LABEL, exact=False).count()
                        if fc > 0:
                            btn_ctx   = frame
                            btn_count = fc
                            print(f'  ラインボタンをフレーム内で発見: {fc}個 ({frame.url[:60]})')
                            break
                    except Exception:
                        continue

            if btn_ctx is None:
                print('  ボタンが見つかりません')
            else:
                # セパレータY座標
                sep_abs_y = None
                try:
                    sep_loc = btn_ctx.get_by_text(SEP_LABEL, exact=False).first
                    if await sep_loc.count() > 0:
                        sep_abs_y = await sep_loc.evaluate(
                            'el => el.getBoundingClientRect().top + window.scrollY'
                        )
                        print(f'  セパレータ absY={sep_abs_y:.0f}')
                except Exception as e:
                    print(f'  セパレータ取得失敗: {e}')

                # 各ボタンのY座標
                target_idx = btn_count - 1
                for i in range(btn_count):
                    try:
                        btn = btn_ctx.get_by_text(BTN_LABEL, exact=False).nth(i)
                        by  = await btn.evaluate(
                            'el => el.getBoundingClientRect().top + window.scrollY'
                        )
                        mark = ' ← TARGET' if (sep_abs_y and by > sep_abs_y) else ''
                        print(f'  ボタン[{i}] absY={by:.0f}{mark}')
                    except Exception as e:
                        print(f'  ボタン[{i}] 取得失敗: {e}')

                if sep_abs_y is not None:
                    min_y = float('inf')
                    for i in range(btn_count):
                        try:
                            btn = btn_ctx.get_by_text(BTN_LABEL, exact=False).nth(i)
                            by  = await btn.evaluate(
                                'el => el.getBoundingClientRect().top + window.scrollY'
                            )
                            if by > sep_abs_y and by < min_y:
                                min_y      = by
                                target_idx = i
                        except Exception:
                            continue

                print(f'\n  ★ターゲット決定: ボタン[{target_idx}]（全{btn_count}個）')

                # クリック
                target_btn = btn_ctx.get_by_text(BTN_LABEL, exact=False).nth(target_idx)
                try:
                    await target_btn.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(500)
                    await target_btn.click(timeout=5_000)
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=f'test_boundary_after_{RACE_ID}.png')
                    print(f'  クリック完了 → test_boundary_after_{RACE_ID}.png')
                except Exception as e:
                    print(f'  クリック失敗: {e}')

        print('\n=== 投稿直前で停止 ===')
        print('ブラウザを手動で閉じてください（または 60秒で自動終了）')
        await page.wait_for_timeout(60_000)
        await browser.close()


asyncio.run(main())
