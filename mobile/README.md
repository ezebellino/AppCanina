# App móvil Comunidad

Cliente móvil Expo. Configurá `EXPO_PUBLIC_API_URL` con la URL HTTPS pública, por ejemplo `https://lazuna.up.railway.app/extraviados/api/v1`, y ejecutá `npm ci` seguido de `npm start` con la versión de Node indicada abajo.

## Migración preparada para el próximo APK

Fuente actual: Expo 54.0.38, React Native 0.81.5 y React 19.1. Usar Node 22.23.4 (`.nvmrc`, engines y perfiles EAS) y `npm ci` para respetar el lock. La instalación global de Node no se actualiza al cambiar estos archivos. Las validaciones se ejecutaron con un runtime aislado de esa versión.

Los overrides mantienen alineados los 14 paquetes de Metro en 0.83.8 bajo `@expo/metro`, sin `image-size`. Glob 13 se sustituye por 14.0.4 y minimatch 9/10 por 11.0.5; las ramas glob 7/minimatch 3 conservan su API antigua. Se mantienen los overrides de postcss/ajv. No quitarlos sin repetir auditoría, exportación y pruebas de compatibilidad. El aviso bajo pendiente de deepmerge se describe en `../RELEASING.md`.

Se conservan la arquitectura anterior, `android.package`, slug, propietario y proyecto EAS. La versión 0.5.0 identifica el APK instalado: esta migración solo está en fuente y se debe preparar el siguiente número antes de construirlo. No ejecutar EAS Build para comprobar esta fuente: usar `npx expo install --check`, `npx expo-doctor` y `npx expo export --platform android --output-dir .tmp-expo-export/check`.

Antes de distribuir el próximo APK, probar cámara/galería (incluida cancelación), permisos y ubicación, biometría/SecureStore, notificaciones, invitación familiar y cierre/cambio de sesión. Revisar login y menú con navegación por gestos/botones y en ambas orientaciones: ahora usan safe-area-context para Android 16. La exportación JavaScript y la introspección de configuración no prueban el comportamiento de módulos nativos en un teléfono.

En un teléfono real no uses `localhost`: debe apuntar al dominio HTTPS de la veterinaria.

La aplicación solicita cámara y ubicación únicamente al tocar **Usar cámara** o **Compartir mi ubicación**. La ubicación se utiliza para el aviso en curso; la API pública conserva solamente una zona aproximada.

Para alertas push en segundo plano, instalá una build Android/iOS (no Expo Go). La aplicación ya está asociada al proyecto EAS `@vasco_88/tu-veterinaria-comunidad`; la persona activa las alertas desde el botón **Activar alertas en este teléfono** y el permiso se solicita solo entonces. Antes de la primera build Android con push, configurá las credenciales FCM del proyecto en Expo/EAS.

## Compartir una ficha con familiares o cuidadores

Desde **Veterinaria → Mis animales**, el responsable puede abrir una ficha y crear un código familiar. **Copiar código** copia únicamente el código; **Compartir código** abre el menú del teléfono para elegir WhatsApp u otra aplicación, con el nombre del animal, instrucciones y vencimiento. La persona destinataria ingresa en **Veterinaria → Vincular mascota familiar** y pega el código para acceder a la misma ficha e historial.

El código conserva su vigencia de 15 minutos y un solo uso. La app impide copiar o compartir códigos vencidos y limpia el código visible al cambiar de animal o cerrar sesión. Puede generar y revocar invitaciones el responsable del animal o un responsable (rol manager) de su refugio verificado. Las fichas del refugio aparecen en Mis animales para ese responsable. Los cuidadores invitados solo consultan la ficha e historial; no administran invitaciones ni consentimiento de viaje. Una invitación pendiente deja de ser válida si quien la emitió pierde su autorización.

Este cambio incorpora `expo-clipboard` y requiere una nueva build nativa para estar disponible en una APK instalada previamente. Validación manual pendiente en teléfono: copiar y pegar el código, compartir por WhatsApp, cancelar el menú, aceptar desde otra cuenta y comprobar que al abrir otro animal no aparece el código anterior.

## Compartir adopciones y colaborar en refugios

Cada tarjeta de Adopciones ofrece **Compartir adopción**. Abre el menú del teléfono (WhatsApp u otras apps) con nombre, especie, raza, edad, zona, descripción, refugio e instrucciones para encontrar la publicación en la app. Comparte texto; no adjunta una foto ni genera un enlace público a la ficha clínica.

Para invitar a un cuidador: el responsable del refugio verificado abre una ficha institucional desde Mis animales, crea un código y lo copia o comparte. El destinatario lo acepta desde Vincular mascota familiar. Se reutiliza la ficha existente y el acceso puede revocarse desde la misma pantalla. Las publicaciones de adopción y las fichas clínicas son registros diferentes: compartir una publicación no crea ni concede acceso clínico.

Entrega pendiente: publicar el backend actualizado antes de distribuir la nueva APK y validar ambos recorridos en dos cuentas reales de prueba. No se generó un build EAS con este cambio.

URL pública: https://lazuna.up.railway.app. Los APK anteriores al cambio de dominio necesitan actualizarse. Conservamos slug, android.package y extra.eas.projectId porque identifican la aplicación existente.
