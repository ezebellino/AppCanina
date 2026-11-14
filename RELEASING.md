# Publicaciones web

## 0.8.22 — Cierre automático de confirmaciones web

- Las confirmaciones flotantes permanecen 3 segundos y luego se desvanecen en 250 ms. Con movimiento reducido se retiran sin animación. Las indicaciones de visita dentro de las tarjetas permanecen visibles.
- Fondo claro y contraste corregido en las cuatro confirmaciones. Sin cambios de APK.
- Validación: cinco pruebas del componente web, incluyendo temporización y movimiento reducido.


## 0.8.21 — Confirmaciones y menús con movimiento

- Web y próximo APK: huella al finalizar búsqueda, sobre al enviar solicitud, perfiles al vincular familia y calendario al aceptar visita. Éxito solo después de respuesta confirmada; resolución repetida no vuelve a animar.
- Menú hamburguesa con entrada/salida hacia abajo; menú de usuario web suave. Escape, clic exterior, pulsaciones rápidas y movimiento reducido comprobados. Menú nativo desplazable para pantallas pequeñas.
- Validación: 41 pruebas Django, 11 pruebas móviles, 6 pruebas web; navegador a 1280 px y 390 px. Exportación Android local correcta, sin build EAS. Verificación física del menú nativo pendiente del próximo APK.


## 0.8.20 — Corrección de la URL al archivar desde web

Un botón name="action" sustituía la propiedad form.action por el propio botón. Los logs confirmaron POST a [object HTMLButtonElement] con 404; no llegaban a la operación de archivo. Ahora se lee el atributo action explícito. Se comprueba el tipo de respuesta, redirecciones de sesión y confirmaciones inválidas antes de animar; errores recuperables sin mostrar excepciones técnicas.

Validación: tres pruebas Node de URL, respuestas HTML/sesión/JSON inválido y conflictos. Reproducción en DOM real con el botón action y respuesta interceptada únicamente en la ruta correcta: POST, animación y navegación completados. Sin cambios móviles ni nuevo build. La prueba visual anterior simulaba cualquier fetch y por eso no detectó la URL incorrecta; esta comprobación restringe la URL.


## 0.8.19 — Animación de archivado

Tras confirmar el servidor, la tarjeta se pliega y un sobre entra en un archivador. Sin animación de éxito ante errores; botón deshabilitado durante la operación, reintento disponible ante fallo y respeto por movimiento reducido. Web usa confirmación JSON conservando POST con CSRF y formulario tradicional sin JavaScript. Móvil preparado con Animated y sin dependencias nuevas; no se generó APK.

Validación: prueba visual en navegador local a 390 y 1280 px, error/reintento, llegada a la pantalla posterior y movimiento reducido. Nueve pruebas de interacción móvil verifican archivo/restauración, movimiento reducido y ausencia de animación ante conflicto. Nueve pruebas Django del archivo y confirmación JSON. Exportación Android local correcta: 753 módulos.


## 0.8.18 — Archivo personal de solicitudes de adopción

Después de “Adopción concretada” o “No continuó”, cada solicitante o responsable puede archivar la solicitud desde su propia bandeja y restaurarla desde Archivadas. No borra historial ni modifica el estado compartido; otros responsables conservan sus propias vistas. Si cambia la solicitud, reaparece automáticamente. Contadores y novedades excluyen los archivos personales vigentes; las nuevas respuestas vuelven a mostrarse.

Migración aditiva 0015_adoptionarchive. Acciones web por POST con CSRF, API autenticada y permisos de institución vigentes; versión de la solicitud requerida para no archivar cambios que todavía no se vieron. API y cliente móvil preparados; **sin build EAS**. El APK anterior no incluye el filtro Archivadas: hasta actualizarlo, se pueden recuperar desde la web.


Validación del archivo: 31 pruebas Django focalizadas (8 nuevas de archivo, 8 de bandeja móvil y 15 de solicitudes/visitas web), 8 pruebas de interacción móvil y exportación local Android de 752 módulos. Revisión general de 148 pruebas: tres expectativas de interfaz actualizadas y verificadas en la repetición focalizada. Migraciones sin diferencias pendientes.

## 0.8.17 — Colaboraciones voluntarias e ícono push preparado

Anuncios publicados de refugios verificados muestran alias opcional, mensaje y botón Copiar alias al pie. Configurable desde Mi Institución; sin pasarela de pagos ni requisito para adoptar. Web y API ocultan colaboraciones de instituciones no verificadas, veterinarias y publicaciones no vigentes. Copia con confirmación y alternativa manual si el navegador o teléfono la rechaza.

Cliente móvil preparado con el mismo bloque y una huella blanca transparente de 96 × 96 para notificaciones Android, configurada en expo-notifications. Arte reproducible mediante scripts/New-NotificationIcon.ps1. **Sin nuevo build EAS**: el APK instalado conserva su ícono hasta la próxima actualización.

Validación: 16 pruebas Django (colaboraciones, perfil y ubicación), 7 pruebas móviles (copia y notificaciones), exportación local Android de 752 módulos y manifiesto Expo con ícono para Firebase y notificaciones locales. Verificación visual del PNG blanco/transparente. Sin migraciones.

## APK 0.8.16 disponible

Build único autorizado `9c83cd33-335e-4cfc-90a1-599cf12a6132`, estado **FINISHED**, Android versionCode 5, perfil preview, firma existente conservada. Fuente `c0589356945efdac8d33d24cdcc9245926ceefab`. Incluye Firebase Android y navegación desde push. APK: https://expo.dev/artifacts/eas/XbZaqlOyoDiOwmxPuqpg_FCagq67P9dUBC1Q-_u9nZE.apk . Guía: `mobile/PRUEBA-APK-0.8.16.md`. Instalación y recepción física confirmadas por el usuario; captura de notificación recibida con el nombre del animal.


## 0.8.16 — Cola Expo Push y configuración Android

Cola persistente por notificación/dispositivo/sesión, lotes de 100 separados al menos dos segundos mediante concesión compartida en SQLite, reintentos con backoff y Retry-After, tickets/recibos, cancelación por visibilidad/sesión y baja de dispositivos inválidos. Worker supervisado junto con gunicorn; migración 0014. Diagnóstico agregado mediante push_status. Ver mobile/EXPO-PUSH.md para límites y alcance.

Firebase Android registrado, configuración pública incorporada y credencial FCM V1 existente verificada en la interfaz EAS. Cliente abre la bandeja al tocar push y captura fallos de canal/permisos. Claves privadas no incorporadas al repositorio. 145 pruebas Django del módulo lost_pets correctas. Exportación Android 751 módulos, compatibilidad Expo correcta, cinco pruebas Node de navegación y arranque/cierre conjunto de servicios en contenedor aislado correctos. Prueba física y próximo APK pendientes.


## 0.8.15 — Avisos de revisión de búsquedas en web y correo

Mis búsquedas muestra las notificaciones internas pendientes de los avisos propios, incluyendo aprobación/rechazo y avistamientos entregables. Contador en accesos del perfil y navegación, actualizado al cargar, volver a la pestaña y cada 30 segundos visible. Lectura explícita por POST con CSRF, limitada al destinatario/autor y al ID visto: no consume novedades posteriores ni se marca al abrir una página. Usa los registros y lecturas existentes del APK; las notificaciones antiguas no leídas se muestran sin aprobar otra vez.

Las nuevas respuestas de moderación envían correo al solicitante activo con dirección válida y enlace a Mis búsquedas. Sin coordenadas ni motivo privado en el correo, asuntos fijos y logs por categoría sin datos sensibles. Si SMTP falla, conserva la decisión y novedad interna y advierte al moderador. Actualización condicional del estado evita envíos duplicados al repetir la misma respuesta. No se reenvían correos retroactivos.

Validación: 86 pruebas Django (plataforma, búsquedas web, visibilidad y novedades móviles), incluyendo aprobación con correo en memoria, fallo SMTP simulado, reintento sin duplicados, lectura por destinatario, CSRF y conservación de novedades posteriores. Sintaxis JavaScript y git diff --check correctos.

Sin migraciones ni nuevo APK. Push existente de mejor esfuerzo permanece sin cambios; recepción con app cerrada depende de registro, sesión vigente, credenciales y permisos del dispositivo. No se afirma entrega física ni recepción de correo real. La integración robusta de push continúa pendiente según lo acordado.

## 0.8.14 — Moderación de búsquedas desde plataforma

El administrador staff activo puede aprobar/rechazar avisos con el mismo criterio de autorización que ya permitía ver solicitudes privadas. No requiere superusuario ni pertenencia al grupo institucional Administrador. Panel y navegación incorporan Revisar búsquedas; pestaña Solicitudes y acciones del detalle reconocen staff. Publicar animal extraviado se oculta en listado, perfil y accesos del administrador, sin retirar la función a colaboradores ni cambiar la autorización de la ruta de creación.

Se conserva el permiso explícito change_lostpetreport para moderadores existentes y la exigencia de motivo para rechazos. POST y CSRF obligatorios; colaboradores no pueden moderar ni sus propias solicitudes. No se cambian grupos, instituciones ni cuentas reales. Sin migraciones ni APK. Validación: 75 pruebas de plataforma, búsquedas web y visibilidad correctas; git diff --check sin errores. Aprobación/rechazo probados con notificaciones simuladas, sin envío real.

## 0.8.13 — Autocompletar animal vinculado en búsquedas web

Seleccionar un animal completa nombre, especie y raza y muestra su foto disponible. La foto de la ficha se copia al aviso, procesada sin metadatos, si no se sube otra. Datos editables del aviso no modifican la ficha; no se copian notas clínicas. Cambiar de animal actualiza los datos identificatorios, conservando zona, fecha, señas y archivo elegido por el usuario. Los errores de validación conservan los valores ingresados. Al editar sin cambiar de animal se mantiene la foto actual del aviso.

El servidor completa datos vacíos desde el animal autorizado y valida nuevamente la vinculación. JSON limitado al selector permitido, sin datos clínicos, con escape de plantilla y respuesta no-store. Sin migraciones ni cambios del APK.

Validación: 70 pruebas Django de publicaciones/visibilidad y una prueba Node de selección, cambio de animal, foto elegida y conservación de datos. Copia real de imagen validada con almacenamiento temporal y datos ficticios. Sin pruebas de publicación con animales reales. Pendiente comprobación visual en teléfono.

## 0.8.12 — Publicación comunitaria y perfil web

Accesos agrupados arriba del formulario personal: Mis animales, Publicar animal extraviado, Mis búsquedas y Mis solicitudes de adopción. La navegación y el listado de extraviados también permiten iniciar una búsqueda. Los colaboradores envían avisos privados a revisión; no pueden publicar directamente ni vincular animales ajenos. Mis búsquedas muestra los estados, permite corregir solicitudes pendientes/rechazadas y finalizar búsquedas publicadas propias. Se reutiliza el flujo de moderación existente y sus fotos protegidas, sin migraciones.

Buscar se oculta para colaboradores y refugios en la web; sigue disponible para perfiles con búsqueda de pacientes/productos. El APK conserva su búsqueda funcional de animales y el acceso Pedir una búsqueda; no se cambió ni generó un APK.

Validación: 68 pruebas Django de publicaciones, permisos y visibilidad correctas; git diff --check sin errores; comprobación del perfil renderizado con usuario ficticio en navegador de escritorio. No se logró capturar una imagen ni verificar visualmente el ancho móvil en la herramienta; esa comprobación queda para teléfono. Sin correos reales ni cambios en animales/cuentas de producción durante las pruebas.

## APK 0.8.11 — 2026-11-11

Build único solicitado por el usuario tras la revisión: `27eb8a55-ffe8-4b1a-9fce-d90d5a97a54d`, perfil preview Android APK, versión 0.8.11/versionCode 4, fuente `a45bdca5820bd3c8ad4e2b31b7e401d5a1227131`. Firma existente conservada. EAS recibió 16.1 MB; exclusiones de respaldos, herramientas, adjuntos y tmp conservadas. Compatibilidad Expo correcta, Doctor 17/17. Guía física: `mobile/PRUEBA-APK-0.8.11.md`. Estado **FINISHED**, completado 2026-11-11 05:42 ART. APK: https://expo.dev/artifacts/eas/fR7ojFo6RbhCJOOlXwP_KAC-yWzLSp-xVAWt80PpD8A.apk . No equivale a instalación ni validación física.

## 0.8.11 — Revisión previa al próximo APK

Corregido el destino de novedades de avistamientos sobre solicitudes móviles propias: abre el detalle del aviso y mapa, mientras la respuesta de moderación sigue abriendo Mis solicitudes. Cliente descarta cargas antiguas de solicitudes que podrían reemplazar la selección abierta desde una novedad. Sin migraciones ni build.

Validación: revisión completa inicial 121 Django, 9 pruebas de novedades tras la corrección; 24 Node incluyendo cuatro de navegación real de componentes con servicios nativos simulados; exportación Android 751 módulos. Ver `mobile/REVISION-PREBUILD.md` para evidencia, alcance y pruebas físicas pendientes. No se declara validación visual/nativa del APK.

## 0.8.10 — Bandeja de novedades y lecturas móviles; acumulado sin APK

Nuevos endpoints privados `/extraviados/api/v1/novedades/`, `/<clave>/` y `/<clave>/leer/`. Unifican notificaciones comunitarias entregables y la última actividad de cada solicitud de adopción por audiencia (solicitante/responsable institucional). Filtros Todas/Sin leer, páginas de 20, contador sin recortar por página y respuestas no-store. GET no marca lectura. POST registra la versión efectivamente abierta y conserva novedades posteriores; recibos compartidos con la web para adopciones. Solo el destinatario o responsable actual de un refugio verificado accede a sus novedades; ocultación, revocación y pertenencia se revalidan. No expone coordenadas ni crea nuevos envíos push.

Cliente: acceso Novedades y contador centrado en cabecera, Notificaciones en menú de ambas áreas, bandeja fuera de Ajustes y apertura de aviso, solicitud de búsqueda, adopción o solicitud institucional específica. Solo marca lectura tras cargar contenido; error de carga conserva pendiente. Respuestas tardías tras salir se descartan; contador se consulta al ingresar, volver a primer plano y cada 60 segundos en primer plano. Lecturas guardadas en servidor, sin depender de permisos push. Para adopciones representa la última novedad por solicitud, no un historial de cada cambio.

Validación: 28 pruebas Django (8 nuevas, 12 de visibilidad y 8 de bandeja institucional), exportación Android de 751 módulos. Pendiente probar físicamente en próximo APK contador, navegación, lectura, falta de red, regreso a primer plano y cambio de cuentas. Sin migraciones, sin EAS Build. Transporte/control completo de push sigue aplazado.

## 0.8.9 — Finalizar búsqueda de un animal encontrado

Botón Se encontró · Finalizar búsqueda en tarjetas/detalle web, con página de confirmación GET y cierre POST protegido por CSRF. Pueden cerrar el autor, moderadores existentes y responsables de refugios verificados de la ficha vinculada. Ser refugio no permite cerrar avisos ajenos sin vínculo. Solo transiciona published a resolved; reintentos son idempotentes, conserva avistamientos y sale del mapa/lista activos. No cierra ningún aviso automáticamente.

Nuevo endpoint móvil POST `/extraviados/api/v1/avisos/<id>/encontrado/`, con los mismos permisos, y capacidad en el detalle. Botón/confirmación móvil acumulados para próximo APK. Pruebas: 24 Django (7 cierre + 12 visibilidad + 5 mapas); exportación Android validada. No se generó build; prueba física pendiente. Sin migraciones ni cambios a push.

## 0.8.8 — Bandeja institucional móvil; acumulado sin APK

Nuevas API GET `/extraviados/api/v1/adopciones/bandeja/` y POST `/extraviados/api/v1/adopciones/bandeja/<id>/`: solicitudes de refugios verificados gestionados por la cuenta, filtros, contadores y páginas de 20. Edición de estado y mensaje visible al adoptante; aceptación/rechazo de visitas reutiliza los correos actuales. Se verifica pertenencia en cada operación, se evita sobrescribir una versión modificada y se conservan respuestas ante fallo SMTP. Sin migraciones; sin cambios al proveedor push.

En Mi actividad del próximo APK, la capacidad devuelta por el servidor habilita Solicitudes recibidas. Formularios con límites, errores, actualización, bloqueo de doble envío y descarte de respuestas tras salir. La dirección se comparte solamente al aceptar. Cambiar el estado de una solicitud no cambia la publicación del animal.

Validación: 28 pruebas Django (8 nuevas de bandeja, 8 del adoptante y 12 web); exportación Android de 750 módulos. Prueba física pendiente del próximo APK. Control completo de push y elección de proveedor aplazados por pedido del usuario; comparar mantenimiento antes de decidir.

## 0.8.7 — Visitas de adopción desde el móvil; acumulado sin APK

El adoptante puede solicitar una visita desde Mi actividad, consultar la respuesta del refugio y abrir la dirección aceptada en Maps. Incluye institución, explicación breve del estado, indicaciones, actualización manual y mensajes de carga/error. La bandeja institucional nativa es otro bloque pendiente; el refugio responde desde la web existente.

API: nuevo POST autenticado `/extraviados/api/v1/adopciones/solicitudes/<id>/visita/` y datos de visita en la actividad privada. Solo el solicitante puede acceder; requiere refugio verificado, publicación vigente y solicitud abierta. Actualización condicional evita duplicados y reenvío de correos en reintentos. Dirección únicamente tras aceptación, indicaciones tras respuesta, caché desactivada en actividad/respuesta. Fallos SMTP conservan la solicitud y devuelven aviso. Sin migraciones.

Validación: 20 pruebas Django (8 nuevas y 12 del flujo web), exportación Android correcta de 749 módulos. Falta validación física en el próximo APK: solicitar, refrescar tras respuesta web, abrir Maps, reintentar sin red y cambiar de cuenta. No se ejecutó EAS Build.

## 0.8.6 — Datos del mapa móvil; cliente acumulado sin APK

Nuevo GET autenticado `/extraviados/api/v1/avisos/<id>/`: detalle de avisos publicados/resueltos, última observación y puntos aproximados de las últimas 20 observaciones, ordenadas por fecha de avistamiento. Excluye avistamientos ocultos incluso para revisores y nunca serializa latitud/longitud exactas. Respuesta no-store; sin migraciones ni cambios a los endpoints anteriores.

Cliente preparado: botón de última ubicación en Google Maps, mapa Leaflet/OSM dentro de WebView y área estimativa con margen de 300 m, fechas y aclaración de que no predice ubicación actual. Maneja último reporte sin GPS, ausencia total de puntos, errores y actualización del detalle; protege contra respuestas tardías de otro aviso. Sin rastreo ni nuevos permisos GPS. WebView no recibe credenciales y bloquea navegación, acceso a archivos y geolocalización. Dependencias remotas Leaflet fijadas con SRI.

Pruebas: 17 Django (cinco nuevas + visibilidad existente) y 11 Node (cuatro nuevas + sesiones); compatibilidad Expo correcta y exportación Android de 748 módulos. Revisión visual del HTML del mapa con dos puntos ficticios: cartografía, puntos y área visibles. No equivale a prueba física de Android/iOS. Próximo APK acumulado, sin EAS Build en este bloque. Ver `mobile/README.md`.

## Preparación APK 0.8.5 — 2026-11-10

Entrega: único build iniciado en este bloque, `2b23795a-bbd5-462a-9e6e-0bdf7f3f24d2`, estado **FINISHED**, versión 0.8.5/versionCode 3, perfil preview, firma Android existente, fuente `9484f21`. APK: https://expo.dev/artifacts/eas/zIlg77lT2XEJsdj1i4d1_LmEWs4PmV8Jq8PLzp322sc.apk . Panel: https://expo.dev/accounts/vasco_88/projects/tu-veterinaria-comunidad/builds/2b23795a-bbd5-462a-9e6e-0bdf7f3f24d2 . El build no prueba instalación/funcionamiento físico; ver `mobile/PRUEBA-APK-0.8.5.md`. Railway del checkpoint quedó SUCCESS y login público HTTP 200/versión 0.8.5. No se eliminaron DEMO ni se configuró YubiKey.

Cliente Expo 54 preparado para un único build preview Android: versión visible 0.8.5, APK explícito, identidad/proyecto EAS y arquitectura conservados, API pública Lazuna. Último build previo consultado: 14c3b508-8425-4f1d-8b72-2ce51fc633f6, FINISHED, 0.5.0/versionCode 2. Sin builds en curso al verificar.

Validación actual: 16 pruebas Node aprobadas con Node 22.23.4; Expo install --check correcto; Expo Doctor 17/17; exportación Android de 739 módulos correcta. npm audit: 0 críticos/altos/moderados, 12 bajos ya documentados por deepmerge. Inspección local del archivo EAS con `.easignore` en la raíz: excluidos respaldos, adjuntos, temporales, herramientas y entornos locales; presentes configuración, lock, fuentes y asset del móvil. No es una prueba física ni auditoría completa de dependencias Gradle.

Incluye mejoras ya preparadas de sesiones y limpieza al salir, enlace web en invitaciones familiares, búsqueda de veterinarias y adaptación Expo 54. Pendiente validar APK en teléfono: instalar sobre 0.5.0 sin desinstalar, ingreso/recuperación, cierre sin red y cambio de cuenta, biometría, cámara/galería y cancelación, ubicación, notificaciones, invitación entre dos cuentas y menús en vertical/apaisado. YubiKey y automatización Proxmox quedan fuera de este bloque.

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

## 0.7.2 — Exploración de extraviados desde plataforma

El administrador de plataforma puede abrir el listado de extraviados, los detalles, el mapa y sus datos con una regla compartida de lectura, sin pertenecer a grupos institucionales. El menú incorpora Animales extraviados. Los permisos de creación de avisos, avistamientos y cambio de estado siguen siendo independientes. El mapa conserva las coordenadas aproximadas y solo incluye avisos publicados; la restricción de avisos ocultos para colaboradores permanece.

Pruebas de regresión: recorrido de lectura con staff sin grupos, filtros, acceso anónimo y sin permisos, bloqueo de escritura, privacidad del mapa y restricciones de colaboradores. Sin migraciones ni nuevo APK.

## 0.8.0 — Ciclo de vida de sesiones móviles

El token Bearer conserva su formato y las rutas de login/registro. Ahora vence a los 30 días desde su emisión (el uso no renueva el plazo), exige usuario activo y una huella HMAC de la contraseña vigente. Cambiar o recuperar la contraseña invalida todos los tokens anteriores, incluso si se elige la misma contraseña. Una sesión inválida devuelve 401; falta de permisos devuelve 403. POST `api/v1/sesion/cerrar/` revoca solo el token presentado, aunque haya perdido permisos, y es idempotente.

La migración `lost_pets.0013` revoca los tokens existentes sin vínculo de contraseña y desactiva los dispositivos push anteriores. Se requiere volver a ingresar y reactivar alertas push. Los nuevos dispositivos push quedan vinculados a la sesión que los registró; al enviar se comprueban titular, vigencia, revocación y contraseña. Los avisos dentro de la app permanecen disponibles.

Para el próximo APK: el cliente valida la sesión antes de guardarla, elimina las contraseñas del formulario, solicita cierre remoto y borra el acceso guardado. Al terminar desmonta el estado de la cuenta, incluidos historiales, credenciales, ubicaciones y formularios. Las peticiones pendientes se abortan y sus respuestas tardías se rechazan; las escrituras en SecureStore se serializan para que una activación tardía no restaure un token eliminado. Un 403 de permisos no cierra la sesión. El cierre remoto tiene un límite de 15 segundos: sin conexión se limpia localmente y se informa que no se confirmó la revocación remota. Los errores de almacenamiento se informan explícitamente.

Validación: `manage.py makemigrations --check --dry-run` sin cambios; `manage.py test lost_pets.test_session_security` (9 pruebas); `manage.py test --verbosity 0` (196 pruebas); `node --test tests/mobile-session.test.cjs` (7 pruebas); exportación Android local con `expo export --platform android --output-dir .expo/session-security-export`. Una primera exportación rechazó un directorio fuera del proyecto; la ruta corregida completó. Revisión independiente de compatibilidad y posibles elusiones sin hallazgos bloqueantes.

Las pruebas rechazan tokens vencidos, revocados, sin huella o de usuarios inactivos, y verifican el flujo real de recuperación de contraseña, cierre repetido, aislamiento entre teléfonos, push después de cierre/cambio de contraseña y respuestas tardías entre cuentas. El login vigente, el acceso autorizado y la otra sesión del mismo usuario siguen funcionando. No se enviaron correos ni push reales desde las pruebas.

Límites: el APK instalado recibe las protecciones del servidor, pero todavía no el nuevo cierre remoto ni la limpieza de interfaz. Debe salir y volver a ingresar manualmente si muestra una sesión inválida. No se generó APK/EAS ni se probó esta versión nueva en teléfono físico. Las operaciones ya autenticadas y en ejecución no se cancelan retrospectivamente por una revocación; el nuevo control se aplica en la próxima autenticación de petición.

## 0.8.1 — Privacidad de avisos y avistamientos ocultos

Se centraliza la visibilidad en `lost_pets/visibility.py`: los detalles, conteos y último avistamiento respetan el estado actual del aviso y avistamiento. Lectura general no concede moderación; staff o permisos explícitos de cambio conservan la revisión. Las notificaciones API se filtran antes del límite de 30 y el envío push vuelve a consultar el estado actual, incluso si recibió objetos anteriores a la ocultación. La respuesta privada sobre una solicitud propia sigue disponible, pero esa excepción nunca incluye avistamientos ocultos.

`lost_pets/media.py` protege las fotos de extraviados en el servidor, también cuando alguien conserva su URL anterior. Resuelve la ruta real antes de autorizar y rechaza variantes ambiguas de Windows. Las fotos públicas continúan disponibles. Para la foto privada de una solicitud propia, la API devuelve una vista previa firmada de cinco minutos, limitada a esa foto, solicitud y sesión vigente; nunca incluye el Bearer reutilizable. Esto conserva el soporte del APK instalado. Las respuestas de archivos usan `no-store`.

Cambios en vistas, API, generación/envío de notificaciones y rutas de archivos; sin migraciones ni cambios de contrato móvil. Pruebas de regresión en `lost_pets/test_hidden_visibility.py`: contenido oculto, contadores, links directos, lectores sin moderación, mapa, cola de notificaciones, respuestas al solicitante, push con objetos antiguos, fotos conocidas, alias de ruta, caducidad/revocación de vistas previas y archivos públicos. La revisión independiente identificó los alias Windows y se añadieron defensas y pruebas. No se enviaron correos ni push reales ni se generó APK.

Validación final: `manage.py test --verbosity 0` pasó 208 pruebas (12 nuevas de privacidad); `manage.py makemigrations --check --dry-run` no detectó cambios; `git diff --check` sin errores. Los casos antes expuestos se filtran o devuelven 404, mientras que las respuestas propias, las revisiones autorizadas y las fotos públicas siguen accesibles.

Límites: no se pueden retirar copias o notificaciones ya descargadas antes de ocultar el contenido. La vista previa privada es un enlace de acceso temporal: quien lo posea puede usarlo durante su vigencia mientras la sesión conserve acceso. La protección cubre las rutas de medios servidas por Django; un futuro almacenamiento/CDN externo deberá aplicar la misma autorización. El cambio no asegura privacidad de fotos de otros módulos, que no pertenecen a este bloque.

## 0.8.2 — Política compartida de contraseñas y conciliación de pendientes

Se habilitan los validadores estándar de Django: mínimo ocho caracteres, rechazo de claves comunes, enteramente numéricas o demasiado similares a los datos de usuario. La configuración alcanza registro web/móvil, altas de colaboradores desde administración y recuperación. `InitialSetupForm` valida explícitamente al primer administrador con el contexto de username/email y conserva exactamente la contraseña ingresada (sin recortar espacios). Los mensajes del registro explican la regla. No se cambian contraseñas actuales ni se revalidan durante login.

Archivos: `config/settings.py`, `organizations/forms.py`, `organizations/setup_forms.py` y nuevas pruebas `organizations/test_password_policy.py`. Se actualiza `LAUNCH_CHECKLIST.md` con los nueve hallazgos originales, sus correcciones y los pendientes reales (DEMO, distribución móvil y verificaciones operativas); el informe sellado permanece intacto.

Validación enfocada: `manage.py test organizations lost_pets.test_session_security --verbosity 0` pasó 52 pruebas. Se comprueban rechazos sin crear cuentas/cambiar hashes, recuperación con clave válida, espacios preservados, bloqueo del bootstrap débil y login con contraseña anterior. `makemigrations --check --dry-run` no detectó cambios. Revisión independiente sin elusiones ni regresiones concretas. Sin migraciones ni APK; no se enviaron correos reales ni se cambiaron credenciales de producción. Esta política no reemplaza límites contra intentos abusivos, revisión de dependencias o control de accesos DEMO, que permanecen pendientes.

Validación final: `manage.py test --verbosity 0` pasó las 214 pruebas; `git diff --check` sin errores.

## 0.8.3 — Accesos DEMO con claves privadas

El generador `lost_pets/management/commands/seed_community_demo.py` deja de asignar o imprimir una contraseña compartida. Las cuentas nuevas quedan sin contraseña utilizable y las existentes conservan su clave al repetir el seed. La clave retirada permanece en el historial Git; quitarla del código no protege por sí solo cuentas existentes.

El nuevo comando `secure_demo_accounts` revisa sin modificar por defecto. En una terminal SSH interactiva, `python manage.py secure_demo_accounts --apply --admin lazuna_admin` solicita y confirma una clave privada diferente para cada una de las cuatro cuentas DEMO conocidas que exista. Exige un administrador real activo con acceso previo, aplica la política Django y rechaza reutilización. No acepta secretos en argumentos ni entrada redirigida. Prepara los hashes antes de una transacción y aborta sin cambios parciales ante cancelación, error o modificación concurrente de las cuentas.

La rotación retira staff/superusuario, revoca tokens móviles y desactiva registros push. El cambio de hash invalida sesiones web anteriores. Conserva actividad, roles institucionales, animales, solicitudes y vínculos; no crea ni elimina cuentas. Es la corrección acotada del generador y de sus accesos heredados, sin alterar usuarios ajenos al listado.

Validación: compilación Python y `git diff --check` correctos; con `DJANGO_SERVE_MEDIA=1`, `manage.py test lost_pets.test_demo_security lost_pets.tests_demo_seed lost_pets.test_session_security --verbosity 0` pasó 19 pruebas. Las ocho pruebas nuevas de `lost_pets/test_demo_security.py` verifican generación sin clave compartida, conservación de clave privada, dry-run, rotación, invalidación web/móvil/push, claves inválidas, cancelación, requisitos de administrador/terminal, cuentas inactivas, rollback y cambios concurrentes. El seed ya no reproduce el acceso compartido; la rotación probada conserva datos y accesos legítimos del administrador. Revisión independiente sin elusiones ni regresiones concretas. No se repitió la suite completa por tratarse de comandos aislados, sin cambios de modelos ni rutas.

Estado: código corregido; cierre operativo pendiente hasta ejecutar la rotación y confirmar su salida en producción. No se verificaron ni cambiaron contraseñas reales desde esta sesión. Sin migraciones ni nuevo APK. La eliminación DEMO continúa programada para después del lanzamiento.

Actualización posterior: el titular confirmó que modificó las claves DEMO correspondientes. No se recibieron ni inspeccionaron contraseñas.

## 0.8.4 — Límites de acceso y recuperación

Los POST de login web, administración Django y API móvil comparten presupuestos previos a autenticar: cinco solicitudes por conexión e identificador, veinte por identificador entre conexiones y sesenta por conexión entre identificadores, en ventanas de quince minutos desde el primer intento. La recuperación permite tres pedidos por correo y diez por conexión en quince minutos. Se cuentan solicitudes válidas e inválidas sin consultar si existe la cuenta; los ingresos correctos no borran el presupuesto. El bloqueo devuelve 429, un mensaje temporal y `Retry-After`; nunca desactiva cuentas ni prolonga la ventana por nuevos intentos bloqueados. La respuesta del límite es igual para correos conocidos y desconocidos, y no envía correo. El flujo normal de recuperación conserva su respuesta genérica de enviado.

Archivos: middleware compartido `organizations/auth_limits.py`, modelo `AuthAttemptBucket` y migración `organizations.0008`, configuración, plantilla `registration/access_wait.html` y reemplazo del límite local de `lost_pets/api.py`. El backend de autenticación, permisos y tokens de recuperación conservan su comportamiento. La API sigue devolviendo `detail` y no requiere cambios del APK instalado. Los cuerpos JSON malformados se rechazan con 400.

Los contadores se guardan en SQLite para sobrevivir reinicios y compartir reservas entre procesos; una escritura inicial obtiene el bloqueo antes de leer y las actualizaciones condicionales reservan cupos antes del hash o SMTP. Se elimina estado vencido en la siguiente solicitud protegida. Las claves son HMAC: no guardan correos, IP ni contraseñas legibles. Se corta al primer presupuesto agotado para que una conexión bloqueada no cree contadores arbitrarios. Si la base de datos falla, se devuelve 503 sin autenticar ni enviar correo.

La conexión se identifica con `REMOTE_ADDR` en instalaciones directas. En Railway, `AUTH_TRUST_RAILWAY_PROXY` usa `X-Real-IP`, que su edge documenta; se activa por `RAILWAY_ENVIRONMENT_ID` y admite override explícito `DJANGO_AUTH_TRUST_RAILWAY_PROXY=0`. No confiar en ese encabezado si se expone directamente el origen o se cambia de proxy. No se usa `X-Forwarded-For`. IPv4 mapeada se unifica con IPv4 e IPv6 se agrupa por /64; encabezados ausentes o ambiguos comparten un presupuesto conservador. Referencia: https://docs.railway.com/networking/public-networking/specs-and-limits#technical-specifications.

Validación ordenada: `git diff --check`, `manage.py check` y `manage.py makemigrations --check --dry-run` correctos. Con `DJANGO_SERVE_MEDIA=1`, `manage.py test organizations.test_auth_limits organizations.tests.EmailLoginTests organizations.tests.PasswordRecoveryTests lost_pets.test_session_security --verbosity 0` pasó 29 pruebas iniciales; `manage.py test --verbosity 0` pasó 235. Tras la corrección de asignaciones posteriores al bloqueo detectada por revisión independiente y la prueba adicional de persistencia, `manage.py test organizations.test_auth_limits --verbosity 0` pasó las 14 pruebas finales. Incluyen bloqueo antes de autenticar/enviar, variantes de identificador, fuentes rotativas, presupuestos compartidos, CSRF, vencimiento, errores de almacenamiento, conexiones simultáneas SQLite en memoria y archivo, y reinicio en proceso separado. Los accesos, redirecciones y recuperación legítimos siguen funcionando. No se enviaron correos reales desde las pruebas.

Límites: defensa de aplicación, no protección contra saturación de red. Una red compartida consume el mismo presupuesto; un ataque distribuido a un identificador puede provocar una espera temporal de ese identificador. Usuario y correo son identificadores separados; no se resuelve su existencia para unificarlos. La respuesta del flujo normal de recuperación no garantiza uniformidad temporal del envío SMTP. El modelo de concurrencia se validó para SQLite, que es la base desplegada; revisar antes de migrar de motor. Sin nuevo APK ni cambios de credenciales.

## 0.8.5 — Dependencias de imágenes y herramientas móviles

Revisión del 2026-11-09 (Argentina), con consultas OSV y npm efectuadas el 2026-11-10 UTC. Los logs del build Railway de 0.8.4 confirmaron Django 5.2.19, Pillow 11.3.0, asgiref 3.12.1, charset-normalizer 3.5.2, et-xmlfile 2.0.0, gunicorn 23.0.0, openpyxl 3.1.5, reportlab 4.5.1, sqlparse 0.6.1 y whitenoise 6.12.0. El entorno Windows anterior tenía versiones distintas de Django/sqlparse: no se usó como evidencia del servidor.

Pillow 11.3.0 coincidió con avisos de decodificación nativa, incluidos [JPEG GHSA-8g5g-8vmr-9782](https://github.com/advisories/GHSA-8g5g-8vmr-9782), [TIFF GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) y [XBM GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8). Aplicabilidad: fotos de usuario alcanzan `Image.open/verify/load` en `patients/image_utils.py`, desde web y API; las credenciales vuelven a decodificar fotos en `patients/credential_pdf.py`. Los límites de tamaño no corrigen fallos nativos del decodificador.

Corrección: `Pillow==13.0.0`, que queda fuera de los rangos afectados consultados, y Docker `python:3.13-slim`, porque Pillow 13 requiere Python >=3.11. Se conserva Django 5.2 LTS y se fijan en `requirements.txt` las versiones directas/indirectas verificadas, incluyendo packaging y tzdata para Windows. La consulta OSV final devolvió cero avisos para las 13 versiones Python fijadas. Esto no demuestra ausencia de fallos desconocidos. No se ejecutaron archivos de explotación; la verificación de remediación consiste en versión corregida frente a rangos oficiales y pruebas de los caminos legítimos.

Móvil: `npm audit --json --ignore-scripts` indicó inicialmente 25 paquetes señalados (5 altos, 19 moderados, 1 bajo), incluyendo avisos propagados por dependencias, no 25 vulnerabilidades independientes del APK. Se actualizaron node-forge 1.4.0→1.4.3, undici 6.29.0→6.29.1, postcss 8.4.49→8.5.32 y ajv 8.11.0→8.20.0. Los dos últimos usan overrides acotados a `@expo/metro-config` y `expo-dev-launcher`; el lock conserva integridades y se instaló sin scripts. Resultado final: 21 paquetes señalados (1 alto, 19 moderados, 1 bajo). No se cambió el SDK Expo 53, React Native, paquete Android ni versión del APK instalado.

Pendientes móviles: `image-size` 1.2.1 es usado por Metro 0.82.5 para leer assets locales del proyecto; los avisos [GHSA-5p2g-fcmc-qvqq](https://github.com/advisories/GHSA-5p2g-fcmc-qvqq) y [GHSA-w3rx-r6r6-pgpr](https://github.com/advisories/GHSA-w3rx-r6r6-pgpr) se corrigen en 2.1.0, pero Metro llama al export CommonJS como función y no se fuerza un salto mayor incompatible. No se demostró explotación desde fotos remotas del APK. Glob/minimatch, uuid/xcode y deepmerge, más sus dependientes Expo, requieren un bloque de migración compatible y reevaluación. Mantener herramientas de desarrollo locales, assets de confianza y no exponer Metro públicamente. No afirmar cierre completo de la revisión móvil ni usar `npm audit fix --force`.

Validación: `docker build -t lazuna-security:0.8.5 .` correcto. En ese Linux/Python 3.13, `manage.py test --verbosity 0` con `DJANGO_SERVE_MEDIA=1` pasó 237 pruebas, sin red, con raíz de solo lectura y datos temporales. `patients/test_image_dependencies.py` verifica JPEG/PNG, EXIF eliminado y la presencia real de imagen en PDF. También pasaron `manage.py check`, `makemigrations --check --dry-run`, migración de base temporal, `collectstatic --noinput`, `pip check` y arranque Gunicorn con HTTP 200 del login. El primer intento completo en Windows terminó sin diagnóstico y no cuenta como prueba aprobada; se sustituyó por la validación Linux del entorno desplegado.

En móvil pasaron 13 pruebas Node de sesión/invitación/búsqueda; `EXPO_OFFLINE=1 node node_modules/expo/bin/cli export --platform android --output-dir .tmp-expo-export/security-085` exportó 724 módulos. `npm ls ajv postcss node-forge undici --all` verificó las versiones y rutas, y `git diff --check` pasó. Revisión independiente sin regresiones concretas. La exportación local no genera APK ni consume un build EAS; no sustituye pruebas físicas o compilación nativa. Sin migraciones nuevas ni cambios de cuentas/datos.

Alcance pendiente: el análisis cubre paquetes Python y el lock npm; no imágenes base/sistema operativo, Gradle, CocoaPods ni inventario binario del APK ya instalado. Los contenedores seguirán recibiendo parches de la rama Python 3.13 al reconstruirse; las versiones de paquetes fijadas requieren revisiones periódicas explícitas.

## Próximo APK — Expo 54 y herramientas corregidas (sin build)

Migración de fuente posterior a 0.8.5, realizada el 2026-11-10 UTC: Expo 54.0.38, React Native 0.81.5, React 19.1.0 y módulos de la matriz `bundledNativeModules.json` de Expo 54. Es el salto acotado que conserva `newArchEnabled: false`; [Expo 54 es la última rama con arquitectura anterior](https://expo.dev/changelog/sdk-54). Se mantienen slug, paquete Android, owner y EAS projectId. No se modifica la versión web 0.8.5 ni el número 0.5.0 del APK instalado; preparar el siguiente número al autorizar su build.

El override acotado a `@expo/metro` alinea sus 14 paquetes en Metro 0.83.8. Ya no existe `image-size` en el lock: `Assets.js` usa el lector interno que excluye ICNS/JXL/HEIF/HEIC también en sus rutas de reconocimiento por contenido. Así se retira el camino de los avisos de bucle infinito del bloque anterior. No se fuerza image-size 2 sobre un consumidor de API 1. Glob 13 se actualiza a 14.0.4 y minimatch 9/10 a 11.0.5 mediante selectores de override; glob 7/minimatch 3 usados por dependencias antiguas se conservan. Las llamadas observadas (`glob`, `globSync`, `Minimatch.match`) se mantienen y se prueban con descubrimiento real de Kotlin y exclusiones/negaciones de Expo.

Cambios de compatibilidad en `mobile/App.js`: SafeAreaProvider/SafeAreaView de safe-area-context en raíz y Modal, preservando la clave de generación que desmonta la sesión; flags actuales `shouldShowBanner/shouldShowList` conservando sonido/badge; selector de fotos `mediaTypes: ["images"]`. No hay llamadas directas al API FileSystem anterior que migrar. Node 22.23.4 queda fijado en `.nvmrc`, engines y los tres perfiles EAS. Se validó con runtime aislado; el Node global 22.12.0 permanece intacto y genera una advertencia al lanzar herramientas recientes desde ese proceso padre.

Auditoría npm: 21 paquetes señalados antes del bloque, 16 tras Expo/Metro (cero altos/críticos), y 12 al corregir glob/minimatch: **0 críticos, 0 altos, 0 moderados, 12 bajos**. Son dependientes de un mismo aviso [deepmerge GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4), no doce defectos independientes de la app. La última versión consultada, 4.3.1, sigue afectada y no hay corrección publicada. Se observó su uso en `@expo/config` para combinar configuración/pluginProps del proyecto durante herramientas de desarrollo; no se demostró una ruta desde datos de usuarios del backend o del APK. Sigue pendiente y no se oculta ni se silencia la auditoría; no procesar configuraciones o plugins no confiables. Esto no equivale a demostrar seguridad completa del runtime nativo.

Validación: instalación de la migración desde lock mediante `npm ci --ignore-scripts --no-audit` con Node 22.23.4; ajustes posteriores glob/minimatch mediante `npm install --ignore-scripts --no-audit`. `npm ls glob minimatch metro --all` sin conflictos; Expo `install --check` correcto; Expo Doctor 18/18 en la combinación final. `expo config --type introspect --json` conserva identidad, arquitectura y bloqueo de RECORD_AUDIO. Exportación Android final con Node 22.23.4: 739 módulos, correcta. Pruebas Node de sesión/invitación/búsqueda y nuevas `tests/mobile-metro.test.cjs`: PNG real e inclusión de assets, rechazo de ICNS con chunk de longitud cero disfrazado como PNG en subproceso limitado a tres segundos, descubrimiento de MainApplication.kt y exclusiones de fingerprint. `git diff --check` correcto. Revisión independiente de Expo/Metro y sus APIs sin regresiones concretas; los ajustes posteriores de glob/minimatch se verificaron con los consumidores anteriores y pruebas enfocadas.

Estado: corrección de dependencias y adaptación móvil preparadas; prueba nativa/distribución pendientes. No se ejecutó EAS Build, no se consumió otro build y no se alteró el APK de ningún teléfono. No se repite la suite Django porque este bloque no cambia backend. La siguiente prueba física debe cubrir cámara/galería, ubicación, notificaciones, biometría/almacenamiento seguro, compartir invitaciones, cambio de cuenta y áreas seguras en Android 16, en vertical/apaisado y navegación por gestos/botones. Siguen pendientes los respaldos/restauración y la limpieza DEMO acordada para después del lanzamiento.
