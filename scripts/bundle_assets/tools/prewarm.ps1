# Prewarm every TTS model the widget can reach.
#
# Meta MMS-TTS checkpoints take 10-30 seconds to JIT through torch the
# first time each is used. Phase A3 added Hindi + English alongside the
# default Odia voice. If a judge's first click picks Hindi, the JIT
# delay is indistinguishable from a crash -- so we warm all three
# sequentially here. The three runs can't be parallelised: the service
# lazy-loads one MMS model at a time and they would just serialise
# behind the first one anyway.
#
# Best-effort: any per-language failure is logged and we move on. A
# partial warm still beats a cold stage. Meta MMS-TTS is the only
# TTS engine - there is no browser-voice fallback, so an un-warmed
# language will simply take longer on its first click (or surface a
# TTS error if the service is not up).

param(
  [int]$GatewayPort
)

$ErrorActionPreference = "Stop"

# Build prewarm phrases from explicit code points so this script is
# safe to save as ASCII / ANSI / UTF-8-without-BOM -- Windows PowerShell
# 5.1 mis-decodes raw UTF-8 literals (assumes Windows-1252) and would
# corrupt the POST body, so the server would reject it as the wrong
# script for the requested language.
#   Odia  = "Namaskara"  (B28 B2E B38 B4D B15 B3E B30)
#   Hindi = "Namaste"    (928 92E 938 94D 924 947)
# English is pure ASCII so no escape gymnastics needed.
$odia  = -join @(0x0B28, 0x0B2E, 0x0B38, 0x0B4D, 0x0B15, 0x0B3E, 0x0B30 |
                 ForEach-Object { [char]$_ })
$hindi = -join @(0x0928, 0x092E, 0x0938, 0x094D, 0x0924, 0x0947 |
                 ForEach-Object { [char]$_ })
$english = "Hello"

$apiKey  = "aaas_live_00000000000000000000000000000000"   # dev-seed tenant
$uri     = "http://127.0.0.1:$GatewayPort/tts/synthesise"
$outfile = Join-Path $env:TEMP "aaas-prewarm.wav"

$phrases = @(
  @{ Lang = "or"; Text = $odia    },
  @{ Lang = "hi"; Text = $hindi   },
  @{ Lang = "en"; Text = $english }
)

$warmed = 0
foreach ($p in $phrases) {
  $json  = '{"text":"' + $p.Text + '","lang":"' + $p.Lang + '"}'
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  try {
    Invoke-WebRequest `
      -Uri $uri `
      -Method POST `
      -Body $bytes `
      -ContentType "application/json; charset=utf-8" `
      -Headers @{ "X-API-Key" = $apiKey } `
      -UseBasicParsing `
      -TimeoutSec 120 `
      -OutFile $outfile `
      -ErrorAction Stop | Out-Null
    $size = (Get-Item $outfile).Length
    Write-Host "  prewarm ok $($p.Lang) ($size bytes)"
    $warmed++
  } catch {
    Write-Host "  prewarm skipped $($p.Lang): $($_.Exception.Message)"
  }
}

if ($warmed -lt $phrases.Count) {
  Write-Host "  (first click in any un-warmed language may lag; no browser-voice fallback - MMS-TTS is the only engine)"
}
