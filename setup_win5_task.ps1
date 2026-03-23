# setup_win5_task.ps1 - KeibaWin5Poster 日曜朝に WIN5予想記事を自動投稿
# 日曜 09:15 に1回だけ実行（発走は通常10:00〜、記事生成に余裕を持たせた時間）

Unregister-ScheduledTask -TaskName 'KeibaWin5Poster' -Confirm:$false -ErrorAction SilentlyContinue

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-03-15T09:15:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Sunday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>bu158</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>py</Command>
      <Arguments>C:\Users\bu158\Keiba_Shisaku20250928\note_publisher\run_auto_post.py --win5</Arguments>
      <WorkingDirectory>C:\Users\bu158\Keiba_Shisaku20250928</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -TaskName 'KeibaWin5Poster' -Xml $xml -Force

Get-ScheduledTaskInfo -TaskName 'KeibaWin5Poster' | Select-Object TaskName, NextRunTime
