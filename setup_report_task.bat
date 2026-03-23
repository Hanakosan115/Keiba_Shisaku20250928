@echo off
chcp 65001 > nul
echo KeibaReportPost タスク登録中...

schtasks /create ^
  /tn "KeibaReportPost" ^
  /tr "py C:\Users\bu158\Keiba_Shisaku20250928\note_publisher\post_result_report.py" ^
  /sc weekly ^
  /d SAT,SUN ^
  /st 18:30 ^
  /f ^
  /rl highest

if %errorlevel% == 0 (
    echo 登録完了: KeibaReportPost (土日 18:30)
) else (
    echo 失敗。管理者として実行してください。
)
pause
