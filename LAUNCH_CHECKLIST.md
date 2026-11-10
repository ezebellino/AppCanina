# Lazuna — pendientes de administración y lanzamiento

## Respaldos — verificación 2026-11-10

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
