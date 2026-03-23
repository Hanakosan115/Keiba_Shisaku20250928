# -*- coding: utf-8 -*-
"""
post_to_note.py — Playwright で note.com に有料記事を自動投稿する

使い方:
    import asyncio
    from note_publisher.post_to_note import post_article

    asyncio.run(post_article(
        title='【東京1R】AI予測 ...',
        free_body='本命は ...',
        paid_body='推奨買い目 ...',
        price=300,
        headless=True,   # False にするとブラウザが見える（デバッグ用）
    ))

前提:
    - note_publisher/.env に NOTE_EMAIL / NOTE_PASSWORD を設定済み
    - note.com アカウントのメール認証が完了していること
    - 有料販売のために本人情報（氏名・住所）が登録済みであること
"""
import os
import asyncio
from pathlib import Path

# python-dotenv で .env を読み込む
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / '.env'
    if not _env_path.exists():
        _env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(_env_path)
except ImportError:
    pass

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

NOTE_EMAIL      = os.getenv('NOTE_EMAIL', '')
NOTE_PASSWORD   = os.getenv('NOTE_PASSWORD', '')
NOTE_LOGIN_URL  = 'https://note.com/login'
NOTE_EDITOR_URL = 'https://editor.note.com/new'
HEADER_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'Noteヘッダー用.png')


async def _upload_header_image(page, image_path: str):
    """エディタのヘッダー画像をアップロードする。"""
    if not image_path or not os.path.exists(image_path):
        print(f'  [note] ヘッダー画像スキップ（ファイル未存在: {image_path}）')
        return

    # ① aria-label="画像を追加" ボタンをクリック（F12で確認済み）
    #    → クリック後に「画像をアップロード」パネルが展開する2段階構造
    add_img_btn = page.locator('button[aria-label="画像を追加"]').first
    btn_count = await add_img_btn.count()
    print(f'  [note] 「画像を追加」ボタン数: {btn_count}')

    if btn_count > 0:
        try:
            await add_img_btn.click()
            await page.wait_for_timeout(1500)  # パネル展開待ち

            # パネル内ボタンをJS で探す（get_by_text より確実）
            upload_btn_handle = await page.evaluate_handle('''() => {
                for (const btn of document.querySelectorAll("button")) {
                    if (btn.textContent.includes("画像をアップロード")) return btn;
                }
                return null;
            }''')
            panel_found = await page.evaluate('el => el !== null', upload_btn_handle)
            print(f'  [note] パネル内「画像をアップロード」ボタン: {panel_found}')

            if panel_found:
                async with page.expect_file_chooser(timeout=5_000) as fc_info:
                    await upload_btn_handle.as_element().click()
                fc = await fc_info.value
                await fc.set_files(image_path)
                await page.wait_for_timeout(2000)
                print(f'  [note] ヘッダー画像アップロード完了: {os.path.basename(image_path)}')

                # クロップモーダル（保存/キャンセル）が出た場合は「保存」をクリック
                await page.wait_for_timeout(1000)
                crop_btn = await page.evaluate_handle('''() => {
                    // data-testid="cropper" の親からボタンを探す
                    const cropper = document.querySelector('[data-testid="cropper"]');
                    if (cropper) {
                        let el = cropper.parentElement;
                        for (let i = 0; i < 10 && el && el !== document.body; i++) {
                            for (const btn of el.querySelectorAll("button")) {
                                if (btn.textContent.trim() === "保存") return btn;
                            }
                            el = el.parentElement;
                        }
                    }
                    // フォールバック: ページ全体から "保存" ボタンを探す（"下書き保存"は除外）
                    for (const btn of document.querySelectorAll("button")) {
                        if (btn.textContent.trim() === "保存") return btn;
                    }
                    return null;
                }''')
                crop_found = await page.evaluate('el => el !== null', crop_btn)
                print(f'  [note] クロップモーダル「保存」ボタン: {crop_found}')
                if crop_found:
                    await crop_btn.as_element().click()
                    # 画像反映に10〜20秒かかるため待機
                    print('  [note] クロップモーダル保存完了（画像反映待ち30秒）')
                    await page.wait_for_timeout(30000)
                return
            else:
                print('  [note] パネル内ボタンが見つかりません')
        except Exception as e:
            print(f'  [note] ヘッダー画像アップロード失敗: {e}')
    else:
        print('  [note] 「画像を追加」ボタンが見つかりません')

    # ② input[type="file"] に直接セット（フォールバック）
    try:
        file_input = page.locator('input[type="file"]').first
        if await file_input.count() > 0:
            await file_input.set_input_files(image_path)
            await page.wait_for_timeout(2000)
            print(f'  [note] ヘッダー画像アップロード完了（file input直接）')
            return
    except Exception:
        pass

    print('  [note] ヘッダー画像: アップロードエリアが見つかりません（スキップ）')


async def _login(page):
    """note.com にログインする。"""
    await page.goto(NOTE_LOGIN_URL, wait_until='domcontentloaded')
    await page.wait_for_timeout(2000)
    email_sel = 'input[type="email"], #email, input[name="email"]'
    pw_sel    = 'input[type="password"], #password, input[name="password"]'
    await page.locator(email_sel).first.fill(NOTE_EMAIL)
    await page.locator(email_sel).first.dispatch_event('input')
    await page.locator(pw_sel).first.fill(NOTE_PASSWORD)
    await page.locator(pw_sel).first.dispatch_event('input')
    await page.wait_for_timeout(500)
    await page.locator('button:has-text("ログイン")').last.click()
    # /login を含まないURLへのナビゲーション完了を待つ
    # （wait_for_url('note.com/**') は note.com/login 自体にも即マッチするため使わない）
    await page.wait_for_function(
        "() => !window.location.href.includes('/login')",
        timeout=20_000,
    )
    await page.wait_for_timeout(1000)  # Cookie 確定のため少し待つ
    print('  [note] ログイン完了')


async def _goto_editor(page):
    """新規記事エディタへ移動する。editor.note.com は cross-origin のため例外をキャッチ。"""
    try:
        await page.goto(NOTE_EDITOR_URL, wait_until='domcontentloaded', timeout=20_000)
    except Exception:
        pass  # cross-origin リダイレクトによる abort は無視
    # タイトル入力エリアが出るまで待つ
    await page.wait_for_selector('textarea[placeholder="記事タイトル"]', timeout=30_000)
    await page.wait_for_timeout(1500)
    print('  [note] エディタ表示完了')


async def _paste_text(page, text: str):
    """クリップボード経由でテキストをペーストする（ProseMirror対応）。"""
    await page.evaluate('(t) => navigator.clipboard.writeText(t)', text)
    await page.keyboard.press('Control+v')
    await page.wait_for_timeout(300)


async def _insert_paid_separator(page):
    """有料ゾーン区切り線を挿入する。Ctrl+End でカーソルを末尾に移動してから試みる。"""
    # click() はカーソルを先頭へ飛ばす可能性があるため focus() を使用
    await page.locator('.ProseMirror').focus()
    await page.wait_for_timeout(300)
    await page.keyboard.press('Control+End')
    await page.wait_for_timeout(300)
    await page.keyboard.press('Enter')
    await page.wait_for_timeout(200)
    await page.keyboard.type('/', delay=150)
    await page.wait_for_timeout(1200)  # スラッシュメニューの表示を待つ

    # 「有料」でメニューをフィルタリング
    await page.keyboard.type('有料', delay=100)
    await page.wait_for_timeout(1000)

    # 複数セレクタでメニューアイテムを探す
    for sel in [
        'text=有料エリア',
        '[role="option"]:has-text("有料エリア")',
        '[class*="slash"] :text("有料エリア")',
        '[class*="menu"] :text("有料エリア")',
    ]:
        try:
            item = page.locator(sel).first
            if await item.count() > 0:
                await item.click(timeout=3_000)
                print('  [note] 有料ゾーン区切り挿入完了（クリック）')
                return True
        except Exception:
            continue

    # Enterキーで選択試み（メニューが絞り込まれている場合）
    try:
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(600)
        print('  [note] 有料ゾーン区切り挿入完了（Enter）')
        return True
    except Exception:
        pass

    # 失敗: アンドゥ（Enter + '/' + '有' + '料' の分）
    await page.keyboard.press('Escape')
    await page.wait_for_timeout(300)
    for _ in range(5):
        await page.keyboard.press('Control+z')
        await page.wait_for_timeout(100)
    print('  [note] 有料ゾーン区切り挿入失敗（スラッシュコマンド不可）')
    return False


async def _post_one(page, title: str, free_body: str, paid_body: str,
                    price: int, race_id: str,
                    stop_before_post: bool = False,
                    sep_label: str = '全印付き馬') -> bool:
    """ログイン済みの page に1記事を投稿する。stop_before_post=True なら投稿直前で60秒待機。"""
    try:
        # エディタへ移動
        await _goto_editor(page)

        # ヘッダー画像をアップロード
        await _upload_header_image(page, HEADER_IMAGE_PATH)

        # タイトル入力
        await page.fill('textarea[placeholder="記事タイトル"]', title)
        print(f'  [note] タイトル入力: {title[:50]}')

        # 本文エリアをクリックして無料部分を入力
        await page.click('.ProseMirror')
        await page.wait_for_timeout(400)
        await _paste_text(page, free_body)
        print('  [note] 無料部分入力完了')

        # 空行を2回キー入力して境界用のセパレータを作る
        # （クリップボード貼り付けは末尾の空行を削除するため keyboard で補完）
        for _ in range(2):
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(80)
        await _paste_text(page, paid_body)
        print('  [note] 有料部分入力完了')

        # 「公開に進む」ボタンをクリック
        await page.locator('button:has-text("公開に進む")').first.click(timeout=10_000)
        await page.wait_for_timeout(2000)
        print('  [note] 公開設定パネルを開いた')

        # 「有料」ラジオを選択
        try:
            await page.locator('label[for="paid"]').click(timeout=5_000)
            await page.wait_for_timeout(1500)
            print('  [note] 有料ラジオ選択完了')
        except PWTimeout:
            print('  [note] 有料ラジオが見つかりません')

        # 価格を入力
        try:
            price_input = page.locator('input#price').first
            await price_input.wait_for(state='visible', timeout=5_000)
            await price_input.fill(str(price))
            print(f'  [note] 価格設定: {price}円')
        except PWTimeout:
            print('  [note] 価格入力フィールド(#price)が見つかりません')

        await page.wait_for_timeout(1000)

        # 有料エリア設定ボタンを（常に）クリックして境界位置を修正する
        # （掲載記事数が増えた後は必須操作になった）
        area_btn = page.locator('button:has-text("有料エリア設定")')
        if await area_btn.count() > 0:
            await area_btn.click(timeout=5_000)
            await page.wait_for_timeout(2000)
            print('  [note] 有料エリア設定ビューを開いた')

            # 「ラインをこの場所に変更」を【予測ランキング】直前の位置でクリック
            # Playwright get_by_text + フレームまたぎ検索（JS evaluate はメインフレームのみのため）
            await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(800)

            BTN_LABEL = 'ラインをこの場所に変更'
            SEP_LABEL  = sep_label

            # メインフレーム → 子フレームの順に検索
            btn_ctx = None
            btn_count = await page.get_by_text(BTN_LABEL, exact=False).count()
            print(f'  [note] ラインボタン数（メインフレーム）: {btn_count}')
            if btn_count > 0:
                btn_ctx = page
            else:
                for frame in page.frames:
                    try:
                        fc = await frame.get_by_text(BTN_LABEL, exact=False).count()
                        if fc > 0:
                            btn_ctx = frame
                            btn_count = fc
                            print(f'  [note] ラインボタンをフレーム内で発見: {fc}個 ({frame.url[:60]})')
                            break
                    except Exception:
                        continue

            if btn_ctx is None or btn_count == 0:
                print('  [note] 「ラインをこの場所に変更」が見つかりません（境界はそのまま）')
            else:
                # セパレータ「── 以下、全印付き馬を掲載 ──」の絶対Y座標
                sep_abs_y = None
                try:
                    sep_loc = btn_ctx.get_by_text(SEP_LABEL, exact=False).first
                    if await sep_loc.count() > 0:
                        sep_abs_y = await sep_loc.evaluate(
                            'el => el.getBoundingClientRect().top + window.scrollY'
                        )
                        print(f'  [note] セパレータ absY={sep_abs_y:.0f}')
                except Exception as e:
                    print(f'  [note] セパレータ取得失敗: {e}')

                # 各ボタンの絶対Y座標を収集してセパレータ直後の最初のボタンを選択
                target_idx = btn_count - 1  # フォールバック: 最後のボタン
                if sep_abs_y is not None:
                    min_y = float('inf')
                    for i in range(btn_count):
                        try:
                            btn = btn_ctx.get_by_text(BTN_LABEL, exact=False).nth(i)
                            by = await btn.evaluate(
                                'el => el.getBoundingClientRect().top + window.scrollY'
                            )
                            print(f'  [note]   ボタン[{i}] absY={by:.0f}')
                            if by > sep_abs_y and by < min_y:
                                min_y = by
                                target_idx = i
                        except Exception as e:
                            print(f'  [note]   ボタン[{i}] 取得失敗: {e}')

                # クリック実行
                target_btn = btn_ctx.get_by_text(BTN_LABEL, exact=False).nth(target_idx)
                print(f'  [note] ターゲット: ボタン[{target_idx}]（全{btn_count}個）')
                try:
                    await target_btn.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(500)
                    await target_btn.click(timeout=5_000)
                    await page.wait_for_timeout(2000)
                    print(f'  [note] 有料エリア境界をクリック完了（ボタン[{target_idx}]）')
                except Exception as e:
                    print(f'  [note] ボタンクリック失敗: {e}')
            await page.wait_for_timeout(1000)

        if stop_before_post:
            print('\n=== 投稿直前で停止（--preview モード）===')
            print('ブラウザを確認してください（5分後に自動終了）')
            await page.wait_for_timeout(300_000)
            return False

        # 投稿ボタンをクリック（note.com のUI変更に対応して複数テキストを試行）
        submitted = False
        # 「保存する」は下書き保存になるため除外
        submitted = False
        for btn_text in ['投稿する', '公開する', 'Post', 'Publish']:
            try:
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if await btn.count() > 0:
                    await btn.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(500)
                    await btn.click(timeout=5_000)
                    submitted = True
                    print(f'  [note] 投稿ボタンクリック: 「{btn_text}」')
                    break
            except Exception:
                continue

        if not submitted:
            raise Exception('投稿ボタンが見つかりません')

        # 投稿完了の確認:
        #   ① URL が editor.note.com から離脱
        #   ② 「記事が公開されました」ポップアップが出現
        # どちらかが満たされれば成功とみなす
        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('editor.note.com')"
                " || document.body.innerText.includes('\u8a18\u4e8b\u304c\u516c\u958b\u3055\u308c\u307e\u3057\u305f')",
                timeout=10_000,
            )
        except Exception:
            pass  # タイムアウトしても次の判定へ

        body_text = await page.evaluate('() => document.body.innerText')
        if '記事が公開されました' in body_text:
            print(f'  [note] 投稿完了（公開ポップアップ確認）: {page.url}')
            return True

        if 'editor.note.com' not in page.url:
            print(f'  [note] 投稿完了: {page.url}')
            return True

        # 境界エディタ→公開パネルへ戻った場合は再クリック
        print('  [note] 公開パネルに戻った、再度「投稿する」をクリック')
        await page.wait_for_timeout(1500)
        for btn_text in ['投稿する', '公開する', 'Post', 'Publish']:
            try:
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if await btn.count() > 0:
                    await btn.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(500)
                    await btn.click(timeout=5_000)
                    print(f'  [note] 投稿ボタン再クリック: 「{btn_text}」')
                    break
            except Exception:
                continue

        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('editor.note.com')"
                " || document.body.innerText.includes('\u8a18\u4e8b\u304c\u516c\u958b\u3055\u308c\u307e\u3057\u305f')",
                timeout=10_000,
            )
        except Exception:
            pass

        body_text2 = await page.evaluate('() => document.body.innerText')
        if '記事が公開されました' in body_text2 or 'editor.note.com' not in page.url:
            print(f'  [note] 投稿完了: {page.url}')
            return True

        raise Exception(f'投稿未完了（URL: {page.url}）')

    except Exception as e:
        print(f'  [ERROR] 投稿失敗: {e}')
        return False


async def post_articles_batch(
    articles: list[dict],
    headless: bool = True,
    stop_before_post: bool = False,
) -> tuple[int, int]:
    """
    1つのブラウザセッションで複数記事を連続投稿する。

    Parameters
    ----------
    articles         : format_article() の戻り値リスト
    headless         : True=ブラウザ非表示 / False=表示
    stop_before_post : True なら投稿直前で60秒停止（プレビュー確認用）

    Returns
    -------
    (ok_count, skip_count)
    """
    if not NOTE_EMAIL or not NOTE_PASSWORD:
        print('  [ERROR] .env に NOTE_EMAIL / NOTE_PASSWORD が設定されていません。')
        return 0, len(articles)

    ok, skip = 0, 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ja-JP',
            permissions=['clipboard-read', 'clipboard-write'],
        )
        page = await context.new_page()

        # ログインは1回だけ
        await _login(page)

        for art in articles:
            success = await _post_one(
                page,
                title=art['title'],
                free_body=art['free_body'],
                paid_body=art['paid_body'],
                price=art.get('price', 100),
                race_id=art.get('race_id', ''),
                stop_before_post=stop_before_post,
                sep_label=art.get('sep_label', '全印付き馬'),
            )
            if success:
                ok += 1
            else:
                skip += 1

        await browser.close()

    return ok, skip


async def post_article(
    title: str,
    free_body: str,
    paid_body: str,
    price: int = 100,
    headless: bool = True,
    race_id: str = '',
    **kwargs,
) -> bool:
    """後方互換用: 1記事のみ投稿する。"""
    if not NOTE_EMAIL or not NOTE_PASSWORD:
        print('  [ERROR] .env に NOTE_EMAIL / NOTE_PASSWORD が設定されていません。')
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ja-JP',
            permissions=['clipboard-read', 'clipboard-write'],
        )
        page = await context.new_page()
        await _login(page)
        result = await _post_one(page, title, free_body, paid_body, price, race_id)
        await browser.close()
        return result


if __name__ == '__main__':
    # 動作テスト用（headless=False で目視確認）
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    test_article = {
        'title': '【テスト投稿】AI競馬予想システム動作確認',
        'free_body': 'これはテスト投稿です。\n◎ 3番 テストウマ  勝率27% / 複勝61%  オッズ5.2倍',
        'paid_body': '【推奨買い目】\n  単勝 7番 テストウマB（11.8倍・条件B）\n\n【全馬予測】\n  1位 ◎ 3番 テストウマ  27% 61%  5.2倍',
        'price': 300,
        'headless': False,
    }
    result = asyncio.run(post_article(**test_article))
    print('結果:', '成功' if result else '失敗')
