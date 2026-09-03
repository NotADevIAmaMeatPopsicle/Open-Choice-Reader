[CmdletBinding()]
param(
    [string]$WslDistro = "Ubuntu",
    [int[]]$Ports = @(8000)
)

$ErrorActionPreference = "Stop"

$wslIp = (& wsl -d $WslDistro -- hostname -I).Trim().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)[0]
if (-not $wslIp) {
    throw "Unable to determine the WSL IP for distro '$WslDistro'."
}

foreach ($port in $Ports) {
    cmd /c "netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port" | Out-Null
    cmd /c "netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=$wslIp connectport=$port" | Out-Null

    $ruleName = "Open Choice Reader Port $port"
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
}

Write-Host "WSL IP: $wslIp"
Write-Host ""
cmd /c "netsh interface portproxy show all"
Write-Host ""
Get-NetFirewallRule -DisplayName "Open Choice Reader Port *" |
    Select-Object DisplayName, Enabled, Direction, Action |
    Format-Table -AutoSize
