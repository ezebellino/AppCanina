# Lazuna — pendientes de administración y lanzamiento

## APK 0.8.16 disponible

Build único `9c83cd33-335e-4cfc-90a1-599cf12a6132` **FINISHED**, versionCode 5. APK: https://expo.dev/artifacts/eas/XbZaqlOyoDiOwmxPuqpg_FCagq67P9dUBC1Q-_u9nZE.apk

- [ ] Instalar como actualización y completar `mobile/PRUEBA-APK-0.8.16.md`. La compilación finalizada no confirma entrega física.

## Expo Push — 0.8.16

- [x] Firebase Android registrado, configuración incorporada, credencial FCM V1 existente en EAS verificada visualmente.
- [x] Cola, límites, tickets/recibos, reintentos y procesos supervisados preparados.
- [ ] Instalar el próximo APK y probar recepción física con teléfono bloqueado, apertura y cambio de cuenta.
- [ ] Confirmar receipt de Expo/FCM; no equivale a lectura. Extender push a adopciones/familia en otro bloque si se requiere.

Guía: mobile/EXPO-PUSH.md. No se envió una notificación real desde las pruebas.


## Avisos de búsquedas — 0.8.15

- [x] Novedad web y contador de Mis búsquedas; lectura privada compartida con app.
- [x] Correo para nuevas aprobaciones/rechazos, sin duplicar reintentos y sin perder respuesta ante fallo de envío.
- [ ] Confirmar recepción real del próximo correo de revisión y revisar la novedad en web/app. No se reenviaron respuestas anteriores.
- [ ] Verificar push físico con app cerrada y permisos habilitados; servicio robusto de push sigue pendiente. Sin nuevo build.

## Moderación de búsquedas — 0.8.14

- [x] Administrador staff sin superusuario: acceso a Revisar búsquedas y aprobación/rechazo; acceso de publicación oculto.
- [x] Colaboradores sin autoridad de moderación; permisos institucionales existentes conservados.
- [ ] Verificar con lazuna_admin el panel y una solicitud real pendiente. No se moderaron avisos reales desde las pruebas.

## Autocompletado de búsquedas web — 0.8.13

- [x] Datos y foto de animal vinculado, copia independiente del aviso y permisos verificados (70 pruebas Django y una Node).
- [ ] En el formulario web seleccionar un animal, revisar sus datos/foto y completar fecha y zona. No es necesario enviar un aviso ficticio en producción.
- Sin nuevo APK.

## Perfil y publicaciones web — 0.8.12

- [x] Accesos agrupados antes de los datos personales; Buscar condicionado por rol.
- [x] Solicitudes comunitarias de búsqueda con revisión previa, listado propio y corrección privada.
- [ ] Comprobar en teléfono el perfil web y enviar una búsqueda desde Publicar animal extraviado. La revisión del navegador confirmó los accesos en escritorio; no sustituye la prueba visual móvil.
- APK 0.8.11 conservado: incluye Pedir una búsqueda y Buscar animales. No se generó otro build.

## APK acumulado 0.8.11 disponible — 2026-11-11

Build único `27eb8a55-ffe8-4b1a-9fce-d90d5a97a54d` **FINISHED**, Android versionCode 4, perfil preview y firma existente. Fuente `a45bdca`. APK: https://expo.dev/artifacts/eas/fR7ojFo6RbhCJOOlXwP_KAC-yWzLSp-xVAWt80PpD8A.apk

- [x] Compatibilidad Expo y Doctor 17/17; compilación cloud finalizada.
- [ ] Instalar como actualización y completar `mobile/PRUEBA-APK-0.8.11.md`. No se declara validación física.
- Push robusto y limpieza DEMO pos-lanzamiento siguen pendientes.

## Revisión del paquete acumulado — 2026-11-11

Revisión técnica y regresiones completadas; dos ajustes de navegación corregidos. Evidencia y plan físico en `mobile/REVISION-PREBUILD.md`. El siguiente paso es decidir el único APK acumulado y ejecutar esa guía en teléfono. No se inició build en la revisión. Push robusto sigue aplazado.

## Novedades móviles — 0.8.10

- [x] Bandeja Todas/Sin leer paginada, contador visible, apertura del aviso/solicitud correspondiente y lectura persistente.
- [x] Actividad de adopciones del adoptante y del refugio; búsquedas públicas y respuestas privadas a solicitudes propias.
- [x] 28 pruebas Django y exportación Android. No marca leída una actualización posterior a la que se abrió.
- [ ] Próximo APK: verificar dos cuentas, novedades leídas/no leídas, solicitud institucional, respuesta de búsqueda rechazada, vuelta a primer plano, falta de red y disposición con texto grande.
- Sin push nuevo ni build. Revisar el paquete acumulado antes de decidir el próximo APK.

## Animal encontrado — 0.8.9

- [x] Cierre web desde tarjeta/detalle con confirmación, permisos por autor/ficha institucional/moderación, conservación del historial e idempotencia.
- [x] API y cliente móvil preparados, 24 pruebas Django y exportación Android.
- [ ] Próximo APK: confirmar/cancelar cierre, doble toque, falta de red, aviso ajeno y consulta en Encontrados. Sin build por este bloque.
- No modificar Alelí ni otros avisos reales como parte de las pruebas: el usuario confirma el cierre desde su cuenta autorizada.

## Acumulado tras 0.8.5: bandeja del refugio

- [x] En Mi actividad, responsables de refugios verificados pueden abrir Solicitudes recibidas, filtrar nuevas/visitas, paginar, actualizar estado/mensaje y aceptar o rechazar visitas.
- [x] Datos limitados a instituciones gestionadas; sin permisos globales por ser staff. Revocación y verificación comprobadas en cada operación. Protección frente a cambios simultáneos con versión de la solicitud.
- [ ] Validación física en el próximo APK acumulado: dos responsables, dos refugios, adoptante, actualización, cambios sin red y cambio de cuenta. No generar build por este bloque.

## Notificaciones push — decisión aplazada por el usuario

Primero completar las features anteriores. En una integración futura decidir Expo/Firebase frente a una opción abierta (por ejemplo ntfy). Comparar mantenimiento: actualizaciones, seguridad/accesos, disponibilidad, monitoreo, respaldos, costos del servidor e integración Android/iOS. No migrar ni activar servicios ahora.

El control futuro deberá incluir cola durable, límite global de envío por proyecto, reintentos espaciados con variación aleatoria, comprobantes de entrega, baja de tokens inválidos y prevención de duplicados. El envío actual es básico; no confundir aceptación del proveedor con entrega en teléfono. La bandeja general móvil ya está preparada en 0.8.10; su validación física queda para el próximo APK.

## Acumulado tras 0.8.5: visitas de adopción en el APK

- [x] API privada y pantalla del adoptante: solicitar visita, consultar respuesta/indicaciones y abrir ubicación aceptada en Maps.
- [x] 20 pruebas Django y exportación Android; ver `RELEASING.md` 0.8.7.
- [ ] Prueba física al generar el próximo APK acumulado, junto con mapas de extraviados. No iniciar build por este bloque.
- [x] Bandeja institucional preparada en fuente (ver bloque superior); la web continúa disponible.
- [ ] Push real (aplazado; proveedor por decidir): revisar credenciales y probar entrega en teléfono. El código usa Expo Notifications; presencia del código no demuestra entrega. Notificaciones de visitas por push todavía no implementadas (correos existentes sí).

Confirmación del usuario (2026-11-10): vínculo familiar de mascotas y correos respectivos funcionan en uso real.

## Acumulado tras 0.8.5: mapa móvil de extraviados

Backend 0.8.6 y cliente preparados para última ubicación aproximada y área estimativa entre observaciones públicas del mismo animal. Validación automatizada y visual HTML registrada en `RELEASING.md`. No se generó APK; probar WebView/Maps en teléfono, red ausente, avisos sin GPS, múltiples reportes y cambios rápidos de aviso al distribuir el próximo paquete.

## APK 0.8.5 disponible — 2026-11-10

Build preview Android `2b23795a-bbd5-462a-9e6e-0bdf7f3f24d2` FINISHED, versionCode 3. Un único build nuevo, con firma e identidad existentes. Validados 16 tests Node, Expo Doctor 17/17, compatibilidad de dependencias y exportación Android. Archivo EAS inspeccionado sin respaldos, adjuntos ni temporales. Enlace en `RELEASING.md`. La distribución ya está disponible; instalación y pruebas físicas siguen pendientes según `mobile/PRUEBA-APK-0.8.5.md`. Las referencias históricas a no generar APK no describen este estado actual. YubiKey/automatización Proxmox pospuestos por el titular; eliminación DEMO después del lanzamiento.

## Respaldos — verificación 2026-11-10

**Recuperación cifrada comprobada:** el titular descifró la copia desde D: y se probó el ZIP recuperado en Docker aislado. Exit 0, SQLite/claves foráneas íntegros, migraciones/check/collectstatic correctos, login HTTP 200 y siete archivos de medios. Cadena completa de descarga/cifrado/copia/descifrado/ensayo verificada; las referencias posteriores a restauración pendiente quedan superadas. Aún pendientes: custodia independiente de clave, automatización SSH/traslado a VM y tratamiento de ZIP sin cifrar. No se modificó producción ni se borraron archivos.

**Primera descarga cifrada real completada:** el titular configuró su clave con prueba de recuperación y descargó `lazuna-20261110T074502Z-888bf2fb.zip.age`. Se verificó SHA-256 idéntico en notebook, D: y archivo de suma. Pendiente descifrado y restauración aislada de esta copia real; no confundir con la prueba sintética de configuración o la restauración del ZIP anterior. Continúan pendientes custodia independiente de la clave, automatización y ZIP antiguos sin cifrar.

**Cifrado incorporado al descargador:** age cifra en streaming antes de escribir en la notebook; la copia externa recibe `.zip.age`. Seis pruebas sintéticas correctas, incluida recuperación y rechazo de manipulación. La configuración inicial pide al titular una contraseña local y prueba la clave privada cifrada. Pendientes: ejecutar `Descargar-Respaldo-Railway.ps1 -ConfigurarCifrado`, custodiar la clave cifrada por separado, hacer una descarga real cifrada y probar su recuperación. Los ZIP anteriores no se modificaron y siguen sin cifrar. No hubo cambios de producción ni APK.

**Avance confirmado:** primera descarga real `lazuna-20261110T072508Z-cd180730.zip` en notebook y disco `SEGATE - Zeqe (D:)`, con SHA-256 idéntico. Restauración aislada del ZIP local correcta: integridad SQLite/claves foráneas, migraciones, check, collectstatic y login HTTP 200; siete archivos de medios. No incluye secretos de entorno. Pendientes: automatización desatendida, cifrado/custodia de secretos y traslado a VM Proxmox. Ver evidencia en `BACKUPS.md`; las referencias siguientes a primera descarga pendiente corresponden al estado previo.

Actualización: el titular eligió notebook → VM en Proxmox + disco externo y rechazó los snapshots pagos. Formulario Railway descartado sin guardar. Descargador SSH portable preparado y probado con datos sintéticos; primera descarga de producción y programación diaria pendientes del desbloqueo de la clave SSH en una terminal del titular. La ejecución sin interacción falla de forma segura; no se creó una tarea automática fallida ni se descargaron datos reales. Ver `BACKUPS.md` y `Descargar-Respaldo-Railway.ps1`.

Railway muestra **sin programación y sin copias** en Backups. Ensayo aislado de la copia local del 5 de octubre: integridad, migraciones y pantalla de ingreso correctas, con 14 archivos de medios. No demuestra recuperación de producción actual. Ver `BACKUPS.md` para evidencia, comando reproducible y pendientes de copia reciente, programación, cifrado y restauración aislada. No hubo cambios de datos ni nuevo APK.

## Comprobación de acceso — 2026-11-09

- Confirmado en producción: la sesión abierta pertenece a `ezebellino` y recibe 403 al consultar `/organizaciones/validaciones/`. Actualmente no puede validar instituciones.
- El panel de plataforma exige `is_staff`. El grupo `Administrador` usado por responsables institucionales no concede por sí solo ese permiso.
- Consulta SSH inicial del titular: `ezebellino` es colaborador sin staff; `demo_veterinaria_admin` tenía staff; `demo_veterinaria` solo tiene el grupo institucional Administrador. La consulta no encontró superusuarios.
- El titular configuró SSH y confirmó acceso al Panel de plataforma y Validar instituciones con la nueva cuenta `lazuna_admin`, creada con staff y sin superusuario. Correo elegido: Gmail personal del titular; Hostinger se conserva como remitente. Los avisos de nuevos registros requieren verificación independiente.
- Esta comprobación no modificó cuentas, roles ni credenciales.

## Próxima etapa administrativa

- Cuenta exclusiva `lazuna_admin` creada y acceso confirmado por el titular. Mantener `ezebellino` para el uso cotidiano.
- Retiro confirmado por salida SSH compartida por el titular: `demo_veterinaria_admin` tiene staff y superusuario desactivados. El inventario posterior devuelve únicamente `lazuna_admin`, activo con staff y sin superusuario. Cuenta DEMO y datos conservados.
- Revisión 2026-11-09: los comandos actuales `seed_community_demo`, `seed_operational_demo` y `setup_roles` no asignan staff/superusuario al DEMO. Se configuró explícitamente `SEED_COMMUNITY_DEMO_ON_START=0` en Railway para impedir la carga automática al reiniciar. No se ejecutaron seeds ni borrados.
- Revisar que solo las cuentas designadas puedan validar veterinarias y refugios. No confundir los permisos de gestión de una institución con los de plataforma.

## Limpieza final después del lanzamiento

Por instrucción del titular, borrar las cuentas DEMO y los datos ficticios al finalizar el lanzamiento, no durante las pruebas actuales.

- Inventariar cuentas, instituciones, animales, publicaciones, solicitudes, permisos, notificaciones y archivos DEMO.
- Separar datos exclusivamente ficticios de vínculos con usuarios y animales reales; preservar estos últimos.
- Preparar un respaldo y una lista concreta de lo que se eliminará antes de ejecutar la limpieza.
- Deshabilitar cualquier carga automática de demostración para que un despliegue no vuelva a crearla.
- Comprobar que el catálogo público no conserve datos ficticios y que las cuentas reales mantengan sus accesos.

No se ejecutó ninguna eliminación ni desactivación.

## Conciliación del informe de seguridad original

Informe de la revisión `19f19e1` (scan `b5b5179b-ec86-4799-9cf4-f9404d814bec`), contrastado con el código y los cambios publicados hasta 0.8.1. Esta tabla no modifica ni reabre el informe sellado y no equivale a una auditoría nueva de toda la aplicación.

| Hallazgo original | Estado y evidencia |
| --- | --- |
| 1. Agenda de peluquería entre instituciones | Corrección de servidor publicada en 0.5.3. Pruebas de agenda, edición, estado, selectores y superposición en `patients/test_tenant_boundaries.py`. |
| 2. Vinculación de contactos concede animales ajenos | Corrección publicada en 0.5.3: concesión explícita por paciente en `patients/ownership.py`, migración 0010 y pruebas de vínculos cruzados. |
| 3. Recuperación no invalida sesiones móviles | Protección de servidor publicada en 0.8.0: huella de contraseña, vencimiento y revocación. `lost_pets/test_session_security.py`. El botón de cierre remoto del cliente requiere el próximo APK. |
| 4. Búsquedas y resúmenes comerciales cruzados | Corrección publicada en 0.5.3, pruebas de búsqueda, ventas e historial delimitados por institución. |
| 5. Avistamientos ocultos expuestos | Corrección publicada en 0.8.1: visibilidad compartida, filtros de notificaciones/push y medios protegidos. `lost_pets/test_hidden_visibility.py`. |
| 6. Cobro vinculado enumera contactos ajenos | Corrección publicada en 0.5.3: `sale_create` conserva querysets acotados en todos los formularios, con prueba de cobro vinculado. |
| 7. Retiro de consentimiento no revoca acceso temporal | Corrección publicada en 0.6.0: `TravelAccessRequest.is_active` revalida consentimiento, credencial, institución y pertenencia; pruebas en `patients/test_veterinary_authorizations.py`. |
| 8. Credenciales DEMO compartidas con autoridad | Generador corregido en 0.8.3: altas sin contraseña utilizable y sin revelar claves; conserva claves privadas al repetir el seed. Comando interactivo `secure_demo_accounts --apply --admin lazuna_admin` probado para rotar las cuatro cuentas conocidas, retirar privilegios de plataforma y revocar sesiones móviles/push. El titular confirmó haber cambiado las claves en producción; no se inspeccionaron sus valores. Conserva actividad, roles institucionales y datos. Eliminación después del lanzamiento. |
| 9. Logout conserva contraseña e historiales | Corregido en fuente móvil (0.8.0), pruebas Node y exportación local correctas. Pendiente distribución y prueba física con nuevo APK; el instalado no recibió esa limpieza. |

### Seguimientos adicionales del informe

- Política de contraseñas: se confirmó `AUTH_PASSWORD_VALIDATORS=[]`, también afectaba registro web/móvil porque usan `UserCreationForm`. Corregido en 0.8.2 con política compartida para altas, recuperación y configuración inicial; no modifica contraseñas existentes. Ver pruebas y estado de publicación en `RELEASING.md`.
- Límites contra intentos abusivos: implementados en 0.8.4 para login web/admin/móvil y recuperación web, con contadores SQLite persistentes, ventanas temporales y claves HMAC por conexión/identificador. Ver límites, validación y alcance en `RELEASING.md`; no sustituye protección de red contra ataques volumétricos.
- Dependencias: servidor corregido en 0.8.5 (Pillow 13/Python 3.13, conjunto fijado sin avisos devueltos por OSV). Fuente móvil migrada a Expo 54/Metro 0.83.8, glob 14.0.4 y minimatch 11.0.5; sin image-size. Auditoría npm final: cero críticos/altos/moderados, 12 paquetes bajos por un aviso de deepmerge sin corrección publicada. Pendiente distribución y prueba física del próximo APK; el instalado conserva SDK 53. Ver evidencia, overrides y límites en `RELEASING.md`. No se auditó el sistema operativo del contenedor ni las dependencias nativas Gradle/CocoaPods.
- Operación: pendiente verificar respaldo/restauración y permisos/cifrado de copias, exposición inicial del primer administrador y configuración de red local. La instancia actual ya tiene administrador, pero eso no prueba seguridad del primer arranque de otras instalaciones.
- El gitlink legado `pet_grooming_appointments` no estaba disponible para el informe original; mantener esa limitación hasta verificar su relevancia y contenido.

No se requieren builds para revisar estos puntos de servidor/operación. Preparar un único APK acumulado cuando los controles previos estén completos; probar login, recuperación, expiración, logout sin red, cambio de cuenta, biometría y notificaciones en teléfono real.

## Acumulado para el próximo APK — 0.8.17

- Ícono Android de notificaciones: huella monocroma blanca, fondo transparente. Preparado y verificado en configuración; falta comprobar visualmente en teléfono tras el próximo build autorizado.
- Anuncios de adopción: bloque opcional de colaboración al refugio con alias seleccionable y botón Copiar alias. Web/backend publicables sin build; móvil preparado.
- Prueba manual: desde Mi Institución guardar alias y mensaje, abrir una adopción publicada del refugio verificado y copiar el alias. Vaciar el alias oculta el bloque. No requiere hacer una transferencia.
- El usuario confirmó recepción real de push en APK 0.8.16. No generar otro APK por estos cambios aislados.

## Acumulado para el próximo APK — 0.8.18

- Archivo personal de solicitudes de adopción: finalizar como Adopción concretada o No continuó, archivar, abrir Archivadas y restaurar. Verificar también desde el refugio; ninguna acción oculta la solicitud a otra cuenta.
- Una respuesta nueva o reapertura devuelve la solicitud a la bandeja. Archivo no equivale a borrar ni cambia el estado de la adopción.
- No se generó otro build. Mientras se usa APK 0.8.16, consultar/restaurar archivos desde la web.

## Acumulado para el próximo APK — 0.8.19

- Animación al archivar: tarjeta plegada, sobre y archivador. Se ejecuta tras confirmación del servidor; sin movimiento si está activado Reducir movimiento. Pendiente de prueba física en el próximo APK autorizado.
