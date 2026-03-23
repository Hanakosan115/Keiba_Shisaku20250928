@echo off
chcp 65001 > nul
echo Starting full 2020-2025 GUI backtest...
cd /d C:\Users\bu158\Keiba_Shisaku20250928
py run_gui_backtest.py > backtest_gui_all_years.log 2>&1
echo Done. See backtest_gui_all_years.log
