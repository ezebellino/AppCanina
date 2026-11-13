# Expo Push — Lazuna 0.8.16

## Configuración verificada

Firebase existente: tu-veterinaria-comunidad. Se registró Android con paquete com.vasco88.tuveterinariacomunidad y alias Lazuna. google-services.json público incorporado a mobile/app.json. EAS ya muestra una clave FCM V1 del mismo proyecto (cargada anteriormente); no fue reemplazada. No se inspeccionó su clave privada ni se probó su validez mediante entrega. El titular generó otra clave en Firebase durante la preparación; no se utilizó ni incorporó al repositorio. No revocar la clave activa en EAS al limpiar claves sin uso.

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
