# PRAHARI-SIM demo launcher for Windows (Phase 10). Serves the static dashboard (dashboard\dist) on
# http://localhost:8765 and opens it in presenter mode: no engine, no internet. Builds the dashboard first when
# dist\ is missing or with -Build (that step needs Node.js and `npm install` done once).
#   powershell -ExecutionPolicy Bypass -File scripts\demo.ps1          # or double-click scripts\demo.cmd
#   powershell -ExecutionPolicy Bypass -File scripts\demo.ps1 -Build   # rebuild, then serve
param([switch]$Build, [int]$Port = 8765)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$url = "http://localhost:$Port/?presenter=1"

if ($Build -or -not (Test-Path "dashboard\dist\index.html")) {
  Write-Host "building the dashboard..."
  Push-Location dashboard; npm run build; Pop-Location
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) {
  $server = Start-Process -FilePath $py.Source -PassThru -NoNewWindow `
    -ArgumentList "-m", "http.server", "$Port", "--bind", "127.0.0.1", "--directory", "dashboard\dist"
} else {
  Push-Location dashboard
  $server = Start-Process -FilePath "npx.cmd" -PassThru -NoNewWindow -ArgumentList "vite", "preview", "--port", "$Port", "--strictPort"
  Pop-Location
}
Start-Sleep -Seconds 1
Start-Process $url   # keys: 1-9 steps, Space play, S/R switches, F full screen
Write-Host "serving dashboard\dist on $url - close this window or press Ctrl-C to stop"
Wait-Process -Id $server.Id
