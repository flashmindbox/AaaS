# Port-conflict detector for AaaS demo bundle.
#
# Usage:   powershell -NoProfile -File portcheck.ps1 <gw> <tts> [<stt> <translate>]
# Stdout:  lines of KEY=VALUE consumed by start.bat
#            GATEWAY_PORT=<n>
#            TTS_PORT=<n>
#            STT_PORT=<n>
#            TRANSLATE_PORT=<n>
#          or
#            ERROR=<message>
#
# If any requested port is in use we scan +50 above it for a free one.
# Backward-compatible with the old two-arg invocation — callers that
# only care about TTS + Gateway keep working.

param(
  [int]$GatewayPort   = 8000,
  [int]$TtsPort       = 8001,
  [int]$SttPort       = 8002,
  [int]$TranslatePort = 8003
)

$ErrorActionPreference = "Stop"

function Test-PortFree([int]$Port) {
  try {
    $inUse = Get-NetTCPConnection -LocalPort $Port -State Listen `
      -ErrorAction SilentlyContinue
    return -not $inUse
  } catch {
    try {
      $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback, $Port)
      $listener.Start()
      $listener.Stop()
      return $true
    } catch {
      return $false
    }
  }
}

function Find-FreePort([int]$Start, [int]$Span = 50, $Taken = @()) {
  for ($p = $Start; $p -lt ($Start + $Span); $p++) {
    if ($Taken -contains $p) { continue }
    if (Test-PortFree -Port $p) { return $p }
  }
  return $null
}

$script:taken = @()
function Resolve-Port {
  param(
    [Parameter(Mandatory=$true)][int]$Wanted,
    [Parameter(Mandatory=$true)][string]$Label
  )
  if ((Test-PortFree -Port $Wanted) -and (-not ($script:taken -contains $Wanted))) {
    $script:taken += $Wanted
    return $Wanted
  }
  $alt = Find-FreePort -Start ($Wanted + 1) -Taken $script:taken
  if ($null -ne $alt) {
    Write-Host "  $Label port $Wanted busy -> using $alt"
    $script:taken += $alt
    return $alt
  }
  return $null
}

$gw = Resolve-Port -Wanted $GatewayPort   -Label "gateway"
$tt = Resolve-Port -Wanted $TtsPort       -Label "tts"
$st = Resolve-Port -Wanted $SttPort       -Label "stt"
$tr = Resolve-Port -Wanted $TranslatePort -Label "translate"

if (-not $gw -or -not $tt -or -not $st -or -not $tr) {
  "ERROR=No free port near $GatewayPort/$TtsPort/$SttPort/$TranslatePort (close Zoom/Skype/Docker and retry)"
  exit 1
}

"GATEWAY_PORT=$gw"
"TTS_PORT=$tt"
"STT_PORT=$st"
"TRANSLATE_PORT=$tr"
exit 0
