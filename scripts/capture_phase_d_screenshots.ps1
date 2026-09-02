param(
  [string]$BaseUrl = "http://127.0.0.1:5175",
  [string]$ScreenshotDir = "docs\screenshots",
  [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
  [int]$DebugPort = 9222
)

$ErrorActionPreference = "Stop"

function Receive-CdpMessage {
  param([System.Net.WebSockets.ClientWebSocket]$Socket)

  $buffer = New-Object byte[] 1048576
  $stream = [System.IO.MemoryStream]::new()
  do {
    $segment = [System.ArraySegment[byte]]::new($buffer)
    $result = $Socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).Result
    if ($result.Count -gt 0) {
      $stream.Write($buffer, 0, $result.Count)
    }
  } until ($result.EndOfMessage)
  [Text.Encoding]::UTF8.GetString($stream.ToArray())
}

function Send-Cdp {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Method,
    [hashtable]$Params = @{}
  )

  $script:CdpId += 1
  $payload = @{ id = $script:CdpId; method = $Method; params = $Params } | ConvertTo-Json -Depth 30 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
  $Socket.SendAsync([System.ArraySegment[byte]]::new($bytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()

  while ($true) {
    $message = Receive-CdpMessage -Socket $Socket
    $parsed = $message | ConvertFrom-Json
    if ($parsed.id -eq $script:CdpId) {
      if ($parsed.error) {
        throw "CDP $Method failed: $($parsed.error.message)"
      }
      return $parsed.result
    }
  }
}

function Invoke-CdpScript {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Expression
  )
  Send-Cdp -Socket $Socket -Method "Runtime.evaluate" -Params @{ expression = $Expression; returnByValue = $true; awaitPromise = $false }
}

function Wait-ForText {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Text,
    [int]$TimeoutMs = 45000
  )

  $quoted = $Text | ConvertTo-Json -Compress
  $started = Get-Date
  while (((Get-Date) - $started).TotalMilliseconds -lt $TimeoutMs) {
    $result = Invoke-CdpScript -Socket $Socket -Expression "document.body && document.body.innerText.includes($quoted)"
    if ($result.result.value -eq $true) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Timed out waiting for visible text: $Text"
}

function Wait-ForEnabled {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Text,
    [int]$TimeoutMs = 90000
  )

  $quoted = $Text | ConvertTo-Json -Compress
  $started = Get-Date
  while (((Get-Date) - $started).TotalMilliseconds -lt $TimeoutMs) {
    $expression = "(() => { const el = [...document.querySelectorAll('button')].find((item) => (item.innerText || item.textContent || '').trim().includes($quoted)); return !!el && !el.disabled; })()"
    $result = Invoke-CdpScript -Socket $Socket -Expression $expression
    if ($result.result.value -eq $true) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Timed out waiting for enabled button: $Text"
}
function Click-Text {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Text
  )

  $quoted = $Text | ConvertTo-Json -Compress
  $expression = @"
(() => {
  const text = $quoted;
  const elements = [...document.querySelectorAll('button,a,[role="button"]')];
  const element = elements.find((item) => (item.innerText || item.textContent || '').trim().includes(text));
  if (!element) return false;
  element.click();
  return true;
})()
"@
  $result = Invoke-CdpScript -Socket $Socket -Expression $expression
  if ($result.result.value -ne $true) {
    throw "Could not click visible text: $Text"
  }
}

function Save-Screenshot {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$FileName
  )

  Start-Sleep -Milliseconds 900
  $result = Send-Cdp -Socket $Socket -Method "Page.captureScreenshot" -Params @{ format = "png"; fromSurface = $true; captureBeyondViewport = $false }
  [IO.File]::WriteAllBytes((Join-Path $ScreenshotDir $FileName), [Convert]::FromBase64String($result.data))
  Write-Output $FileName
}

New-Item -ItemType Directory -Force -Path $ScreenshotDir | Out-Null

try {
  Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/version" | Out-Null
} catch {
  $profile = Join-Path (Resolve-Path ".") ".tmp-chrome-phase-d"
  Start-Process -FilePath $ChromePath -WindowStyle Hidden -ArgumentList @(
    "--headless=new",
    "--remote-debugging-port=$DebugPort",
    "--user-data-dir=$profile",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
  )
  Start-Sleep -Seconds 2
}

$target = [uri]::EscapeDataString("$BaseUrl/")
$page = Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:$DebugPort/json/new?$target"
$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$script:CdpId = 0
$socket.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()

try {
  Send-Cdp -Socket $socket -Method "Page.enable" | Out-Null
  Send-Cdp -Socket $socket -Method "Runtime.enable" | Out-Null
  Send-Cdp -Socket $socket -Method "Emulation.setDeviceMetricsOverride" -Params @{ width = 1440; height = 1000; deviceScaleFactor = 1; mobile = $false } | Out-Null
  Send-Cdp -Socket $socket -Method "Page.navigate" -Params @{ url = "$BaseUrl/" } | Out-Null
  Wait-ForText -Socket $socket -Text "Run audit" -TimeoutMs 20000

  Save-Screenshot -Socket $socket -FileName "01-home.png"
  Click-Text -Socket $socket -Text "Build batch"
  Wait-ForEnabled -Socket $socket -Text "Run audit" -TimeoutMs 90000
  Save-Screenshot -Socket $socket -FileName "02-world-builder.png"
  Click-Text -Socket $socket -Text "Run audit"
  Wait-ForText -Socket $socket -Text "Here is what needs attention." -TimeoutMs 90000

  Save-Screenshot -Socket $socket -FileName "01-home-demo-ready.png"
  Click-Text -Socket $socket -Text "Review priority case"
  Wait-ForText -Socket $socket -Text "Cases where Auditra needs you" -TimeoutMs 20000
  Save-Screenshot -Socket $socket -FileName "08-human-review.png"
  Click-Text -Socket $socket -Text "Audit"
  Wait-ForText -Socket $socket -Text "Controller" -TimeoutMs 20000
  Save-Screenshot -Socket $socket -FileName "05-controller.png"
} finally {
  $socket.Dispose()
}
