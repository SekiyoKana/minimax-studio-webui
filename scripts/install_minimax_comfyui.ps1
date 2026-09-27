$ErrorActionPreference = 'Stop'

$resourcePath = Join-Path $PSScriptRoot 'MiniMaxH3-ComfyUI-Resources.zip'
if (-not (Test-Path -LiteralPath $resourcePath -PathType Leaf)) {
    Write-Host "Missing resource archive: $resourcePath" -ForegroundColor Red
    exit 2
}

$pythonExecutable = $null
$pythonPrefix = @()
$pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    & $pythonLauncher.Source -3.11 --version *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonExecutable = $pythonLauncher.Source
        $pythonPrefix = @('-3.11')
    }
}

if (-not $pythonExecutable) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $pythonVersion = (& $pythonCommand.Source --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $pythonVersion -match '^Python 3\.11(\.|$)') {
            $pythonExecutable = $pythonCommand.Source
        }
    }
}
if (-not $pythonExecutable) {
    Write-Host 'Python 3.11 was not found. Install Python 3.11 and add it to PATH.' -ForegroundColor Red
    exit 2
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$temporaryInstaller = Join-Path $env:TEMP ("minimax_comfyui_installer_$([guid]::NewGuid().ToString('N')).py")
try {
    $archive = [System.IO.Compression.ZipFile]::OpenRead($resourcePath)
    try {
        $installerEntry = $archive.GetEntry('installer/install_minimax_comfyui.py')
        if (-not $installerEntry) {
            throw 'The resource ZIP does not contain the Windows installer core.'
        }
        $source = $installerEntry.Open()
        $destination = [System.IO.File]::Create($temporaryInstaller)
        try {
            $source.CopyTo($destination)
        }
        finally {
            $source.Dispose()
            $destination.Dispose()
        }
    }
    finally {
        $archive.Dispose()
    }
}
catch {
    if (Test-Path -LiteralPath $temporaryInstaller) {
        [System.IO.File]::Delete($temporaryInstaller)
    }
    Write-Host "Could not extract the installer from the resource ZIP: $_" -ForegroundColor Red
    exit 2
}

$commandArguments = @($pythonPrefix) + @($temporaryInstaller, '--resource-archive', $resourcePath) + $args
$installerExitCode = 1
try {
    & $pythonExecutable @commandArguments
    $installerExitCode = $LASTEXITCODE
}
finally {
    [System.IO.File]::Delete($temporaryInstaller)
}
exit $installerExitCode
