# Revisión del paquete móvil — 2026-11-11

Estado: preparado para prueba física; no se generó un APK durante esta revisión.

## Alcance

Mapas aproximados de extraviados, cierre de búsquedas, coordinación de visitas del adoptante, bandeja institucional y novedades. El transporte push y su control completo siguen aplazados. El APK instalado 0.8.5 no incluye este paquete.

## Correcciones encontradas

1. Un avistamiento en una búsqueda propia enviada desde el móvil abría Mis solicitudes en lugar del detalle público con mapa. Ahora abre el aviso; las respuestas privadas de moderación siguen abriendo la solicitud propia.
2. Una carga anterior de solicitudes podía reemplazar el contenido seleccionado desde una notificación. Se invalidan respuestas anteriores tanto para solicitudes de búsqueda como para adopciones; también se limpia el error/carga anterior al abrir la novedad.

## Evidencia

- Revisión completa inicial: 121 pruebas Django de lost_pets aprobadas.
- Tras corregir el destino: 9 pruebas de novedades aprobadas, incluida la nueva regresión del avistamiento propio.
- 24 pruebas Node aprobadas: sesiones, mapas, invitaciones, búsqueda veterinaria, Metro y cuatro pruebas nuevas de navegación con los componentes React reales.
- Exportación Android final correcta (751 módulos). No equivale a ejecutar Android.
- Pruebas React: abrir contenido antes de registrar lectura; carga fallida mantiene pendiente; salir durante la petición descarta la respuesta; carga antigua no reemplaza la adopción seleccionada.
- Componentes nativos y servicios Expo simulados en estas pruebas: NO validan píxeles, tamaño de toque, mapa WebView, teclado, permisos reales ni gestos.

## Prueba física pendiente para el próximo APK

1. Notificaciones: contador y filtros, abrir una de cada tipo, volver y comprobar lectura; revisar texto grande y pantalla angosta.
2. Dos cuentas: adoptante solicita visita, refugio responde, adoptante abre dirección; comprobar que cada uno ve solo lo autorizado.
3. Red: cargar sin conexión, reintentar, cambiar de pantalla durante la carga y salir/cambiar de cuenta con una petición pendiente.
4. Mapas y búsquedas: mapa con/sin coordenadas, abrir Maps, cancelar y confirmar cierre de un aviso de prueba; verificar Encontrados.
5. Regresión básica: ingreso, vínculo familiar, cámara/galería y menú vertical/apaisado. No modificar datos reales para ensayar.

## Reproducir pruebas de navegación

Desde la raíz, instalar herramientas únicamente en tmp (no modifica dependencias del APK):

```powershell
npm.cmd install --prefix tmp/mobile-review --no-audit --no-fund --package-lock=false react@19.1.0 react-test-renderer@19.1.0
node scripts/test-mobile-notifications.cjs
```

Usar Node 22.23.4 y dependencias mobile instaladas. React Test Renderer emite una advertencia de deprecación; este arnés se usa como verificación lógica temporal, no como sustituto de pruebas nativas.
