(() => {
  const form = document.querySelector('[data-adoption-filters], [data-adoption-location]');
  if (!form) return;
  const editing = form.hasAttribute('data-adoption-location');
  const lat = form.elements[editing ? 'location_latitude' : 'lat'];
  const lon = form.elements[editing ? 'location_longitude' : 'lon'];
  const status = form.querySelector('[data-location-status]');
  let sequence = 0;
  form.querySelector('[data-use-location]').addEventListener('click', () => {
    const current = ++sequence;
    if (!navigator.geolocation) { status.textContent = 'Este navegador no ofrece ubicación. Podés buscar por localidad.'; return; }
    status.textContent = 'Obteniendo ubicación…';
    navigator.geolocation.getCurrentPosition(position => {
      if (sequence !== current) return;
      lat.value = position.coords.latitude.toFixed(2);
      lon.value = position.coords.longitude.toFixed(2);
      status.textContent = editing ? 'Referencia aproximada lista. Guardá para aplicarla.' : 'Ubicación aproximada lista. Elegí una distancia o dejá Sin límite y aplicá los filtros.';
    }, () => {
      if (sequence === current) status.textContent = 'No pudimos obtener tu ubicación. Podés buscar por localidad o volver a intentarlo.';
    }, {enableHighAccuracy: false, timeout: 10000, maximumAge: 60000});
  });
  form.querySelector('[data-clear-location]').addEventListener('click', () => {
    sequence++;
    lat.value = lon.value = '';
    if (form.elements.radius) form.elements.radius.value = '';
    status.textContent = 'Ubicación quitada. Podés continuar por localidad.';
  });
  document.querySelector('[data-unlimited]')?.addEventListener('click', event => {
    event.preventDefault(); form.elements.radius.value = ''; form.requestSubmit();
  });
})();
