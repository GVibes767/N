$ErrorActionPreference = "Stop"
$Root = "E:\Для chat\.ai\omniroute"
$Status = Join-Path $Root "bootstrap-status.json"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
function Save-Status($state,$message) {
  $o = [ordered]@{ time=(Get-Date).ToString("o"); state=$state; message=$message; host=$env:COMPUTERNAME }
  $o | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $Status
}
try {
  Save-Status "starting" "Checking Node/npm and OmniRoute"
  Get-Command node -ErrorAction Stop | Out-Null
  Get-Command npm -ErrorAction Stop | Out-Null
  $has = (& npm list -g omniroute --depth=0 2>$null) -match "omniroute@"
  if (-not $has) {
    Save-Status "installing" "Installing OmniRoute globally"
    & npm install -g omniroute
    if ($LASTEXITCODE -ne 0) { throw "npm install -g omniroute failed: $LASTEXITCODE" }
  }
  $exe = (Get-Command omniroute -ErrorAction Stop).Source
  $existing = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "omniroute" -and $_.CommandLine -match "20128" }
  if (-not $existing) {
    Save-Status "starting-router" "Starting OmniRoute on port 20128"
    Start-Process -FilePath $exe -ArgumentList "--port","20128" -WindowStyle Hidden
    Start-Sleep -Seconds 5
  }
  $listen = Test-NetConnection -ComputerName 127.0.0.1 -Port 20128 -WarningAction SilentlyContinue
  if (-not $listen.TcpTestSucceeded) { throw "OmniRoute port 20128 is not listening" }
  Save-Status "ready" "OmniRoute installed and running"
} catch {
  Save-Status "failed" $_.Exception.Message
  exit 1
}