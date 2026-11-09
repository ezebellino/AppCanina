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

## 0.5.2 — Preparación de invitación con HTTPS

La comprobación real del navegador detectó un rechazo CSRF con `Referrer-Policy: no-referrer`. Se usa `same-origin`: conserva el origen necesario para validar POST HTTPS, sin enviar Referer a otros sitios ni incluir el fragmento secreto. Revalidación de las 9 pruebas familiares, incluida preparación HTTPS con CSRF.

## 0.5.3 — Separación entre instituciones

La vinculación de cuentas autoriza una ficha concreta, no todos los animales de un contacto. La migración `patients.0010` conserva los accesos anteriores de responsables y adoptantes (incluidos animales archivados); las invitaciones familiares mantienen su autorización independiente. Crear un animal desde el APK concede explícitamente acceso a esa ficha. Los contactos compartidos se separan al editar sus datos desde otra institución, conservando los roles y permisos de la ficha editada.

Se limitan contactos, agenda y edición de turnos, búsqueda de productos, proyecciones de ventas y selectores de cobro a las instituciones autorizadas. Las superposiciones de peluquería se comprueban dentro de cada institución. El catálogo común de servicios no cambia en este bloque.

No requiere un nuevo APK. La API mantiene el contrato de la versión instalada. Antes de publicar: suite Django completa, migración de vínculos históricos, pruebas de aislamiento entre dos instituciones y revisión independiente del parche. Al desplegar, confirmar `patients.0010` aplicada y versión web 0.5.3. La migración conserva permisos históricos; no determina retrospectivamente si alguna vinculación anterior fue indebida.

## 0.6.0 — Atenciones veterinarias autorizadas

Desde Mis animales → Historial → Autorizar veterinaria, el responsable principal elige una institución verificada, solo consulta o consulta y nuevas atenciones, durante 24 horas, 3 días o 7 días. Un nuevo permiso para la misma institución reemplaza el anterior; retirar el permiso corta acceso y escritura, conservando el historial existente. Los familiares con acceso de consulta no pueden conceder permisos clínicos.

La veterinaria abre Atenciones autorizadas. Cada lectura y escritura exige pertenencia actual a la institución, permisos clínicos, vigencia del permiso y autoridad actual de quien lo concedió. Las nuevas atenciones guardan paciente, profesional, institución y autorización desde el servidor; no existe edición de registros anteriores en este flujo. Los registros históricos sin institución conocida se conservan sin inventar su procedencia.

Las credenciales de viaje siguen siendo de consulta. Se revalidan consentimiento, credencial, pertenencia y verificación institucional al abrir el historial; desactivar el consentimiento anula los códigos anteriores para evitar que revivan al reactivarlo.

La migración patients.0011 agrega autorizaciones, auditoría de consulta y procedencia de registros. Flujo disponible en web responsive, sin nuevo APK. El APK existente recibe las nuevas atenciones mediante la API compatible; la gestión de permisos se realiza en la web. No se enviaron correos ni se alteraron cuentas reales en las pruebas.

## 0.7.0 — Buscar veterinarias por nombre y cercanía

El selector de autorización permite buscar por nombre, localidad y dirección, sin distinguir tildes ni mayúsculas. “Usar mi ubicación” solicita permiso al navegador y ordena por distancia aproximada en línea recta, con filtros de 5, 10, 25 y 50 km. No elige una institución automáticamente; si un filtro oculta la selección actual, la limpia. Nombre, ciudad y dirección siguen visibles para distinguir instituciones homónimas.

La posición del usuario se mantiene solo en memoria en esa pantalla, sin enviarla al servidor ni guardarla. La ubicación es opcional: ante rechazo, error o falta de coordenadas se mantiene la búsqueda textual. Las veterinarias sin coordenadas figuran al final al ordenar y quedan excluidas al aplicar un radio; “Todas las distancias” vuelve a incluirlas.

La migración organizations.0007 agrega coordenadas opcionales del local, validadas como par y con límites geográficos. Desde Mi negocio, el responsable puede usar la ubicación estando físicamente en la veterinaria y guardarla como ubicación pública del local. Modificar dirección o localidad requiere volver a marcarla. No se geocodifican direcciones automáticamente ni se inventan coordenadas para registros existentes.

Validación: 182 pruebas Django, 3 pruebas Node de búsqueda/distancias, validación de migraciones y navegador a 390 px (sin desbordamiento), rechazo de ubicación, cercanía simulada y limpieza de selección al cambiar filtros. No requiere ni genera un APK; mejora de la web.

## 0.7.1 — Exploración desde administración

Las cuentas de plataforma con staff pueden explorar el catálogo publicado de adopciones sin necesitar un grupo institucional o comunitario. El menú de plataforma incorpora Explorar adopciones junto al panel y la validación. Los filtros de gestión no revelan publicaciones pendientes a una cuenta staff sin institución; tampoco conceden creación o cambios de estado. Los permisos clínicos y comerciales mantienen su alcance.

Validación: 41 pruebas de organizaciones y navegación de adopciones, incluyendo staff sin grupos, filtros, bloqueo de escritura y acceso de usuarios sin permisos. Sin migraciones ni nuevo APK.
