# App móvil Comunidad

Cliente Expo inicial. Configurá `EXPO_PUBLIC_API_URL` con la URL HTTPS pública, por ejemplo `https://appcanina-production.up.railway.app/extraviados/api/v1`, y ejecutá `npm install` seguido de `npm start`.

En un teléfono real no uses `localhost`: debe apuntar al dominio HTTPS de la veterinaria.

La aplicación solicita cámara y ubicación únicamente al tocar **Usar cámara** o **Compartir mi ubicación**. La ubicación se utiliza para el aviso en curso; la API pública conserva solamente una zona aproximada.
