(() => {
  const button = document.getElementById('business-location');
  if (!button) return;
  const lat = document.getElementById('id_latitude');
  const lon = document.getElementById('id_longitude');
  const confirmed = document.getElementById('id_location_confirmed');
  const status = document.getElementById('business-location-status');
  let generation = 0;
  status.textContent = lat.value && lon.value ? 'El local tiene una ubicación registrada.' : 'Sin ubicación registrada. Podrán encontrarte por nombre y localidad.';
  function clear(message) {
    generation++; lat.value = ''; lon.value = ''; confirmed.value = ''; button.disabled = false;
    status.textContent = message;
  }
  document.getElementById('business-location-clear').addEventListener('click', () => clear('La ubicación se quitará al guardar el perfil.'));
  for (const id of ['id_address', 'id_locality']) {
    document.getElementById(id)?.addEventListener('input', () => clear('Cambiaste la dirección o localidad. Volvé a marcar la ubicación del local antes de guardar.'));
  }
  button.addEventListener('click', () => {
    if (!navigator.geolocation) { status.textContent = 'Este navegador no permite obtener ubicación. Podés guardar la dirección y localidad.'; return; }
    const request = ++generation;
    button.disabled = true; status.textContent = 'Buscando la ubicación del local…';
    navigator.geolocation.getCurrentPosition(position => {
      if (request !== generation) return;
      button.disabled = false;
      const {latitude, longitude, accuracy} = position.coords;
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || accuracy > 1000) {
        status.textContent = 'La ubicación no es suficientemente precisa. Intentá nuevamente desde el local.'; return;
      }
      lat.value = latitude.toFixed(6); lon.value = longitude.toFixed(6);
      confirmed.value = 'true';
      status.textContent = 'Ubicación lista. Confirmá que estás en el local y guardá el perfil para publicarla.';
    }, () => {
      if (request !== generation) return;
      button.disabled = false; status.textContent = 'No se pudo obtener la ubicación. Revisá el permiso del navegador o guardá solo la dirección y localidad.';
    }, {enableHighAccuracy: true, timeout: 15000, maximumAge: 0});
  });
})();
