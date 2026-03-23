# setup_result_task.ps1
# KeibaResultFetch タスク登録（土日 18:00 自動実行）
# 実行方法: powershell -ExecutionPolicy Bypass -File setup_result_task.ps1

$TaskName   = "KeibaResultFetch"
$ScriptPath = "C:\Users\bu158\Keiba_Shisaku20250928\paper_trade_result_auto.py"
$PythonExe  = "py"
$WorkDir    = "C:\Users\bu158\Keiba_Shisaku20250928"
$LogFile    = "C:\Users\bu158\Keiba_Shisaku20250928\result_auto_log.txt"

# 既存タスク削除
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>競馬ペーパートレード結果自動取得（土日18:00）</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-03-08T18:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Saturday />
          <Sunday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>$PythonExe</Command>
      <Arguments>$ScriptPath >> $LogFile 2>&amp;1</Arguments>
      <WorkingDirectory>$WorkDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -TaskName $TaskName -Xml $Xml -Force
Write-Host "タスク登録完了: $TaskName（土日 18:00）"
