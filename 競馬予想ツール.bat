@echo off
chcp 65001 > nul
cd /d %~dp0

REM ── 土日のみ: スケジュール取得を自動実行 ─────────────────────────
for /f "tokens=1" %%d in ('powershell -nologo -command "(Get-Date).DayOfWeek.ToString()"') do set DOW=%%d
if "%DOW%"=="Saturday" (
    echo [%time%] 土曜: レーススケジュール取得中...
    py odds_collector/schedule_fetch.py
    echo [%time%] スケジュール取得完了
)
if "%DOW%"=="Sunday" (
    echo [%time%] 日曜: レーススケジュール取得中...
    py odds_collector/schedule_fetch.py
    echo [%time%] スケジュール取得完了
)

REM ── GUI起動 ──────────────────────────────────────────────────────
py keiba_prediction_gui_v3.py
pause
