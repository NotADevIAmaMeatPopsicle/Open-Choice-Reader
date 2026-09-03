[CmdletBinding()]
param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslRepoPath = "",
    [switch]$RemoveExposure,
    [int[]]$Ports = @(8000)
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

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedWslRepoPath = Resolve-WslRepoPath -RepoRoot $repoRoot -Distro $WslDistro -ExplicitPath $WslRepoPath

Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "bash scripts/stop.sh"

if ($RemoveExposure) {
    foreach ($port in $Ports) {
        cmd /c "netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port" | Out-Null
        $ruleName = "Open Choice Reader Port $port"
        Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    }
}

Write-Host "Open Choice Reader host stopped."
