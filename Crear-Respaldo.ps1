param(
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backupRoot = Join-Path $projectPath "Respaldos"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFile = Join-Path $backupRoot "respaldo-tu-veterinaria_$timestamp.zip"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "appcanina-backup-$timestamp"
$temporaryData = Join-Path $temporaryRoot "datos"
$exitCode = 0

function Pause-IfNeeded {
    if (-not $NoPause) { Read-Host "Presioná Enter para cerrar" }
}

try {
    Set-Location $projectPath
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "No se encontró Docker Desktop. Instalalo y volvé a intentarlo."
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop no está listo. Abrilo, esperá a que inicie y ejecutá el respaldo de nuevo."
    }

    New-Item -ItemType Directory -Force -Path $backupRoot, $temporaryData | Out-Null
    $containerId = (docker compose ps -aq appcanina).Trim()
    if (-not $containerId) {
        docker compose up -d appcanina
        if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar la aplicación para crear el respaldo." }
        Start-Sleep -Seconds 3
        $containerId = (docker compose ps -aq appcanina).Trim()
    }
    if (-not $containerId) { throw "No se encontró el contenedor de la aplicación." }

    Write-Host "Preparando un respaldo seguro. La aplicación se detendrá solo unos segundos..." -ForegroundColor Cyan
    docker compose stop appcanina
    if ($LASTEXITCODE -ne 0) { throw "No se pudo detener la aplicación." }

    try {
        docker cp "$containerId`:/data/." $temporaryData
        if ($LASTEXITCODE -ne 0) { throw "No se pudieron copiar los datos de la aplicación." }
        Compress-Archive -Path (Join-Path $temporaryData "*") -DestinationPath $backupFile -CompressionLevel Optimal
        Write-Host "Respaldo creado correctamente:" -ForegroundColor Green
        Write-Host "  $backupFile" -ForegroundColor Green
        Write-Host "Copiá este archivo a un pendrive o a otra ubicación segura." -ForegroundColor DarkGray
    }
    finally {
        docker compose start appcanina | Out-Null
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
catch {
    $exitCode = 1
    Write-Host "No se pudo crear el respaldo: $($_.Exception.Message)" -ForegroundColor Red
}

Pause-IfNeeded
if ($exitCode -ne 0) {
    throw "La creación del respaldo no se completó."
}
