$ErrorActionPreference = "Stop"
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Falta instalar Docker Desktop. Descargalo desde https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Read-Host "Presioná Enter para cerrar"
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Abrí Docker Desktop y esperá a que indique que está listo. Después ejecutá este archivo de nuevo." -ForegroundColor Yellow
    Read-Host "Presioná Enter para cerrar"
    exit 1
}

docker compose up --build -d
Start-Sleep -Seconds 3
Start-Process "http://localhost:8000"
