# Respaldos y ensayo de recuperación

## Descargas cifradas con age — implementación 2026-11-10

Las nuevas descargas exigen un destinatario age válido antes de conectar a Railway. El flujo decodificado se entrega por una tubería a age y solo se escribe el resultado `.zip.age`; no se crea un ZIP temporal sin cifrar en la notebook. Se comprueba el tamaño y SHA-256 del flujo original, el código de salida de SSH/age y la suma del archivo cifrado. La copia externa recibe ese mismo archivo cifrado y se verifica por SHA-256. No hay alternativa automática sin cifrado si falta la configuración o falla age.

El servidor comprueba SQLite y CRC del ZIP antes de transmitir; la comprobación local completa del manifiesto se hace al descifrar. El ZIP temporal del servidor sigue sin cifrar y se elimina al terminar normalmente. No equivale a cifrar el volumen de Railway ni los discos locales, ni impide que el sistema operativo pagine memoria al disco.

### Configuración inicial, una sola vez

```powershell
C:\ProjectsZeqe\AppCanina\Descargar-Respaldo-Railway.ps1 -ConfigurarCifrado
```

Elegir una contraseña fuerte en la terminal y conservarla en un gestor. La herramienta crea una clave privada en memoria, la guarda únicamente cifrada mediante age y pide comprobar su recuperación antes de publicar la configuración. No usa contraseñas en argumentos, variables de entorno ni código. No reemplaza claves existentes.

Archivos de configuración: `C:\Users\ezebe\.config\lazuna-backup\identity.age` (clave privada cifrada) y `recipient.txt` (clave pública). Guardar una copia de `identity.age` en un lugar separado y protegido; guardar su contraseña por separado. Para recuperar se necesitan **ambos**. Perderlos puede hacer irrecuperables las copias. No basta con memorizar la contraseña si se pierde el archivo de clave.

Después de configurar:

```powershell
C:\ProjectsZeqe\AppCanina\Descargar-Respaldo-Railway.ps1 -DiscoExterno 'D:\Respaldos-Lazuna'
```

La contraseña de recuperación no se pide para descargar. La frase SSH todavía puede pedirse: es una clave diferente y la automatización SSH sigue pendiente. El mensaje de éxito local es `Verified encrypted local backup`.

### Recuperar un ZIP explícitamente

Desde la raíz del repositorio, reemplazando el nombre de ejemplo por la copia real:

```powershell
python scripts/backup_encryption.py decrypt --input 'Respaldos\Railway\COPIA.zip.age' --output 'Respaldos\Railway\recuperacion.zip'
```

Solicita la contraseña de la clave privada cifrada. Solo publica el ZIP tras descifrado autenticado y comprobación del manifiesto. El ZIP de recuperación queda **sin cifrar**: usarlo en el ensayo aislado y custodiarlo como dato sensible. El comando no restaura ni sobrescribe producción y rechaza un destino ya existente.

### Herramienta y evidencia

age 1.3.2 portable para Windows amd64 instalado en `.backup-tools/v1.3.2/age` (ignorado por Git). Paquete oficial: https://github.com/FiloSottile/age/releases/download/v1.3.2/age-v1.3.2-windows-amd64.zip; SHA-256 verificado contra metadatos de la publicación oficial: `f48d8f8f9ebe903ab5027ed067652f2cc1db94bc206976430133b905dcd8e8c7`. En otra máquina instalar age/age-keygen de su distribución oficial y ponerlos en PATH. Los binarios no viajan con el repositorio.

Seis pruebas sintéticas pasaron: exportación de SQLite/WAL activo, medios y clave oculta ficticia; rechazo de transferencia incompleta/corrupta y base inexistente; cifrado real con age y recuperación con manifiesto válido; rechazo de alteración del cifrado y destinatario inválido. Sin configuración, el descargador abortó antes de conectar. No se generó una clave real del titular ni una nueva descarga de producción en esta etapa: pendientes de su configuración interactiva y ensayo real.

Los ZIP anteriores en notebook y D: **siguen sin cifrar y no se borraron**. Las secciones anteriores sobre respaldo sin cifrado describen ese estado histórico. Cifrar las próximas descargas no protege retroactivamente esos archivos ni garantiza borrado seguro en discos sin cifrar.

## Primera descarga de producción verificada — 2026-11-10

El titular ejecutó la descarga e ingresó la frase SSH únicamente en su terminal. Se confirmó `Verified local backup` y `Verified external copy completed` para `lazuna-20261110T072508Z-cd180730.zip`.

- Copia local: `C:\ProjectsZeqe\AppCanina\Respaldos\Railway`.
- Segunda copia: `D:\Respaldos-Lazuna`, volumen NTFS `SEGATE - Zeqe`, identificado previamente.
- Ambas copias y el archivo de suma coinciden: SHA-256 `cd3b8eb5f1556f62669454d7ccd6f5f3fbd3da0b13427e834b9a790244bda537`.
- Restauración del ZIP local en `lazuna-security:0.8.5`, sin red, raíz de solo lectura, ZIP de solo lectura y almacenamiento temporal: exit 0. SQLite íntegro y claves foráneas válidas antes/después de migrar; migraciones, Django check, collectstatic y GET del login mediante cliente Django (200) correctos. Nueve entradas, siete archivos de medios.
- No contiene `.django_secret_key`; la prueba usa una clave ficticia. No demuestra recuperación de los secretos de entorno, SMTP, sesiones originales, Gunicorn ni cada flujo funcional. Los medios y la base no constituyen una instantánea atómica durante cambios concurrentes.

Primera copia real y ensayo aislado completados. Sigue pendiente automatización sin interacción, custodia de secretos/cifrado y traslado a una VM de Proxmox. No se modificó producción ni se creó un APK. Las menciones a descarga pendiente más abajo describen el estado anterior a esta verificación.

## Destino elegido: notebook, servidor personal y disco externo

El titular rechazó los snapshots pagos de Railway. El 2026-11-10 se descartó el formulario sin guardar y se confirmó nuevamente `No backup schedule` / `No Backups`. El destino inmediato es esta notebook; la migración a una VM del servidor Proxmox y la segunda copia al disco externo quedan pendientes de disponibilidad y rutas. No se creó una tarea automática todavía.

### Descargar desde producción en la notebook

En una terminal PowerShell propia:

```powershell
Set-Location C:\ProjectsZeqe\AppCanina
.\Descargar-Respaldo-Railway.ps1
```

SSH puede pedir la frase de la clave privada. Ingresarla solo en esa terminal; no guardarla en scripts, variables, tareas ni chats. El proceso tiene un máximo de quince minutos. La salida `Verified local backup` confirma ZIP completo y sumas verificadas, no una restauración ya probada.

Destino: `C:\ProjectsZeqe\AppCanina\Respaldos\Railway`. Cada ejecución genera nombre UTC único, ZIP y suma SHA-256; no sobrescribe ni elimina copias anteriores. `Respaldos/` está excluido de Git. Para el disco externo, indicar una carpeta existente, una vez confirmada su letra:

```powershell
.\Descargar-Respaldo-Railway.ps1 -DiscoExterno 'E:\Respaldos-Lazuna'
```

`E:` es solo un ejemplo, no un disco detectado. La segunda copia se publica tras comparar SHA-256. Si falla el disco externo después de la descarga, la copia local válida permanece.

### Contenido, seguridad y límites

- Usa la CLI autenticada para resolver el destino SSH actual y OpenSSH con verificación estricta del servidor, sin cambiar claves ni permisos. La clave existente ya tiene el servidor en known_hosts. En un servidor nuevo habrá que verificar su huella antes de conectar.
- Crea una copia coherente de SQLite mediante su API de backup (incluye transacciones confirmadas aunque haya WAL), reúne `media/` y `.django_secret_key` si existe; no descarga variables de entorno. Genera un manifiesto de sumas por archivo y comprueba integridad SQLite. Solo escribe temporales en `/tmp` remoto; no modifica `/data`, no reinicia el servicio ni restaura nada.
- La base tiene un punto consistente, pero los medios se recorren después: no es una instantánea atómica de base y fotos mientras hay actividad. Rechaza archivos que cambian durante su lectura y enlaces simbólicos. Para una recuperación estricta, coordinar una ventana sin cambios y comprobar vínculos de medios al restaurar.
- ZIP **sin cifrado** en reposo. SSH cifra el transporte. Guardarlo en almacenamiento cifrado y restringido (BitLocker o equivalente); no compartirlo. La custodia de secretos de entorno y su recuperación se resuelven por separado. El traslado al disco externo/servidor debe conservar esta protección.
- Evita el producto pago de snapshots, pero descargar datos puede consumir transferencia del plan Railway. No se promete costo total cero.

### Automatización y traslado a Proxmox

`python scripts/download_railway_backup.py --unattended` permite ejecución sin preguntas, pero requiere una clave disponible en un agente SSH y una sesión CLI válida. La prueba real del 2026-11-10 falló de forma segura por `no-ssh-key-offered`: no hay agente SSH activo y la clave requiere desbloqueo. No se guardó ningún ZIP incompleto ni se presentó esa prueba como respaldo exitoso.

Una vez verificada una primera descarga real: probar su restauración con el contenedor aislado descrito abajo; luego configurar una tarea diaria en la notebook, considerando que debe estar encendida y conectada. No crear una tarea que falle diariamente por autenticación. Al trasladar a Proxmox, usar una VM Linux de aplicaciones, no instalar el proceso en el host hipervisor. Los dos scripts Python son portables; requieren Python, Railway CLI y OpenSSH. Configurar allí autenticación, almacenamiento protegido, horario y prueba real antes de retirar la tarea de la notebook. No se configuró ni accedió al servidor Proxmox en este bloque.

Validación local: cuatro pruebas nuevas cubren copia con SQLite/WAL activo, medios y clave oculta ficticia, transferencia cortada/corrupta y ausencia de base sin crear una nueva. Descarga real pendiente de desbloqueo SSH por el titular. No hay programación automática activa ni nuevo APK.

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

**Plan anterior, reemplazado por la decisión de almacenamiento propio indicada arriba.** No activar snapshots pagos sin nueva autorización. Los pasos siguientes se conservan como referencia de la alternativa Railway, no como tareas vigentes.

1. En Railway → servicio appcanina → Backups, revisar el costo mostrado y crear una copia actual; verificar que termine correctamente y registrar fecha/identificador.
2. Configurar frecuencia y retención adecuadas (propuesta: diaria y semanal), considerando el costo del almacenamiento. Verificar la programación guardada.
3. Ensayar una copia actual en un entorno aislado. No usar Restore sobre el servicio vivo: puede cambiar el volumen montado e interrumpir o retroceder producción. Preparar primero un destino separado y sin SMTP/push/red pública.
4. Guardar las copias externas cifradas y con acceso restringido; custodiar configuración y claves necesarias por separado en un gestor de secretos. Una copia ZIP simple no ofrece cifrado.

Los scripts `Crear-Respaldo.ps1` y `Restaurar-Respaldo.ps1` corresponden al Docker Compose local, no a Railway. La restauración existente borra datos locales antes de copiar: no usarla como prueba. Queda pendiente endurecerla con validación previa y recuperación ante fallos. No se modificaron esos scripts en este bloque.
