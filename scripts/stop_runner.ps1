# Stop the experiment runner and its whole process tree, then verify nothing of this repo is left running.
#   powershell -NoProfile -File scripts/stop_runner.ps1
$repo = Split-Path -Parent $PSScriptRoot
$lock = Join-Path $repo "results\run_info\runner.lock"
if (Test-Path $lock) {
    $runnerPid = [int](Get-Content $lock)
    Write-Output "stopping runner PID $runnerPid and its process tree"
    taskkill /PID $runnerPid /T /F | Out-Null
    Remove-Item $lock -ErrorAction SilentlyContinue
} else {
    Write-Output "no runner lock file"
}
Start-Sleep -Seconds 1
$left = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -in 'python.exe', 'cbc.exe') -and ($_.CommandLine -like '*Quantum-Route*' -or $_.Name -eq 'cbc.exe')
}
if ($left) { $left | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize -Wrap } else { Write-Output "verified: no runner, python or cbc processes left" }
