# Respaldos y ensayo de recuperación

## Estado verificado el 2026-11-10

- Panel Railway, servicio `appcanina`, entorno production: **No backup schedule** y **No Backups**. El volumen persistente `/data` no equivale a un respaldo. No se modificó Railway.
- Se ensayó la copia local `Respaldos/respaldo-tu-veterinaria_2026-10-05_06-34-09.zip` en Docker, sin red, con el ZIP montado en solo lectura y sin montar ningún volumen real.
- SHA-256: `33554a17b980bbd1442453c578f907117cc1a643de5f534e3e1a5a92e01b0943`.
- Resultado: 17 entradas, 14 archivos de medios; integridad SQLite y claves foráneas correctas antes/después de migrar; migraciones, Django check, collectstatic y GET de ingreso mediante cliente Django (200) correctos.
- No incluye `.django_secret_key`. El ensayo usa una clave ficticia; no demuestra recuperación de la clave original, sesiones ni configuración SMTP. El ZIP no está cifrado. No subirlo a Git, chats o sitios públicos.
- Esta copia antigua **no prueba recuperación del estado actual de Railway**. No se validó visualmente cada foto, cada relación de negocio ni el arranque de Gunicorn restaurado.

## Repetir el ensayo local

Desde la raíz del repositorio, con una imagen local confiable construida del código actual (`docker build -t lazuna-security:0.8.5 .`). Ajustar únicamente la ruta del ZIP:

```powershell
docker run --rm --network none --read-only --cpus 2 --memory 1g --pids-limit 128 `
  --tmpfs /tmp:rw,size=512m --tmpfs /app/staticfiles:rw,size=128m `
  --mount "type=bind,source=C:\ProjectsZeqe\AppCanina\Respaldos\respaldo-tu-veterinaria_2026-10-05_06-34-09.zip,target=/backup.zip,readonly" `
  --mount "type=bind,source=C:\ProjectsZeqe\AppCanina\scripts\check_backup_restore.py,target=/drill.py,readonly" `
  --entrypoint python lazuna-security:0.8.5 /drill.py
```

El script solo escribe en almacenamiento temporal del contenedor. Rechaza rutas externas, enlaces simbólicos, colisiones y archivos mayores a los límites del ensayo (256 MiB descomprimidos, 100.000 entradas). La salida contiene categorías y cantidades, nunca registros o claves. No ejecuta el script de restauración destructiva ni el entrypoint de producción.

## Pendiente para cerrar el bloque

1. En Railway → servicio appcanina → Backups, revisar el costo mostrado y crear una copia actual; verificar que termine correctamente y registrar fecha/identificador.
2. Configurar frecuencia y retención adecuadas (propuesta: diaria y semanal), considerando el costo del almacenamiento. Verificar la programación guardada.
3. Ensayar una copia actual en un entorno aislado. No usar Restore sobre el servicio vivo: puede cambiar el volumen montado e interrumpir o retroceder producción. Preparar primero un destino separado y sin SMTP/push/red pública.
4. Guardar las copias externas cifradas y con acceso restringido; custodiar configuración y claves necesarias por separado en un gestor de secretos. Una copia ZIP simple no ofrece cifrado.

Los scripts `Crear-Respaldo.ps1` y `Restaurar-Respaldo.ps1` corresponden al Docker Compose local, no a Railway. La restauración existente borra datos locales antes de copiar: no usarla como prueba. Queda pendiente endurecerla con validación previa y recuperación ante fallos. No se modificaron esos scripts en este bloque.
