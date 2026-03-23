# -*- coding: utf-8 -*-
"""
inspect_header.py — note.com エディタのヘッダー画像エリアを調査する

実行:
    py note_publisher/inspect_header.py

やること:
  1. ログイン → エディタ起動
  2. タイトル入力欄の上部DOM要素を全列挙
  3. input[type=file] を全列挙
  4. タイトル上方をクリックしてファイルチューザーが開くか試す
  5. スクリーンショットで視覚確認
"""
import asyncio
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from playwright.async_api import async_playwright

EMAIL = os.getenv('NOTE_EMAIL')
PASS  = os.getenv('NOTE_PASSWORD')


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            locale='ja-JP', viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        # ── ログイン ───────────────────────────────────────
        await page.goto('https://note.com/login', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.fill('#email', EMAIL)
        await page.fill('#password', PASS)
        await page.locator('button:has-text("ログイン")').last.click()
        await page.wait_for_function("() => !window.location.href.includes('/login')", timeout=15000)
        print('ログイン完了')

        # ── エディタ起動 ──────────────────────────────────
        try:
            await page.goto('https://editor.note.com/new',
                            wait_until='domcontentloaded', timeout=20000)
        except Exception:
            pass
        await page.wait_for_selector('textarea[placeholder="記事タイトル"]', timeout=30000)
        await page.wait_for_timeout(3000)

        # ── スクリーンショット（初期状態）─────────────────
        await page.screenshot(path='inspect_header_initial.png', full_page=False)
        print('スクリーンショット保存: inspect_header_initial.png')

        # ── タイトル欄の位置取得 ──────────────────────────
        title_box = await page.locator('textarea[placeholder="記事タイトル"]').bounding_box()
        print(f'\nタイトル欄: {title_box}')

        # ── input[type=file] を全列挙 ─────────────────────
        print('\n=== input[type=file] 一覧 ===')
        file_inputs = await page.query_selector_all('input[type="file"]')
        print(f'  {len(file_inputs)}個')
        for i, el in enumerate(file_inputs):
            info = await page.evaluate('''el => ({
                id: el.id, name: el.name,
                accept: el.accept,
                cls: el.className.substring(0, 100),
                display: window.getComputedStyle(el).display,
                visibility: window.getComputedStyle(el).visibility,
                offsetParent: el.offsetParent ? el.offsetParent.tagName : "none"
            })''', el)
            print(f'  [{i}] {info}')

        # ── タイトル上方の要素を座標で列挙 ───────────────
        if title_box:
            cx = title_box['x'] + title_box['width'] / 2
            top_y = title_box['y']
            print(f'\n=== タイトル上方 (y < {top_y:.0f}) の要素 ===')
            result = await page.evaluate(f'''() => {{
                const elements = document.elementsFromPoint({cx}, {top_y - 60});
                return elements.slice(0, 15).map(el => ({{
                    tag: el.tagName,
                    id: el.id,
                    cls: el.className.toString().substring(0, 100),
                    role: el.getAttribute("role") || "",
                    ariaLabel: el.getAttribute("aria-label") || "",
                    rect: el.getBoundingClientRect()
                }}));
            }}''')
            for r in result:
                print(f"  {r['tag']} id={r['id']!r} cls={r['cls']!r} role={r['role']!r} aria={r['ariaLabel']!r}")

        # ── ヘッダーエリアのクリック試行（ファイルチューザー検出）──
        print('\n=== タイトル上方クリック試行 ===')
        if title_box:
            cx = title_box['x'] + title_box['width'] / 2
            for offset in [60, 100, 140, 180, 220]:
                hy = title_box['y'] - offset
                if hy < 0:
                    continue
                print(f'  クリック試行: y={hy:.0f} (タイトル上 {offset}px)')
                try:
                    async with page.expect_file_chooser(timeout=2000) as fc_info:
                        await page.mouse.click(cx, hy)
                    fc = await fc_info.value
                    print(f'  ★ファイルチューザー検出！ offset={offset}px → クリック位置 y={hy:.0f}')
                    await fc.set_files(
                        os.path.join(os.path.dirname(__file__), 'Noteヘッダー用.png')
                    )
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=f'inspect_header_after_upload.png')
                    print('  アップロード試行完了: inspect_header_after_upload.png')
                    break
                except Exception as e:
                    print(f'  → チューザーなし ({e.__class__.__name__})')

        # ── クリック後のDOM再確認 ─────────────────────────
        print('\n=== クリック後 input[type=file] 再確認 ===')
        file_inputs2 = await page.query_selector_all('input[type="file"]')
        print(f'  {len(file_inputs2)}個')
        for i, el in enumerate(file_inputs2):
            info = await page.evaluate('''el => ({
                id: el.id, name: el.name, accept: el.accept,
                cls: el.className.substring(0, 100)
            })''', el)
            print(f'  [{i}] {info}')

        # ── 全ボタンでヘッダー関連を探す ─────────────────
        print('\n=== ヘッダー関連ボタン/要素 ===')
        result2 = await page.evaluate('''() => {
            const all = document.querySelectorAll("button, [role='button'], label");
            const found = [];
            for (const el of all) {
                const text = el.textContent.trim().substring(0, 50);
                const cls  = el.className.toString().toLowerCase();
                const aria = (el.getAttribute("aria-label") || "").toLowerCase();
                if (cls.includes("header") || cls.includes("eyecatch") ||
                    cls.includes("thumbnail") || cls.includes("cover") ||
                    cls.includes("hero") ||
                    aria.includes("ヘッダー") || aria.includes("サムネ") ||
                    text.includes("ヘッダー") || text.includes("画像")) {
                    found.push({tag: el.tagName, text, cls: el.className.toString().substring(0, 100), aria});
                }
            }
            return found;
        }''')
        if result2:
            for r in result2:
                print(f"  {r['tag']} text={r['text']!r} cls={r['cls']!r} aria={r['aria']!r}")
        else:
            print('  該当なし')

        print('\n=== 60秒後に終了（手動確認してください） ===')
        await page.wait_for_timeout(60000)
        await browser.close()


asyncio.run(main())
