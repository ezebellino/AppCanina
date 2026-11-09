const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../appcanina/static/js/family-invitation.js'), 'utf8');

function open(hash) {
  const events = [];
  const input = {value: ''};
  const status = {textContent: ''};
  const form = {elements: {namedItem: () => input}, requestSubmit: () => events.push('prepare')};
  vm.runInNewContext(source, {
    URLSearchParams,
    location: {hash, pathname: '/mis-animales/agregar-con-codigo/', search: ''},
    history: {replaceState: (_state, _title, url) => events.push(url)},
    document: {getElementById: id => id === 'family-link-status' ? status : form},
  });
  return {events, input, status};
}

test('link strips secret before posting preparation, never acceptance', () => {
  const result = open('#code=FAM-ABC_123-xyz');
  assert.deepEqual(result.events, ['/mis-animales/agregar-con-codigo/', 'prepare']);
  assert.equal(result.input.value, 'FAM-ABC_123-xyz');
});

test('normal manual page and redirect return do not submit again', () => {
  assert.deepEqual(open('').events, []);
  assert.deepEqual(open('#section').events, []);
});

test('malformed and oversized links are cleared without submitting', () => {
  for (const hash of ['#code=', '#code=%3Cscript%3E', '#code=https://evil.example', '#code=FAM-' + 'A'.repeat(77)]) {
    const result = open(hash);
    assert.deepEqual(result.events, ['/mis-animales/agregar-con-codigo/']);
    assert.equal(result.input.value, '');
    assert.match(result.status.textContent, /no contiene un código válido/);
  }
});
