@echo off
chcp 65001 > nul
echo タスクスケジューラ設定中...

REM 既存タスク削除（存在しなくてもエラー無視）
schtasks /delete /tn "KeibaScheduleFetch" /f 2>nul
schtasks /delete /tn "KeibaOddsSnapshot" /f 2>nul

REM タスク1: 土日 07:00 スケジュール取得
schtasks /create ^
  /tn "KeibaScheduleFetch" ^
  /tr "py C:\Users\bu158\Keiba_Shisaku20250928\odds_collector\schedule_fetch.py" ^
  /sc WEEKLY /d SAT,SUN ^
  /st 07:00 ^
  /f
if %errorlevel% == 0 (
    echo [OK] KeibaScheduleFetch タスク登録完了
) else (
    echo [ERROR] KeibaScheduleFetch 登録失敗
)

REM タスク2: 土日 09:00〜17:30 30分ごとにオッズ取得
schtasks /create ^
  /tn "KeibaOddsSnapshot" ^
  /tr "py C:\Users\bu158\Keiba_Shisaku20250928\odds_collector\odds_snapshot.py --timing 30min_before" ^
  /sc WEEKLY /d SAT,SUN ^
  /st 09:00 /et 17:30 ^
  /ri 30 ^
  /f
if %errorlevel% == 0 (
    echo [OK] KeibaOddsSnapshot タスク登録完了
) else (
    echo [ERROR] KeibaOddsSnapshot 登録失敗
)

echo.
echo 登録済みタスク一覧:
schtasks /query /tn "KeibaScheduleFetch" /fo LIST 2>nul
schtasks /query /tn "KeibaOddsSnapshot" /fo LIST 2>nul

pause
