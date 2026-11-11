// Only public, displaced coordinates are accepted. Raw latitude/longitude are ignored.
function point(location) {
  const latitude = location?.public_latitude;
  const longitude = location?.public_longitude;
  return typeof latitude === 'number' && typeof longitude === 'number' &&
    Number.isFinite(latitude) && Number.isFinite(longitude) && Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180
    ? {latitude, longitude, seen_at: location.seen_at, area: location.area} : null;
}
const rad = value => value * Math.PI / 180;
function distance(a, b) {
  const h = Math.sin(rad(b.latitude - a.latitude) / 2) ** 2 +
    Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(rad(b.longitude - a.longitude) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}
function searchRegion(data) {
  const points = (Array.isArray(data?.points) ? data.points : []).slice(0, 20).map(point).filter(Boolean);
  if (!points.length) return {points, center: null, radius: 0};
  const reference = points[0].longitude;
  const unwrapped = points.map(p => reference + ((p.longitude - reference + 540) % 360 - 180));
  const center = {
    latitude: (Math.min(...points.map(p => p.latitude)) + Math.max(...points.map(p => p.latitude))) / 2,
    longitude: ((Math.min(...unwrapped) + Math.max(...unwrapped)) / 2 + 540) % 360 - 180,
  };
  // Pad the displayed area for the deliberate ~200-280m displacement, not an animal movement prediction.
  const radius = Math.ceil((Math.max(...points.map(p => distance(center, p))) + 300) / 50) * 50;
  return {points, center, radius};
}
function mapsUrl(location) {
  const coordinate = point(location);
  return coordinate ? `https://www.google.com/maps/search/?api=1&query=${coordinate.latitude},${coordinate.longitude}` : null;
}
function mapHtml(data) {
  const region = searchRegion(data);
  if (!region.center) return '';
  // Never interpolate report text, URLs, tokens or private coordinates into HTML.
  const coordinates = region.points.map(p => [p.latitude, p.longitude]);
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' https://unpkg.com; style-src 'unsafe-inline' https://unpkg.com; img-src https://tile.openstreetmap.org data:; connect-src 'none'">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<style>html,body,#map{height:100%;margin:0;background:#edf4ef}#notice{position:absolute;z-index:999;top:10px;left:12px;background:white;padding:8px;border-radius:8px;font:14px sans-serif}</style></head>
<body><div id="map" role="img" aria-label="Mapa de ubicaciones aproximadas"></div><div id="notice">Cargando mapa…</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
try {
const points=${JSON.stringify(coordinates)};
const map=L.map('map').setView([${region.center.latitude},${region.center.longitude}],14);
const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors'}).addTo(map);
tiles.on('tileerror',()=>{document.getElementById('notice').textContent='Mapa sin conexión. Podés abrir la ubicación en Maps.';document.getElementById('notice').style.display='block';});
tiles.on('load',()=>{document.getElementById('notice').style.display='none';});
const circle=L.circle([${region.center.latitude},${region.center.longitude}],{radius:${region.radius},color:'#287d58',fillOpacity:0.12}).addTo(map);
points.forEach((p,i)=>L.circleMarker(p,{radius:i===0?9:6,color:i===0?'#b44821':'#287d58',fillOpacity:0.85}).bindPopup(i===0?'Última ubicación con coordenadas (aproximada)':'Avistamiento aproximado').addTo(map));
map.fitBounds(circle.getBounds(),{padding:[20,20],maxZoom:15});
window.ReactNativeWebView?.postMessage('ready');
}catch(e){console.error('Map initialization failed',e);document.getElementById('notice').textContent='No se pudo cargar el mapa. Usá el botón de Maps.';window.ReactNativeWebView?.postMessage('error');}
</script></body></html>`;
}
module.exports = {point, distance, searchRegion, mapsUrl, mapHtml};
