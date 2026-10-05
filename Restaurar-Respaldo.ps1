param(
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backupRoot = Join-Path $projectPath "Respaldos"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "appcanina-restore-$timestamp"
$appStopped = $false

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
        throw "Docker Desktop no está listo. Abrilo, esperá a que inicie y ejecutá la restauración de nuevo."
    }

    Write-Host "Elegí el archivo .zip creado con Crear-Respaldo." -ForegroundColor Cyan
    $backupPath = Read-Host "Pegá la ruta completa del respaldo"
    $backupFile = Get-Item -LiteralPath $backupPath -ErrorAction Stop
    if ($backupFile.Extension -ne ".zip") { throw "El archivo seleccionado debe ser un respaldo .zip." }

    New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null
    Expand-Archive -LiteralPath $backupFile.FullName -DestinationPath $temporaryRoot -Force
    $databaseFile = Join-Path $temporaryRoot "db.sqlite3"
    if (-not (Test-Path -LiteralPath $databaseFile)) {
        throw "El archivo no parece un respaldo válido de Tu Veterinaria: falta db.sqlite3."
    }

    Write-Host "La restauración reemplazará los datos actuales por los del respaldo elegido." -ForegroundColor Yellow
    $confirmation = Read-Host "Para continuar, escribí RESTAURAR"
    if ($confirmation -cne "RESTAURAR") {
        Write-Host "Restauración cancelada. No se modificó ningún dato." -ForegroundColor Yellow
        return
    }

    Write-Host "Primero se creará un respaldo automático de seguridad..." -ForegroundColor Cyan
    & (Join-Path $projectPath "Crear-Respaldo.ps1") -NoPause
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el respaldo de seguridad previo." }

    $containerId = (docker compose ps -aq appcanina).Trim()
    if (-not $containerId) { throw "No se encontró el contenedor de la aplicación." }

    docker compose stop appcanina
    if ($LASTEXITCODE -ne 0) { throw "No se pudo detener la aplicación." }
    $appStopped = $true
    docker compose run --rm --no-deps --entrypoint sh appcanina -c "rm -rf /data/*"
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar los datos para la restauración." }
    docker cp "$temporaryRoot\." "$containerId`:/data"
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron restaurar los datos." }

    docker compose start appcanina
    if ($LASTEXITCODE -ne 0) { throw "Los datos se restauraron, pero no se pudo reiniciar la aplicación automáticamente." }
    $appStopped = $false
    Start-Sleep -Seconds 3
    docker compose exec -T appcanina python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "Los datos se restauraron, pero no se pudieron aplicar las migraciones necesarias." }
    docker compose exec -T appcanina python manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Los datos se restauraron, pero Django informó un problema de configuración." }
    Write-Host "Restauración completada. La aplicación ya puede abrirse normalmente." -ForegroundColor Green
}
catch {
    Write-Host "No se pudo completar la restauración: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if ($appStopped) {
        docker compose start appcanina *> $null
    }
    Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Pause-IfNeeded
