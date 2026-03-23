# -*- coding: utf-8 -*-
"""note.com 有料設定後の価格入力フィールドを特定する"""
import asyncio, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from playwright.async_api import async_playwright

EMAIL = os.getenv('NOTE_EMAIL')
PASS  = os.getenv('NOTE_PASSWORD')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(locale='ja-JP',
                                            viewport={'width': 1280, 'height': 900})
        page = await context.new_page()

        # ── ログイン ─────────────────────────────────────
        await page.goto('https://note.com/login', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.fill('#email', EMAIL)
        await page.fill('#password', PASS)
        await page.locator('button:has-text("ログイン")').last.click()
        await page.wait_for_timeout(5000)

        # ── エディタ ─────────────────────────────────────
        try:
            await page.goto('https://editor.note.com/new',
                            wait_until='domcontentloaded', timeout=20000)
        except Exception:
            pass
        await page.wait_for_selector('textarea[placeholder="記事タイトル"]', timeout=30000)
        await page.wait_for_timeout(2000)

        # ── タイトル・本文入力 ────────────────────────────
        await page.fill('textarea[placeholder="記事タイトル"]', 'テスト有料記事2026')
        await page.click('.ProseMirror')
        await page.wait_for_timeout(300)
        await page.keyboard.type('テスト本文です。', delay=20)
        await page.wait_for_timeout(500)

        # ── 「公開に進む」クリック ────────────────────────
        await page.locator('button:has-text("公開に進む")').first.click()
        await page.wait_for_timeout(2000)

        # ── 「有料」ラジオをクリック（labelをクリック）────
        print('「有料」ラベルをクリック...')
        await page.locator('label[for="paid"]').click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path='note_paid_selected.png')
        print('スクリーンショット: note_paid_selected.png')

        # ── 価格入力フィールドを調査 ──────────────────────
        print('\n=== 有料選択後のinput要素 ===')
        all_inputs = await page.query_selector_all('input')
        print(f'全input: {len(all_inputs)}個')
        for i, el in enumerate(all_inputs):
            info = await page.evaluate('''el => ({
                type: el.type, name: el.name, id: el.id,
                ph: el.placeholder, val: el.value.substring(0, 20),
                cls: el.className.substring(0, 80)
            })''', el)
            print(f'  [{i}] {info}')

        # JS で価格inputを探す
        price_js = await page.evaluate('''() => {
            const inputs = document.querySelectorAll("input");
            const results = [];
            for (const el of inputs) {
                const ph = el.placeholder || "";
                const nm = el.name || "";
                const id = el.id || "";
                if (ph.includes("価格") || ph.includes("円") || nm.includes("price") ||
                    id.includes("price") || el.type === "number") {
                    results.push({tag: el.tagName, type: el.type, id: id, name: nm,
                                  ph: ph, cls: el.className.substring(0, 80)});
                }
            }
            return results;
        }''')
        print(f'\nJS価格input探索: {price_js}')

        # ボタン一覧（最終確認）
        buttons = await page.query_selector_all('button')
        print(f'\nボタン: {len(buttons)}個')
        for i, el in enumerate(buttons[:5]):
            info = await page.evaluate('''el => ({
                text: el.textContent.trim().substring(0, 50),
                disabled: el.disabled
            })''', el)
            print(f'  [{i}] {info}')

        print('\n=== 30秒後に終了 ===')
        await page.wait_for_timeout(30000)
        await browser.close()

asyncio.run(main())
