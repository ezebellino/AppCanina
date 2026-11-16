# Expo Push — Lazuna 0.8.16

## Configuración verificada

Firebase existente: tu-veterinaria-comunidad. Se registró Android con paquete com.vasco88.tuveterinariacomunidad y alias Lazuna. La configuración Android se resuelve desde mobile/app.config.js: archivo secreto de EAS GOOGLE_SERVICES_JSON o copia local google-services.json, fuera de Git. EAS ya muestra una clave FCM V1 del mismo proyecto (cargada anteriormente); no fue reemplazada. No se inspeccionó su clave privada ni se probó su validez mediante entrega. El titular generó otra clave en Firebase durante la preparación; no se utilizó ni incorporó al repositorio. No revocar la clave activa en EAS al limpiar claves sin uso.

## Recorrido

1. El usuario inicia sesión y pulsa Activar alertas en este teléfono. Android solicita permiso y Expo devuelve el identificador del dispositivo.
2. El servidor registra el identificador ligado a esa sesión. Al crear una novedad, encola un envío por dispositivo y notificación.
3. Un worker usa la base SQLite compartida y una concesión global para enviar hasta 100 mensajes, con un mínimo de dos segundos entre solicitudes. No hay llamadas a Expo en el request web.
4. El ticket de Expo queda guardado; se consulta su recibo tras 15 minutos. confirmed/provider_accepted significa aceptación de FCM/APNs, NO recepción visible ni lectura humana.
5. Al tocar el aviso, el próximo APK abre la bandeja autenticada. El payload no concede acceso ni marca automáticamente como leída una novedad.

## Operación

Migración lost_pets.0014 agrega PushDelivery y PushWorkerLease. El contenedor inicia gunicorn y process_push mediante config.run_services; si un proceso termina inesperadamente, detiene al otro y sale con error para que la plataforma reinicie la unidad. PUSH_WORKER_ENABLED=0 permite detener el consumo sin borrar la cola. Todos los emisores de Lazuna deben usar esta cola y la misma base; emisores externos al proyecto no quedan limitados por ella.

Comandos seguros: python manage.py push_status (solo conteos/categorías), python manage.py process_push --once (procesa un lote real). No ejecutar el segundo contra producción como prueba sin dispositivos de prueba preparados.

Reintentos exponenciales con variación y Retry-After; seis intentos por fase y vencimiento de 24 horas. Errores de credenciales/payload requieren corrección operativa. DeviceNotRegistered desactiva únicamente el registro que conserva la sesión original. Lectura/visibilidad/sesión se revalidan antes del envío. Un fallo después de que Expo acepte pero antes de guardar el ticket puede duplicar un aviso: entrega al menos una vez, no exactamente una vez. La cola no procesa retrospectivamente novedades creadas antes de esta integración. Solo se encolan dispositivos registrados al producirse el evento.

Alcance: búsquedas nuevas, avistamientos y respuesta de revisión comunitaria. Las novedades de adopción y vínculos familiares siguen sus canales existentes; no se incorporaron automáticamente a esta cola. Sin credenciales APNs/iOS: este bloque prepara Android. Los registros de entrega permanecen para diagnóstico; definir retención operativa antes de aumentar el volumen.

## Prueba física pendiente

Instalar el próximo APK como actualización. Iniciar sesión personal, abrir Mi teléfono y alertas, pulsar Activar alertas en este teléfono y conceder permiso. Bloquear el teléfono sin forzar la detención de Lazuna. Usar una revisión real acordada de una búsqueda de esa cuenta. Comprobar aparición de la notificación, apertura de bandeja al tocarla y resultado del recibo tras 15 minutos. Repetir con app abierta y tras cambiar de cuenta. No confundir permiso concedido con registro correcto o ticket con entrega física.

Fuentes: https://docs.expo.dev/push-notifications/fcm-credentials/ y https://docs.expo.dev/push-notifications/sending-notifications/

## Configuración Firebase fuera de Git — 2026-11-16

- GitHub secret-scanning #1 señaló la API key cliente de `mobile/google-services.json`, no una clave privada de cuenta de servicio. El archivo se conserva localmente, pero se retira del seguimiento Git y del archivo de subida EAS.
- `GOOGLE_SERVICES_JSON` está configurado como variable de tipo archivo y visibilidad secret, scope project, en development, preview y production de `@vasco_88/tu-veterinaria-comunidad`. Su valor en build es una ruta al archivo. No usar `EXPO_PUBLIC_` ni pegar el JSON en app.json o logs.
- Un clon nuevo necesita la configuración local descargada de Firebase o la variable de archivo del entorno EAS. La copia local no se versiona. Mantener el paquete Android y el projectId EAS originales.
- Google Cloud: Android key reducida de 25 a 6 APIs: FCM Registration, Firebase Installations, Firebase Management, Cloud Logging, Identity Toolkit y Token Service. Se conservó Identity Toolkit porque Google detectó uso activo; Token Service acompaña la autenticación. No se forzó la advertencia de interrupción.
- Restricciones de aplicación siguen sin modificar: antes de limitar por paquete y certificado debe verificarse la firma del APK y la compatibilidad de los SDK. No revocar/rotar sin coordinar la actualización de los APK instalados. La credencial privada FCM V1 de EAS no se cambió.
- Quitar el archivo de Git no borra el historial ni el valor incluido en APK anteriores. La alerta sigue abierta: no declarar revocación ni ausencia de abuso; falta prueba física de registro/recepción push tras la propagación de las restricciones (hasta 5 minutos según Google).
- Comprobaciones: `node --test scripts/test-firebase-config.cjs`; Expo config prebuild local y con ruta de archivo EAS (salida filtrada, nunca imprimir el contenido del archivo).
- Fuente de compatibilidad: https://firebase.google.com/docs/projects/api-keys
