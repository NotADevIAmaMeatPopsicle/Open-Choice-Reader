[CmdletBinding()]
param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslRepoPath = "",
    [switch]$Bootstrap,
    [switch]$SkipBuild,
    [switch]$Expose,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Resolve-WslRepoPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Distro,
        [string]$ExplicitPath
    )

    if ($ExplicitPath) {
        return $ExplicitPath
    }

    $normalizedRepoRoot = $RepoRoot -replace "\\", "/"
    $resolvedPath = (& wsl -d $Distro -- wslpath -a $normalizedRepoRoot).Trim()

    if (-not $resolvedPath) {
        throw "Unable to resolve a WSL path for $RepoRoot. Pass -WslRepoPath explicitly."
    }

    return $resolvedPath
}

function Invoke-WslScript {
    param(
        [Parameter(Mandatory = $true)][string]$Distro,
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string]$Command
    )

    & wsl -d $Distro --cd $RepoPath -- bash -lc $Command
    if ($LASTEXITCODE -ne 0) {
        throw "WSL command failed: $Command"
    }
}

function Get-PreferredHostIp {
    $address = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL|Hyper-V"
        } |
        Sort-Object InterfaceMetric, SkipAsSource |
        Select-Object -First 1

    if ($address) {
        return $address.IPAddress
    }

    return "127.0.0.1"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedWslRepoPath = Resolve-WslRepoPath -RepoRoot $repoRoot -Distro $WslDistro -ExplicitPath $WslRepoPath

if ($Bootstrap) {
    Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "bash scripts/bootstrap.sh"
}

if (-not $SkipBuild) {
    Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "cd frontend && npm run build"
}

$listenHost = if ($Expose) { "0.0.0.0" } else { "127.0.0.1" }
Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "bash scripts/stop.sh || true; OPEN_CHOICE_READER_HOST=$listenHost OPEN_CHOICE_READER_PORT=$Port bash scripts/start.sh"

if ($Expose) {
    & (Join-Path $PSScriptRoot "expose-wsl.ps1") -WslDistro $WslDistro -Ports @($Port)
}

$healthUrl = "http://127.0.0.1:$Port/api/health"
$uiUrl = "http://127.0.0.1:$Port"
$hostIp = Get-PreferredHostIp
$lanUrl = "http://${hostIp}:$Port"

Write-Host ""
Write-Host "Open Choice Reader host started."
Write-Host "Local UI: $uiUrl"
Write-Host "Local health: $healthUrl"
if ($Expose) {
    Write-Host "LAN UI: $lanUrl"
    Write-Host "LAN health: $lanUrl/api/health"
}
