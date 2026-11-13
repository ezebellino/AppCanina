# Prueba Android 0.8.16 — Expo Push

Build autorizado único: 9c83cd33-335e-4cfc-90a1-599cf12a6132. versionCode 5, preview, firma existente. Fuente c0589356945efdac8d33d24cdcc9245926ceefab. Incluye Firebase Android y apertura de bandeja al tocar push. Ver EXPO-PUSH.md para operación del servidor y límites.

Estado EAS verificado: **FINISHED**. APK: https://expo.dev/artifacts/eas/XbZaqlOyoDiOwmxPuqpg_FCagq67P9dUBC1Q-_u9nZE.apk

## Primera prueba

1. Instalar como actualización sobre Lazuna; no desinstalar para esta prueba.
2. Iniciar sesión personal. Menú → Mi teléfono y alertas → Activar alertas en este teléfono. Autorizar notificaciones y comprobar el mensaje de registro correcto.
3. Bloquear el teléfono, sin forzar la detención de la aplicación desde Ajustes Android.
4. Coordinar una revisión real de una búsqueda de esa cuenta. No aprobar/rechazar avisos reales solo para repetir pruebas ni crear búsquedas públicas ficticias. La primera revisión posterior al registro del teléfono debe generar novedad web/app, correo y envío push.
5. Comprobar que el aviso aparece en pantalla bloqueada y que al tocarlo abre la bandeja de la cuenta correcta. Abrir la novedad y verificar lectura.

## Verificaciones posteriores

- Probar con la app abierta y en segundo plano, permiso denegado, red temporalmente ausente y cambio/cierre de sesión. La cuenta cerrada no debe recibir nuevos envíos dirigidos a su sesión anterior; un aviso ya entregado al sistema operativo puede permanecer en la bandeja del teléfono.
- Revisar push_status en Railway: ticket significa aceptado por Expo; confirmed/provider_accepted indica aceptación de FCM/APNs, no recepción física garantizada. El primer recibo se consulta tras 15 minutos.
- Si hay InvalidCredentials o MismatchSenderId, verificar la clave FCM V1 y el proyecto Firebase antes de hacer otro build. Si el permiso está concedido pero el registro falla, conservar el mensaje sin compartir tokens.

Pendiente: confirmación física del titular. La finalización de EAS no valida la recepción real.
