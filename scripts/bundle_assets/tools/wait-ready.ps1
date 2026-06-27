# Real-readiness probe for AaaS demo bundle.
#
# Polls:
#   - gateway   /healthz   (uvicorn is up)
#   - tts       /readyz    (VITS model loaded)
#   - stt       /readyz    (engine loaded; mock returns 200 immediately)
#   - translate /readyz    (engine loaded; mock returns 200 immediately)
#
# Exits 0 only when ALL are 200. Exits 1 after TimeoutSec seconds.
#
# STT and Translate ports are optional — if omitted, only gateway + TTS
# are waited on, preserving backward compatibility with old two-service
# bundles.

param(
  [int]$GatewayPort,
  [int]$TtsPort,
  [int]$SttPort       = 0,
  [int]$TranslatePort = 0,
  [int]$TimeoutSec    = 120
)

$ErrorActionPreference = "Stop"

$deadline = (Get-Date).AddSeconds($TimeoutSec)

function Probe([string]$Url) {
  try {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 `
      -ErrorAction Stop
    return $r.StatusCode -eq 200
  } catch {
    return $false
  }
}

$targets = @()
$targets += @{ Label = "gateway";   Url = "http://127.0.0.1:$GatewayPort/healthz"; Ok = $false }
$targets += @{ Label = "tts";       Url = "http://127.0.0.1:$TtsPort/readyz";     Ok = $false }
if ($SttPort -gt 0) {
  $targets += @{ Label = "stt";       Url = "http://127.0.0.1:$SttPort/readyz";       Ok = $false }
}
if ($TranslatePort -gt 0) {
  $targets += @{ Label = "translate"; Url = "http://127.0.0.1:$TranslatePort/readyz"; Ok = $false }
}

Write-Host ("Waiting for {0} services: {1} ..." -f $targets.Count, (($targets | ForEach-Object { $_.Label }) -join ", "))

while ((Get-Date) -lt $deadline) {
  $pending = $false
  foreach ($t in $targets) {
    if (-not $t.Ok) {
      if (Probe $t.Url) {
        $t.Ok = $true
        Write-Host ("  {0} ready" -f $t.Label)
      } else {
        $pending = $true
      }
    }
  }
  if (-not $pending) { exit 0 }
  Start-Sleep -Milliseconds 500
}

$report = ($targets | ForEach-Object { "$($_.Label)=$($_.Ok)" }) -join " "
Write-Host "Timeout after ${TimeoutSec}s -- $report. See logs\*.log."
exit 1
