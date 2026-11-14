const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '../appcanina/static/js/adoption-archive.js'), 'utf8');

async function submit(response) {
  let handler, destination;
  const requests = [];
  const status = {textContent: ''};
  const button = {value: 'archive', disabled: false};
  const form = {
    action: button, // Real DOM named-property collision: <button name="action">.
    getAttribute: name => name === 'action' ? '/extraviados/adopciones/archivo/institution/2/' : null,
    parentElement: {querySelector: () => status},
    setAttribute() {}, removeAttribute() {}, closest: () => null,
    addEventListener: (_name, fn) => {handler = fn;},
  };
  const fetch = async (url, options) => {requests.push({url, options}); return response;};
  vm.runInNewContext(script, {
    document: {querySelectorAll: () => [form]}, fetch, URL,
    FormData: class {set() {}},
    location: {href: 'https://lazuna.up.railway.app/extraviados/adopciones/intereses/', origin: 'https://lazuna.up.railway.app'},
    window: {fetch, location: {assign: url => {destination = url;}}},
  });
  await handler({submitter: button, preventDefault() {}});
  return {requests, destination, status, button};
}
const jsonResponse = (data, status = 200) => ({ok: status === 200, status, headers: {get: () => 'application/json'}, json: async () => data});

test('named action button cannot replace the archive endpoint', async () => {
  const result = await submit(jsonResponse({detail: 'Archivada', redirect_url: '/extraviados/adopciones/intereses/'}));
  assert.equal(result.requests[0].url, '/extraviados/adopciones/archivo/institution/2/');
  assert.equal(result.requests[0].options.method, 'POST');
  assert.equal(result.requests[0].options.headers.Accept, 'application/json');
  assert.equal(result.destination, 'https://lazuna.up.railway.app/extraviados/adopciones/intereses/');
});

test('HTML, expired sessions and malformed confirmations show readable errors and enable retry', async () => {
  for (const response of [
    {ok: false, status: 404, headers: {get: () => 'text/html'}, json: async () => {throw SyntaxError('Unexpected token <');}},
    {ok: true, redirected: true},
    {ok: false, status: 403},
    {...jsonResponse({}), json: async () => {throw SyntaxError('Unexpected token <');}},
    jsonResponse({}),
    jsonResponse({redirect_url: 'https://example.com/'}),
  ]) {
    const result = await submit(response);
    assert.equal(result.destination, undefined);
    assert.equal(result.button.disabled, false);
    assert.match(result.status.textContent, /Recargá/);
    assert.doesNotMatch(result.status.textContent, /Unexpected|DOCTYPE|JSON/);
  }
});

test('state conflicts keep the server explanation', async () => {
  const result = await submit(jsonResponse({detail: 'La solicitud cambió. Actualizá la bandeja.'}, 409));
  assert.equal(result.status.textContent, 'La solicitud cambió. Actualizá la bandeja.');
  assert.equal(result.destination, undefined);
  assert.equal(result.button.disabled, false);
});
