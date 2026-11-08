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

El destino propuesto es https://lazuna.up.railway.app (sujeto a disponibilidad). El corte de dominio reemplaza la URL gratuita anterior: requiere coordinar el uso del APK instalado y los enlaces viejos. No activar PUBLIC_BASE_URL con un dominio sin verificar.
