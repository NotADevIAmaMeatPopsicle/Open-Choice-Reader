[CmdletBinding()]
param(
    [string]$WslDistro = "Ubuntu",
    [string]$WslRepoPath = ""
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

Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "bash scripts/bootstrap.sh"
Invoke-WslScript -Distro $WslDistro -RepoPath $resolvedWslRepoPath -Command "cd frontend && npm run build"

Write-Host "Open Choice Reader host dependencies are installed."
Write-Host "Next step: powershell -ExecutionPolicy Bypass -File .\\scripts\\start-open-choice-reader.ps1"
