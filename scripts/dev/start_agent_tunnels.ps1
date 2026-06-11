param(
    [Parameter(Mandatory = $true)]
    [string]$ServerHost,

    [Parameter(Mandatory = $true)]
    [string]$ServerUser,

    [string]$IdentityFile = "",

    [bool]$UseSamePorts = $true
)

$ErrorActionPreference = "Stop"

if (-not $UseSamePorts) {
    throw "UseSamePorts must remain true for the current demo bridge."
}

if ($IdentityFile -and -not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Identity file does not exist: $IdentityFile"
}

$ports = @(
    10000,
    10001,
    10002,
    10006,
    10009,
    10022,
    10020,
    10010,
    10011,
    10013,
    10012,
    10014,
    10015,
    10023,
    10016,
    10024
)

function Test-LocalPortInUse {
    param([int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $result.AsyncWaitHandle.WaitOne(200)
        if ($connected) {
            $client.EndConnect($result)
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

foreach ($port in $ports) {
    if (Test-LocalPortInUse -Port $port) {
        throw "Local port 127.0.0.1:$port is already in use. Stop that process before starting the tunnel."
    }
}

$sshArgs = @(
    "-N",
    "-T",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3"
)

if ($IdentityFile) {
    $sshArgs += @("-i", $IdentityFile)
}

foreach ($port in $ports) {
    $sshArgs += @("-L", "127.0.0.1:${port}:127.0.0.1:${port}")
}

$sshArgs += "$ServerUser@$ServerHost"

Write-Host "Starting R8-12 local remote-agent demo tunnel."
Write-Host "Local bind: 127.0.0.1 only"
Write-Host "Forwarded ports: $($ports -join ', ')"
Write-Host "Press Ctrl+C to close the tunnel."

& ssh @sshArgs
