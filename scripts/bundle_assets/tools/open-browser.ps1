# Open the demo URL in the best available browser.
#
# Preference order:
#   1. Microsoft Edge   -- widely installed on Windows 11.
#   2. Google Chrome    -- second most common; fine on Windows/macOS.
#   3. Default browser  -- whatever Windows has configured.
#
# The bundled TTS is Meta MMS-TTS (served by aaas-tts.exe) — browser
# choice no longer affects speech quality because we do not use the
# browser's Web Speech API.
#
# Never blocks: if all three paths fail we still exit 0 because the
# launcher already printed the URL for manual copy-paste.

param(
  [string]$Url
)

$ErrorActionPreference = "SilentlyContinue"

$candidates = @(
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)

foreach ($path in $candidates) {
  if ($path -and (Test-Path $path)) {
    Start-Process -FilePath $path -ArgumentList $Url | Out-Null
    Write-Host "  opened $([System.IO.Path]::GetFileName($path))"
    exit 0
  }
}

# Fall back to whatever is registered as the default URL handler.
try {
  Start-Process $Url | Out-Null
  Write-Host "  opened default browser"
} catch {
  Write-Host "  could not open a browser automatically"
  Write-Host "  visit this URL manually:  $Url"
}
