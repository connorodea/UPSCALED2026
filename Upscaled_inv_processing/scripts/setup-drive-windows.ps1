$ErrorActionPreference = 'Stop'

$repoDefault = (Resolve-Path "$PSScriptRoot\.." ).Path
$repoDir = Read-Host "Repo path [$repoDefault]"
if ([string]::IsNullOrWhiteSpace($repoDir)) { $repoDir = $repoDefault }

Write-Host "Example Google Drive path:" -ForegroundColor Cyan
Write-Host "  C:\\Users\\<user>\\Google Drive\\Shared drives\\Upscaled" -ForegroundColor Cyan
$driveRoot = Read-Host "Google Drive base folder"
if ([string]::IsNullOrWhiteSpace($driveRoot)) {
  Write-Host "Drive root is required." -ForegroundColor Red
  exit 1
}

$intakeDir = Join-Path $driveRoot "Upscaled_Photo_Intake"
$outputDir = Join-Path $driveRoot "Upscaled_Photos"
New-Item -ItemType Directory -Force -Path $intakeDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$binDir = Join-Path $env:USERPROFILE "bin"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

$upscaledCmd = Join-Path $binDir "upscaled.cmd"
@"
@echo off
set "repo=$repoDir"
cd /d "%repo%"
node "%repo%\\dist\\index.js" %*
"@ | Set-Content -Path $upscaledCmd -Encoding ASCII

$photosCmd = Join-Path $binDir "upscaled-photos.cmd"
@"
@echo off
start "" "$outputDir"
"@ | Set-Content -Path $photosCmd -Encoding ASCII

$intakeCmd = Join-Path $binDir "upscaled-intake.cmd"
@"
@echo off
start "" "$intakeDir"
"@ | Set-Content -Path $intakeCmd -Encoding ASCII

[Environment]::SetEnvironmentVariable("PHOTO_INTAKE_DIR", $intakeDir, "User")
[Environment]::SetEnvironmentVariable("PHOTO_OUTPUT_DIR", $outputDir, "User")

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
  $newPath = if ([string]::IsNullOrEmpty($userPath)) { $binDir } else { "$userPath;$binDir" }
  [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

Write-Host "Done." -ForegroundColor Green
Write-Host "- Intake: $intakeDir"
Write-Host "- Output: $outputDir"
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "1) Open a new terminal"
Write-Host "2) cd $repoDir; npm install; npm run build"
Write-Host "3) run: upscaled"
