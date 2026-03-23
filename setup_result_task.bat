@echo off
chcp 65001 > nul
echo KeibaResultFetch タスク登録中...

schtasks /create ^
  /tn "KeibaResultFetch" ^
  /tr "py C:\Users\bu158\Keiba_Shisaku20250928\paper_trade_result_auto.py" ^
  /sc weekly ^
  /d SAT,SUN ^
  /st 18:00 ^
  /f ^
  /rl highest

if %errorlevel% == 0 (
    echo 登録完了: KeibaResultFetch (土日 18:00)
) else (
    echo 失敗。管理者として実行してください。
)
pause
