# App móvil Comunidad

Cliente Expo inicial. Configurá `EXPO_PUBLIC_API_URL` con la URL HTTPS pública, por ejemplo `https://appcanina-production.up.railway.app/extraviados/api/v1`, y ejecutá `npm install` seguido de `npm start`.

En un teléfono real no uses `localhost`: debe apuntar al dominio HTTPS de la veterinaria.

La aplicación solicita cámara y ubicación únicamente al tocar **Usar cámara** o **Compartir mi ubicación**. La ubicación se utiliza para el aviso en curso; la API pública conserva solamente una zona aproximada.

Para alertas push en segundo plano, instalá una build Android/iOS (no Expo Go). La aplicación ya está asociada al proyecto EAS `@vasco_88/tu-veterinaria-comunidad`; la persona activa las alertas desde el botón **Activar alertas en este teléfono** y el permiso se solicita solo entonces. Antes de la primera build Android con push, configurá las credenciales FCM del proyecto en Expo/EAS.
