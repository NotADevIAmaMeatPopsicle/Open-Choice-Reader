[CmdletBinding()]
param(
    [string]$BackendUrl = "http://127.0.0.1:8000/api/health",
    [string]$FrontendUrl = "http://127.0.0.1:8000",
    [int]$TimeoutSeconds = 5
)

$ErrorActionPreference = "Stop"

function Invoke-SmokeRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [switch]$UseBasicParsing,
        [switch]$UseRestMethod
    )

    try {
        if ($UseRestMethod) {
            return Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSeconds
        }

        if ($UseBasicParsing) {
            return Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing
        }

        return Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds
    }
    catch {
        throw "$Name check failed for $Url. $($_.Exception.Message)"
    }
}

$backendPayload = Invoke-SmokeRequest -Name "Backend health" -Url $BackendUrl -UseRestMethod

if ($backendPayload.status -ne "ok") {
    throw "Backend health returned status '$($backendPayload.status)' instead of 'ok'."
}

$frontendResponse = Invoke-SmokeRequest -Name "Frontend root" -Url $FrontendUrl -UseBasicParsing

if ($frontendResponse.StatusCode -ne 200) {
    throw "Frontend root returned HTTP $($frontendResponse.StatusCode) instead of 200."
}

Write-Host "Smoke test passed."
Write-Host "Backend: $BackendUrl status ok"
Write-Host "Frontend: $FrontendUrl HTTP 200"
