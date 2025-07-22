$version = Read-Host "Enter version number (format: x.x.x)"

. ".venv\Scripts\activate.ps1"

if ($version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Host "Error: Invalid version format. Please use x.x.x format." -ForegroundColor Red
    exit 1
}

Write-Host "Starting packaging process for MySekaiStorywriter version $version..." -ForegroundColor Cyan

if (Test-Path "main.dist") {
    Write-Host "Deleting existing main.dist folder..." -ForegroundColor Yellow
    Remove-Item -Path "main.dist" -Recurse -Force
}

Write-Host "Compiling application with Nuitka..." -ForegroundColor Green
pyside6-rcc app/resources/resources.qrc -o app/_resources_rc.py
nuitka --standalone --jobs=10 --windows-console-mode=disable --windows-icon-from-ico=app/resources/icons/logo.ico --include-data-dir=resources --enable-plugins=pyside6 --show-progress main.py

if (-not (Test-Path "main.dist\main.exe")) {
    Write-Host "Error: Nuitka compilation failed. main.exe not found." -ForegroundColor Red
    exit 1
}

Write-Host "Renaming executable file..." -ForegroundColor Yellow
Rename-Item -Path "main.dist\main.exe" -NewName "MySekaiStorywriter.exe"

if (-not (Test-Path "dist")) {
    New-Item -ItemType Directory -Path "dist" | Out-Null
}

$zipFileName = "dist\MySekaiStorywriter-v$version-win-x64.zip"

Write-Host "Compressing files to $zipFileName..." -ForegroundColor Green
& zip -r -9 $zipFileName "main.dist"

if (Test-Path $zipFileName) {
    $zipSize = (Get-Item $zipFileName).Length / 1MB
    Write-Host "Packaging complete! ZIP file size: $($zipSize.ToString('0.00')) MB" -ForegroundColor Cyan
    Write-Host "File location: $zipFileName" -ForegroundColor Cyan
} else {
    Write-Host "Error: Compression failed. ZIP file not generated." -ForegroundColor Red
    exit 1
}