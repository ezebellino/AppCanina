const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const Module = require('node:module');
const root = path.resolve(__dirname, '..');
const mobile = Module.createRequire(path.join(root, 'mobile/package.json'));
const review = Module.createRequire(path.join(root, 'tmp/mobile-review/package.json'));
const React = review('react');
const {create, act} = review('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT = true;
function component(copy) {
  const filename = path.join(root, 'mobile/ShelterDonation.js');
  const compiled = new Module(filename, module);
  compiled.require = name => ({react: React, 'react-native': {
    View: 'View', Text: 'Text', Pressable: 'Pressable', StyleSheet: {create: x => x},
  }, 'expo-clipboard': {setStringAsync: copy}}[name] || mobile(name));
  const code = mobile('@babel/core').transformSync(fs.readFileSync(filename, 'utf8'), {
    filename, babelrc: false, configFile: false,
    presets: [mobile.resolve('@babel/preset-react')],
    plugins: [mobile.resolve('@babel/plugin-transform-modules-commonjs')],
  }).code;
  compiled._compile(code, filename);
  return compiled.exports.default;
}
test('donation copies exact alias and handles clipboard denial', async () => {
  for (const outcome of ['success', 'false', 'throw']) {
    let copied;
    const Donation = component(async value => {
      copied = value;
      if (outcome === 'throw') throw Error('denied');
      return outcome !== 'false';
    });
    let renderer;
    await act(async () => {renderer = create(React.createElement(Donation, {
      organization: {name: 'Refugio', donation_alias: 'refugio.patitas', donation_message: 'Gracias'},
    }));});
    await act(async () => {await renderer.root.findByType('Pressable').props.onPress();});
    assert.equal(copied, 'refugio.patitas');
    assert.ok(JSON.stringify(renderer.toJSON()).includes(outcome === 'success' ? 'Alias copiado' : 'No pudimos copiarlo'));
    await act(async () => renderer.unmount());
  }
});
test('missing institution or alias does not offer donations', async () => {
  const Donation = component(async () => {throw Error('must not copy');});
  for (const organization of [null, {name: 'Refugio', donation_alias: ''}]) {
    let renderer;
    await act(async () => {renderer = create(React.createElement(Donation, {organization}));});
    assert.equal(renderer.toJSON(), null);
    await act(async () => renderer.unmount());
  }
});
