# -*- coding: utf-8 -*-
# Windows 任务计划程序注册脚本
# 将 Meme 舆情预警系统注册为 Windows 后台定时任务 (每 5 分钟自动执行一次全网扫描与飞书投递)

$TaskName = "MemeSentimentAlert"
$PythonPath = "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
$ScriptPath = "E:\Github\meme-sentiment-alert\main.py"
$WorkingDir = "E:\Github\meme-sentiment-alert"

# 1. 检查是否存在旧任务，有则删除
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 2. 定义触发器：每日启动，每 5 分钟重复执行一次
$Trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)).Repetition

# 3. 定义动作：后台静默执行 python main.py --once
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "main.py --once" -WorkingDirectory $WorkingDir

# 4. 定义任务设置
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

# 5. 注册任务
Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $Action -Settings $Settings -Description "Meme 代币与 NFT 链上舆情异动实时监控与飞书预警定时任务" -Force

Write-Host "✓ Windows 任务计划程序 [$TaskName] 注册成功！每 5 分钟自动执行一次全网异动巡检并投递飞书 Digest。"
