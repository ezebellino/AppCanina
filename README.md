Bienvenidos a mi AppCanina ! 
La idea del proyecto surge para practicar, ya que hace 1 mes (20/12/2024) terminé el Bootcamp Full-Stack de 4Geeks Academy. Quedé muy contento con el contenido y de hecho seguimos aprendiendo. 
Por mi parte, estoy afianzando conceptos aprendidos por medio de práctica, y conociendo nuevas tecnologías para poder compararlas con las que he ido obteniendo en el proceso de aprendizaje. 
Crear esta app surge del momento en que mi pareja, tenía intenciones de crear su propio emprendimiento de peluquería canina, cuidado de mascotas y traslados de estas. Por ende, aprovechando que tengo al 
propietario de la app 24/7 conmigo, decidí empezar a crearla y consultándole a su semejanza, qué le gustaría que tuviese. Obviamente, me gusta mucho ir agregándole cosas sin que ella se entere y que al 
mostrárselas, se sorprenda y disfrute, como así también, me pueda decir si algo no le convenció. 

## Entrega simple para un cliente

1. Instalá y abrí Docker Desktop (sólo la primera vez).
2. Descomprimí esta carpeta en la PC del negocio.
3. Hacé doble clic en `Abrir-Tu-Veterinaria.cmd`.
4. En el navegador, elegí **Configurar mi negocio** y creá la cuenta administradora.

La instalación comienza vacía: no se copian pacientes, productos, ventas ni fotos de demostración. El cliente carga solamente sus propios datos.

Para uso técnico también se puede ejecutar `docker compose up --build -d` desde esta carpeta.

La base de datos y las fotos se guardan en el volumen `appcanina_data`, por lo que reiniciar o actualizar el contenedor no las borra. Para detenerlo: `docker compose down`. Para ver si está saludable: `docker compose ps`.

### Respaldo y restauración

- Para guardar pacientes, ventas, productos, configuración y fotos: hacé doble clic en `Crear-Respaldo.cmd`. El archivo `.zip` se guarda en la carpeta `Respaldos`. Copialo luego a un pendrive, disco externo o almacenamiento seguro.
- Para recuperar una copia: hacé doble clic en `Restaurar-Respaldo.cmd`, pegá la ruta del archivo `.zip` y escribí `RESTAURAR` para confirmar. Antes de reemplazar datos, el asistente genera una copia de seguridad automática de lo que existe actualmente.
- La aplicación se detiene únicamente durante la copia para que la base de datos y las fotos queden sincronizadas. No cierres la ventana hasta ver el mensaje de finalización.

Antes de publicar la aplicación fuera de tu PC, cambiá `DJANGO_SECRET_KEY` en `docker-compose.yml` por una clave privada larga.

### Preparación para acceso móvil por HTTPS

La configuración de producción está lista en `docker-compose.public.yml` y usa Caddy para gestionar HTTPS automáticamente. Todavía no la actives si no tenés un dominio y un servidor público: primero copiá `.env.public.example` como `.env`, completá `APP_DOMAIN` y `DJANGO_SECRET_KEY`, apuntá el DNS del dominio al servidor y verificá que los puertos 80 y 443 estén disponibles. Luego, en el servidor, ejecutá:

`docker compose -f docker-compose.public.yml up --build -d`

La capa HTTPS prepara la app para acceso móvil seguro; la autenticación de colaboradores y las notificaciones push se implementarán antes de abrir el registro a personas externas.

### Datos para una demostración operativa

Con un administrador ya creado, ejecutá `docker compose exec appcanina python manage.py seed_operational_demo`. Agrega 50 productos, 50 pacientes, turnos, servicios y ventas de muestra sin tocar ni duplicar tus registros existentes.
