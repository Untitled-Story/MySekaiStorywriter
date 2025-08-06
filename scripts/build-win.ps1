$version = $(poetry version -s)

Write-Host "Starting packaging process for MySekaiStorywriter version $version..." -ForegroundColor Cyan

if (Test-Path "MySekaiStorywriter.dist") {
    Write-Host "Deleting existing MySekaiStorywriter.dist folder..." -ForegroundColor Yellow
    Remove-Item -Path "MySekaiStorywriter.dist" -Recurse -Force
}

Write-Host "Compiling application with Nuitka..." -ForegroundColor Green
poetry run pyside6-rcc app/resources/resources.qrc -o app/_resources_rc.py
poetry run nuitka --standalone --jobs=10 --windows-console-mode=attach --product-version=$version --file-description="A Scenario Editor for MySekaiStoryteller" --windows-icon-from-ico=app/resources/icons/logo.ico --include-data-dir=resources=resources --enable-plugins=pyside6,tk-inter --lto=yes --show-progress MySekaiStorywriter.py

if (-not (Test-Path "MySekaiStorywriter.dist\MySekaiStorywriter.exe")) {
    Write-Host "Error: Nuitka compilation failed. MySekaiStorywriter.exe not found." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "dist")) {
    New-Item -ItemType Directory -Path "dist" | Out-Null
}

$zipFileName = "dist\MySekaiStorywriter-v$version-win-x64.zip"

Write-Host "Compressing files to $zipFileName..." -ForegroundColor Green

Push-Location main.dist
zip -r -9 "..\$zipFileName" .
Pop-Location

if (Test-Path $zipFileName) {
    $zipSize = (Get-Item $zipFileName).Length / 1MB
    Write-Host "Packaging complete! ZIP file size: $($zipSize.ToString('0.00')) MB" -ForegroundColor Cyan
    Write-Host "File location: $zipFileName" -ForegroundColor Cyan
} else {
    Write-Host "Error: Compression failed. ZIP file not generated." -ForegroundColor Red
    exit 1
}