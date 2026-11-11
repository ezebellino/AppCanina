const test = require('node:test');
const assert = require('node:assert/strict');
const {point, distance, searchRegion, mapsUrl, mapHtml} = require('../mobile/search-map.cjs');
const location = (latitude, longitude) => ({public_latitude: latitude, public_longitude: longitude});

test('maps accept only valid public coordinates, including zero', () => {
  assert.equal(point({latitude: -34, longitude: -58}), null);
  for (const p of [location(null, null), location('', 0), location(NaN, 0), location(91, 0), location(0, Infinity)]) {
    assert.equal(mapsUrl(p), null);
  }
  assert.equal(mapsUrl(location(0, 0)), 'https://www.google.com/maps/search/?api=1&query=0,0');
});
test('search area covers all approximate observations with displacement padding', () => {
  const region = searchRegion({points: [location(-34.6, -58.4), location(-34.62, -58.43)]});
  for (const p of region.points) assert.ok(distance(region.center, p) + 300 <= region.radius);
  assert.equal(searchRegion({points: [location(0, 0)]}).radius, 300);
  assert.equal(searchRegion({points: []}).center, null);
});
test('date-line observations stay local and the history is bounded', () => {
  assert.ok(searchRegion({points: [location(0, 179.99), location(0, -179.99)]}).radius < 3000);
  assert.equal(searchRegion({points: Array(100).fill(location(0, 0))}).points.length, 20);
});
test('map HTML contains no report text, private fields or interpolated markup', () => {
  const html = mapHtml({points: [{...location(0, 0), area: '</script><script>alert(1)</script>', latitude: 42, longitude: 43}]});
  assert.ok(html.includes('OpenStreetMap'));
  assert.ok(!html.includes('alert(1)'));
  assert.ok(!html.includes('[42,43]'));
  assert.equal(mapHtml({points: []}), '');
});
