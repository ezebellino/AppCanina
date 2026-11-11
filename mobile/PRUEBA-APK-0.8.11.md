# Prueba en teléfono — Lazuna 0.8.11

APK: https://expo.dev/artifacts/eas/fR7ojFo6RbhCJOOlXwP_KAC-yWzLSp-xVAWt80PpD8A.apk

Build `27eb8a55-ffe8-4b1a-9fce-d90d5a97a54d` FINISHED; Android versionCode 4.

Instalar como actualización sobre el APK existente, sin desinstalar. Verificar versión 0.8.11. Este paquete reúne mapas, coordinación de visitas, bandeja del refugio, cierre de búsquedas y novedades. Push robusto/proveedor siguen pendientes; probar las notificaciones DENTRO de la app.

## 1. Ingreso y novedades

- Ingresar con la cuenta personal. Abrir Novedades desde la cabecera.
- Probar Todas/Sin leer y contador; abrir una novedad y volver para comprobar que quedó leída.
- Abrir un avistamiento: debe mostrar el animal y el mapa; una respuesta de moderación debe abrir la solicitud propia.
- Volver a la app desde segundo plano y comprobar actualización del contador. Sin push, no se espera una alerta del sistema operativo.

## 2. Visitas entre dos cuentas

- Desde adoptante, solicitar visita para una publicación de prueba y comprobar Esperando al refugio.
- Desde responsable del refugio, Mi actividad → Solicitudes recibidas: abrir y aceptar con dirección, día y horario.
- Desde adoptante, actualizar o abrir la novedad: comprobar indicaciones y botón Maps.
- Con otra solicitud de prueba, rechazar y comprobar que no se comparte dirección. No cambiar datos de adopciones reales para ensayar.

## 3. Extraviados y mapas

- Abrir aviso con avistamientos: última zona, puntos aproximados y aclaración del área estimativa.
- Probar aviso sin coordenadas y enlace externo a Maps.
- En un aviso propio DE PRUEBA, cancelar el cierre, luego confirmar animal encontrado y revisar Encontrados. No usar Alelí ya cerrada.

## 4. Red, permisos y cuentas

- Sin conexión: abrir/actualizar novedades y reintentar al recuperar red; no debería quedar leída por una carga fallida.
- Cambiar rápidamente de pantalla durante una carga; no debe abrirse contenido antiguo.
- Cerrar sesión, ingresar con otra cuenta: no deben quedar fichas ni notificaciones de la cuenta previa.
- Una cuenta ajena no debe gestionar solicitudes del refugio ni finalizar búsquedas de otros.

## 5. Uso cotidiano

- Confirmar que Mis animales y la vinculación familiar siguen funcionando.
- Probar cámara/galería, cancelación de selección y ubicación voluntaria.
- Revisar menú, contador y formularios en vertical/apaisado y con letra grande.

Ante un problema, registrar pantalla/paso, cuenta o rol utilizado (sin contraseña), conexión disponible y mensaje exacto. No hace falta repetir acciones que envían correos si ya quedaron guardadas.
