# Hughes Power Watchdog WiFi read-only API probe
# Calls ONLY:
#   GET https://api.watchdogsrv.com/user/login
#   GET https://api.watchdogsrv.com/device/list
# It does not call relay, reset, edit, add, delete, share, or other mutation endpoints.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$BaseUri = 'https://api.watchdogsrv.com'
$AppVersion = '1.0.15'
$DeviceType = 'android'

function ConvertFrom-SecureStringPlainText {
    param([Parameter(Mandatory)][Security.SecureString]$SecureString)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Get-TokenFromResponse {
    param([Parameter(Mandatory)]$Response)

    if ($null -ne $Response.data -and $null -ne $Response.data.token) {
        return [string]$Response.data.token
    }
    if ($null -ne $Response.token) {
        return [string]$Response.token
    }
    return $null
}

function Invoke-WatchdogGet {
    param(
        [Parameter(Mandatory)][ValidateSet('/user/login','/device/list')][string]$Path,
        [Parameter(Mandatory)][hashtable]$Query
    )

    $pairs = foreach ($key in $Query.Keys) {
        $encodedKey = [Uri]::EscapeDataString([string]$key)
        $encodedValue = [Uri]::EscapeDataString([string]$Query[$key])
        "$encodedKey=$encodedValue"
    }

    $uri = "$BaseUri$Path?" + ($pairs -join '&')
    $headers = @{
        'Accept' = 'application/json'
        'User-Agent' = 'PowerWatchdogWiFi/1.0.15 (Android; read-only interoperability probe)'
    }

    return Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 30
}

Write-Host ''
Write-Host 'Hughes Power Watchdog WiFi — read-only probe' -ForegroundColor Cyan
Write-Host 'This script calls only /user/login and /device/list.'
Write-Host 'It does not issue relay-control, reset, edit, add, delete, or sharing requests.'
Write-Host ''

$account = Read-Host 'Hughes account email'
$passwordSecure = Read-Host 'Hughes account password' -AsSecureString
$passwordPlain = ConvertFrom-SecureStringPlainText -SecureString $passwordSecure

try {
    Write-Host ''
    Write-Host 'Authenticating…'
    $loginResponse = Invoke-WatchdogGet -Path '/user/login' -Query @{
        account = $account
        password = $passwordPlain
        device = $DeviceType
        version = $AppVersion
        token = ''
    }

    $token = Get-TokenFromResponse -Response $loginResponse
    if ([string]::IsNullOrWhiteSpace($token)) {
        Write-Host 'Login returned no token. Redacted response:' -ForegroundColor Yellow
        $loginResponse | ConvertTo-Json -Depth 20
        exit 2
    }

    Write-Host 'Authentication succeeded. Token received but not displayed or saved.' -ForegroundColor Green
    Write-Host 'Requesting the account device list…'

    $deviceResponse = Invoke-WatchdogGet -Path '/device/list' -Query @{
        token = $token
        device = $DeviceType
        version = $AppVersion
    }

    $outputPath = Join-Path $PSScriptRoot 'watchdog_device_list.json'
    $deviceResponse | ConvertTo-Json -Depth 30 | Set-Content -Path $outputPath -Encoding UTF8

    Write-Host ''
    Write-Host 'Device-list response:' -ForegroundColor Cyan
    $deviceResponse | ConvertTo-Json -Depth 30
    Write-Host ''
    Write-Host "A copy was saved to: $outputPath" -ForegroundColor Green
    Write-Host 'Review it before sharing. It should not contain your password or login token.'
}
catch {
    Write-Host ''
    Write-Host 'The request failed:' -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
        Write-Host 'Server response:'
        Write-Host $_.ErrorDetails.Message
    }
    exit 1
}
finally {
    # Minimize how long the plaintext password remains referenced in this process.
    $passwordPlain = $null
    $token = $null
}
