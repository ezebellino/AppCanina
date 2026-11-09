# Publicaciones web

La versión pública se define únicamente en `appcanina/VERSION`. Django la muestra en el pie de la aplicación y la usa para renovar la caché de CSS y JavaScript. Docker incluye este archivo.

Antes de publicar una mejora, actualizar la versión en el mismo commit:

- Correcciones o ajustes visuales: aumentar el último número (0.2.0 → 0.2.1).
- Nuevas funciones: aumentar el segundo y reiniciar el último (0.2.1 → 0.3.0).
- Cambios mayores incompatibles: aumentar el primero.

Verificar `manage.py check`, las pruebas correspondientes, el despliegue de Railway y el número visible. Reintentar un despliegue sin cambios conserva su versión. El número no se incrementa por recargar una página ni reiniciar el servidor.

La versión de Expo en `mobile/app.json` identifica otro artefacto: actualizarla al preparar un APK. Publicar una mejora web no requiere un build de Expo.

## 0.2.0

Botón de cuenta con flecha vectorial y estados de apertura; versión visible en escritorio y al pie del contenido en celulares.

## 0.3.0

Registro web público desde el login, con elección y explicación de perfiles: colaborador, institución y veterinaria. Las organizaciones nuevas quedan pendientes de validación.

## 0.4.0

Compartir credenciales PDF desde el navegador, con descarga alternativa para WhatsApp. Invitaciones familiares de un uso, consulta compartida y revocación en web; aceptación común con el cliente móvil.

## 0.4.1

Confirmaciones por correo al aceptar una invitación familiar en web o móvil, después de guardar el acceso. El registro conserva el destino de regreso al iniciar sesión.

## 0.5.0 — Lazuna

Marca pública centralizada en APP_NAME, nueva URL pública centralizada en PUBLIC_BASE_URL, y nombres actualizados en web, correos, credenciales y cliente Expo. Identificadores internos, base de datos, volumen, paquete Android y proyecto EAS conservados para no perder datos ni crear otra app.

URL verificada: https://lazuna.up.railway.app. Railway fue renombrado y PUBLIC_BASE_URL actualizado. El corte reemplaza la URL gratuita anterior: los enlaces viejos dejan de funcionar y el APK anterior debe actualizarse. El usuario autorizó expresamente el corte y un nuevo build después de las pruebas. No se compraron dominios ni se modificó DNS de Hostinger.

Validación: 141 pruebas Django, exportación Android local y respuesta HTTPS 200 del nuevo login. EAS preview fija la nueva API y aumenta el versionCode; conserva paquete y credenciales de firma.

## 0.5.1 — Invitación familiar por enlace

Web y API generan un enlace con código en el fragmento (no se envía en la URL HTTP). La página lo prepara por POST con CSRF y lo conserva temporalmente en la sesión del servidor durante registro/login. Abrir o previsualizar no concede acceso: la aceptación autenticada sigue siendo explícita, de uso único y con vencimiento de 15 minutos. El código manual continúa disponible.

El cliente Expo comparte el enlace y texto de la API. Cambio acumulado para el próximo APK por decisión del usuario: no ejecutar EAS Build para esta publicación; la versión nativa permanece 0.5.0 hasta preparar el siguiente artefacto. Los APK ya instalados continúan compartiendo el código manual; desde la web se puede usar el nuevo enlace.

Validación local: 146 pruebas Django, 3 pruebas Node del fragmento y preparación, `manage.py check` y exportación Android. Cobertura: continuidad registro/login, CSRF, no aceptación al previsualizar/preparar, vencimiento, uso único y compatibilidad del código manual.
