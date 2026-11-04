# Daily refresh from this PC (Windows scheduled task "CX ticket dashboard refresh", 10:00 IST).
# Refreshes the data with the key in ~/.metabase_key, pushes index.html; the push starts the
# GitHub workflow, which sends the Slack alerts. Log: scripts/daily_local.log (not committed).
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$log = Join-Path $PSScriptRoot 'daily_local.log'
Set-Location $repo
Start-Transcript -Path $log -Append | Out-Null
try {
    git pull --rebase -q
    if ($LASTEXITCODE) { throw 'git pull failed' }
    py -X utf8 scripts/refresh_build.py
    if ($LASTEXITCODE) { throw 'refresh failed' }
    git add index.html
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { Write-Output 'No data change'; return }
    git commit -q -m "Daily data refresh $(Get-Date -Format yyyy-MM-dd)"
    git push -q
    if ($LASTEXITCODE) { git pull --rebase -q; git push -q }
    if ($LASTEXITCODE) { throw 'git push failed' }
    Write-Output "Pushed at $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
} finally {
    Stop-Transcript | Out-Null
}
