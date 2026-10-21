param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
$ffprobe = (Get-Command ffprobe -ErrorAction Stop).Source
& $Python -m PyInstaller --noconfirm --clean --onefile --name ClassicaXExtractor scripts\extractor_entry.py
& $Python -m PyInstaller --noconfirm --clean --onedir --name ClassicaX --add-data "classica_x/web;classica_x/web" --add-binary "$ffmpeg;." --add-binary "$ffprobe;." scripts\x_entry.py
Copy-Item dist\ClassicaXExtractor.exe dist\ClassicaX\ClassicaXExtractor.exe -Force
