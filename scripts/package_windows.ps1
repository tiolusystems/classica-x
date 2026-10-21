param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Find-FFmpegBinary([string]$Name) {
    # Chocolatey exposes small launch shims in its bin directory.  PyInstaller
    # must receive the actual FFmpeg executable, which is self-contained.
    if ($env:ChocolateyInstall) {
        $packages = Get-ChildItem (Join-Path $env:ChocolateyInstall 'lib') -Directory -Filter 'ffmpeg*' -ErrorAction SilentlyContinue |
            Sort-Object FullName
        foreach ($package in $packages) {
            $candidate = Join-Path $package.FullName "tools\ffmpeg\bin\$Name.exe"
            if (Test-Path -LiteralPath $candidate) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
    }

    $command = Get-Command $Name -ErrorAction Stop
    if ($command.Source -match '\\chocolatey\\bin\\') {
        throw "O comando $Name encontrado e um shim do Chocolatey, mas o binario real nao foi localizado."
    }
    return (Resolve-Path -LiteralPath $command.Source).Path
}

$ffmpeg = Find-FFmpegBinary 'ffmpeg'
$ffprobe = Find-FFmpegBinary 'ffprobe'
& $Python -m PyInstaller --noconfirm --clean --onefile --name ClassicaXExtractor scripts\extractor_entry.py
& $Python -m PyInstaller --noconfirm --clean --onedir --name ClassicaX --add-data "classica_x/web;classica_x/web" --add-binary "$ffmpeg;." --add-binary "$ffprobe;." scripts\x_entry.py
Copy-Item dist\ClassicaXExtractor.exe dist\ClassicaX\ClassicaXExtractor.exe -Force
& $Python scripts\smoke_windows_package.py --bundle dist\ClassicaX
