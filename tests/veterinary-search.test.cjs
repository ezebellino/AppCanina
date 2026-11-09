const {test} = require('node:test');
const assert = require('node:assert/strict');
const {results, distanceKm, validPoint} = require('../appcanina/static/js/veterinary-search.js');
const items = [
  {value:'1', label:'Veterinaria Sol · Córdoba · Calle Uno', lat:-31.4, lon:-64.18},
  {value:'2', label:'Veterinaria Sol · Avellaneda · Mitre 20', lat:-34.66, lon:-58.36},
  {value:'3', label:'Clínica Álamo · Avellaneda', lat:null, lon:null},
];
test('search identifies equal names by city/address and ignores accents', () => {
  assert.equal(results(items,'sol cordoba',null,0)[0].value,'1');
  assert.equal(results(items,'mitre 20',null,0)[0].value,'2');
  assert.equal(results(items,'clinica alamo',null,0)[0].value,'3');
  assert.equal(results(items,'unknown',null,0).length,0);
});
test('nearby sorting and radius do not invent distance for missing coordinates', () => {
  const origin={lat:-34.66,lon:-58.36};
  assert.deepEqual(results(items,'',origin,0).map(x=>x.value),['2','1','3']);
  assert.deepEqual(results(items,'sol',origin,10).map(x=>x.value),['2']);
  assert.equal(results(items,'alamo',origin,10).length,0);
  assert.equal(results(items,'alamo',null,0)[0].distance,null);
});
test('distance is finite at antipodes and accepts valid zero coordinates', () => {
  assert.equal(distanceKm({lat:0,lon:0},{lat:0,lon:0}),0);
  assert.ok(Math.abs(distanceKm({lat:0,lon:0},{lat:0,lon:180})-20015)<2);
  assert.ok(validPoint(0,0));
  for (const point of [[null,0],[91,0],[0,181],[NaN,0],[Infinity,0]]) assert.equal(validPoint(...point),false);
});
