const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('selection fills data, preserves event details and uploaded photo, clears unlinked data', () => {
  const element = (props = {}) => ({ value: '', listeners: {},
    addEventListener(type, fn) { this.listeners[type] = fn; },
    removeAttribute(name) { delete this[name]; }, ...props });
  const nodes = {
    'linked-animal-data': element({ textContent: JSON.stringify({
      1: { name: 'Alelí', species: 'cat', breed: 'Mestiza', photo: '/private/cat.png' },
      2: { name: 'Otro', species: 'dog', breed: '', photo: '' },
    }) }),
    id_patient: element(), id_name: element({ value: 'Corrección del usuario' }),
    id_species: element(), id_breed: element(), id_photo: element({ files: [] }),
    'animal-photo-preview': element(), 'animal-photo-help': element(),
    id_area_label: element({ value: 'Plaza' }), id_description: element({ value: 'Collar rojo' }),
  };
  vm.runInNewContext(fs.readFileSync('appcanina/static/js/lost-pet-prefill.js', 'utf8'), {
    document: { getElementById: id => nodes[id] },
  });
  assert.equal(nodes.id_name.value, 'Corrección del usuario');
  nodes.id_patient.value = '1';
  nodes.id_patient.listeners.change();
  assert.equal(nodes.id_name.value, 'Alelí');
  assert.equal(nodes.id_species.value, 'cat');
  assert.equal(nodes['animal-photo-preview'].src, '/private/cat.png');
  assert.equal(nodes.id_area_label.value, 'Plaza');
  assert.equal(nodes.id_description.value, 'Collar rojo');
  nodes.id_photo.files = [{}];
  nodes.id_photo.listeners.change();
  assert.equal(nodes['animal-photo-preview'].hidden, true);
  nodes.id_patient.value = '2';
  nodes.id_patient.listeners.change();
  assert.equal(nodes.id_name.value, 'Otro');
  assert.equal(nodes.id_photo.files.length, 1);
  nodes.id_patient.value = '';
  nodes.id_patient.listeners.change();
  assert.equal(nodes.id_name.value, '');
  assert.equal(nodes['animal-photo-preview'].src, undefined);
});
