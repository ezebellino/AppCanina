# Lazuna — pendientes de administración y lanzamiento

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
