/* Location stays in memory: never sent to the server or stored in the browser. */
(() => {
  const normalize = text => String(text).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
  const validPoint = (lat, lon) => typeof lat === 'number' && typeof lon === 'number' && Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  function distanceKm(a, b) {
    const rad = Math.PI / 180;
    const dlat = (b.lat - a.lat) * rad, dlon = (b.lon - a.lon) * rad;
    const h = Math.sin(dlat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dlon / 2) ** 2;
    return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
  }
  function results(items, query, origin, radius) {
    const terms = normalize(query).split(/\s+/).filter(Boolean);
    return items.filter(item => terms.every(term => normalize(item.label).includes(term))).map(item => ({
      ...item, distance: origin && validPoint(item.lat, item.lon) ? distanceKm(origin, item) : null,
    })).filter(item => !radius || (item.distance !== null && item.distance <= radius)).sort((a, b) => {
      if (origin && a.distance !== b.distance) return (a.distance ?? Infinity) - (b.distance ?? Infinity);
      return a.label.localeCompare(b.label, 'es') || a.value.localeCompare(b.value);
    });
  }
  if (typeof module !== 'undefined') module.exports = {normalize, validPoint, distanceKm, results};
  if (typeof document === 'undefined') return;
  const select = document.getElementById('id_organization');
  const search = document.getElementById('vet-search');
  if (!select || !search) return;
  const button = document.getElementById('vet-nearby');
  const clear = document.getElementById('vet-clear-location');
  const radius = document.getElementById('vet-radius');
  const radiusField = document.getElementById('vet-radius-field');
  const status = document.getElementById('vet-search-status');
  const items = [...select.options].filter(o => o.value).map(o => ({
    value: o.value, label: o.textContent,
    lat: o.dataset.latitude === undefined ? null : Number(o.dataset.latitude),
    lon: o.dataset.longitude === undefined ? null : Number(o.dataset.longitude),
  }));
  let origin = null, generation = 0;
  function render(message = '') {
    const selected = select.value;
    const found = results(items, search.value, origin, Number(radius.value));
    select.replaceChildren(new Option('Seleccioná una veterinaria', ''));
    for (const item of found) {
      const suffix = origin ? (item.distance === null ? ' · Sin ubicación registrada' : ` · ${item.distance < 1 ? '< 1' : item.distance.toFixed(1)} km aprox.`) : '';
      select.add(new Option(item.label + suffix, item.value));
    }
    select.value = found.some(item => item.value === selected) ? selected : '';
    const removed = selected && !select.value ? ' La selección anterior no coincide con los filtros; elegí nuevamente.' : '';
    status.textContent = `${message}${found.length} ${found.length === 1 ? 'veterinaria disponible.' : 'veterinarias disponibles.'} ${origin ? 'Más cercanas primero; sin ubicación al final.' : ''}${radius.value ? ' El límite de distancia excluye las que no tienen ubicación; elegí Todas las distancias para verlas.' : ''}${removed}`;
  }
  document.getElementById('vet-search-tools').hidden = false;
  search.addEventListener('input', () => render());
  search.addEventListener('keydown', event => { if (event.key === 'Enter') event.preventDefault(); });
  radius.addEventListener('change', () => render());
  clear.addEventListener('click', () => {
    generation++; origin = null; radius.value = ''; radius.disabled = true; radiusField.hidden = true;
    clear.hidden = true; button.disabled = false; render();
  });
  button.addEventListener('click', () => {
    if (!navigator.geolocation) { render('Este navegador no permite obtener tu ubicación. '); return; }
    const request = ++generation;
    button.disabled = true; clear.hidden = false; status.textContent = 'Buscando tu ubicación…';
    navigator.geolocation.getCurrentPosition(position => {
      if (request !== generation) return;
      button.disabled = false;
      const {latitude: lat, longitude: lon} = position.coords;
      if (!validPoint(lat, lon)) { render('No se pudo obtener una ubicación válida. '); return; }
      origin = {lat, lon}; radius.disabled = false; radiusField.hidden = false; render();
    }, () => {
      if (request !== generation) return;
      button.disabled = false; clear.hidden = !origin;
      render('No se pudo acceder a tu ubicación. Podés buscar por nombre o ciudad. ');
    }, {enableHighAccuracy: false, timeout: 10000, maximumAge: 60000});
  });
  render();
})();
