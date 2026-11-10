param([string]$DiscoExterno, [switch]$ConfigurarCifrado)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($ConfigurarCifrado) {
    python scripts/backup_encryption.py setup
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo configurar el cifrado.' }
    return
}
$backupArguments = @('scripts/download_railway_backup.py')
if ($DiscoExterno) { $backupArguments += @('--copy-to', $DiscoExterno) }
Write-Host 'Descarga privada desde Railway. Si SSH pide la frase de la clave, ingresala en esta terminal.'
Write-Host 'No cierres la ventana hasta ver Verified encrypted local backup.'
python @backupArguments
if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar el respaldo. Las copias anteriores se conservan.' }
