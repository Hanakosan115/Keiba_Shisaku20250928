@echo off
rem 週次レースデータ収集タスクを登録する
rem 毎週月曜 06:00 に collect_weekly_races.py を実行

schtasks /create ^
  /tn "KeibaWeeklyCollect" ^
  /tr "py C:\Users\bu158\Keiba_Shisaku20250928\collect_weekly_races.py" ^
  /sc WEEKLY ^
  /d MON ^
  /st 06:00 ^
  /f

echo.
echo タスク登録完了: KeibaWeeklyCollect (毎週月曜 06:00)
echo.
schtasks /query /tn "KeibaWeeklyCollect" /fo LIST
pause
