const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const repo = path.resolve(__dirname, '..');
const mobileRequire = Module.createRequire(path.join(repo, 'mobile/package.json'));
const reviewRequire = Module.createRequire(path.join(repo, 'tmp/mobile-review/package.json'));
const React = reviewRequire('react');
const {create, act} = reviewRequire('react-test-renderer');
const babel = mobileRequire('@babel/core');
global.IS_REACT_ACT_ENVIRONMENT = true;

function harness() {
  const cache = new Map();
  const calls = [];
  let handler = () => null;
  const permission = async () => ({status: 'denied'});
  const mocks = {
    'react': React,
    'react-native': {
      ...Object.fromEntries(['View', 'Text', 'Image', 'ScrollView', 'TextInput', 'Pressable'].map(x => [x, x])),
      Modal: ({visible, children}) => visible ? children : null,
      Platform: {OS: 'android'}, StyleSheet: {create: x => x},
      AppState: {currentState: 'active', addEventListener: () => ({remove() {}})},
      Linking: {openURL: async () => {}}, Share: {share: async () => {}},
    },
    'react-native-safe-area-context': {SafeAreaProvider: 'View', SafeAreaView: 'View'},
    'react-native-webview': {WebView: 'View'},
    'expo-secure-store': {getItemAsync: async key => key === 'community-token' ? 'test-token' : null, setItemAsync: async () => {}, deleteItemAsync: async () => {}},
    'expo-local-authentication': {hasHardwareAsync: async () => false, isEnrolledAsync: async () => false},
    'expo-notifications': {setNotificationHandler() {}, getPermissionsAsync: permission},
    'expo-image-picker': {getCameraPermissionsAsync: permission},
    'expo-location': {getForegroundPermissionsAsync: permission},
    'expo-constants': {expoConfig: {version: 'review'}},
    'expo-device': {modelName: 'Test'}, 'expo-clipboard': {},
  };
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const compiled = new Module(filename, module);
    cache.set(filename, compiled);
    compiled.filename = filename;
    compiled.require = name => {
      if (mocks[name]) return mocks[name];
      if (name.startsWith('react/')) return reviewRequire(name);
      if (name.startsWith('.')) {
        let target = path.resolve(path.dirname(filename), name);
        if (!path.extname(target)) target += '.js';
        return target.endsWith('.cjs') ? require(target) : load(target);
      }
      return mobileRequire(name);
    };
    const code = babel.transformSync(fs.readFileSync(filename, 'utf8'), {
      filename, babelrc: false, configFile: false,
      presets: [mobileRequire.resolve('@babel/preset-react')],
      plugins: [mobileRequire.resolve('@babel/plugin-transform-modules-commonjs')],
    }).code;
    compiled._compile(code, filename);
    return compiled.exports;
  }
  const response = (data, status = 200) => ({ok: status < 400, status, json: async () => data});
  global.fetch = async (url, options) => {
    calls.push({url, options});
    const custom = handler(url, options);
    if (custom) return await custom;
    if (url.includes('count_only')) return response({unread_count: 2});
    if (url.endsWith('/avisos/')) return response({reports: []});
    if (url.includes('/dispositivos/permisos/')) return response({permissions: {}});
    throw Error(`Unexpected test request: ${url}`);
  };
  let renderer;
  return {
    calls, response, setHandler: fn => {handler = fn;},
    async start() { const App = load(path.join(repo, 'mobile/App.js')).default; await act(async () => {renderer = create(React.createElement(App));}); },
    async press(label) {
      const found = renderer.root.findAllByType('Pressable').find(node => node.props.accessibilityLabel?.startsWith(label) || node.findAllByType('Text').some(text => typeof text.props.children === 'string' && text.props.children === label));
      assert.ok(found, `Button ${label} exists`);
      assert.ok(!found.props.disabled, `Button ${label} enabled`);
      await act(async () => { found.props.onPress(); });
    },
    contains(text) { return JSON.stringify(renderer.toJSON()).includes(text); },
    async stop() { if (renderer) await act(async () => renderer.unmount()); },
  };
}
const notice = {key: 'community-1', title: 'Aviso de Luna', body: 'Plaza', activity_at: '2026-11-11T10:00:00Z', category: 'Búsquedas', unread: true};
function feed(h) { return h.response({notifications: [notice], has_next: false, unread_count: 1}); }

test('notification opens report before acknowledging reading', async () => {
  const h = harness();
  h.setHandler(url => {
    if (url.includes('/novedades/?filter=')) return feed(h);
    if (url.endsWith('/novedades/community-1/')) return h.response({target: 'report', report_id: 5, activity_at: notice.activity_at});
    if (url.endsWith('/avisos/5/')) return h.response({report: {id: 5, name: 'Luna encontrada', species: 'Perro', status: 'resolved'}});
    if (url.endsWith('/leer/')) return h.response({});
  });
  try {
    await h.start(); await h.press('Notificaciones,'); await h.press('Ver novedad');
    assert.ok(h.contains('Luna encontrada'));
    const urls = h.calls.map(x => x.url);
    assert.ok(urls.findIndex(x => x.endsWith('/avisos/5/')) < urls.findIndex(x => x.endsWith('/leer/')));
    assert.equal(h.calls.filter(x => x.url.endsWith('/leer/')).length, 1);
  } finally { await h.stop(); }
});

test('failed target stays unread and shows retryable error', async () => {
  const h = harness();
  h.setHandler(url => {
    if (url.includes('/novedades/?filter=')) return feed(h);
    if (url.endsWith('/novedades/community-1/')) return h.response({target: 'report', report_id: 5});
    if (url.endsWith('/avisos/5/')) return h.response({detail: 'El aviso ya no está disponible.'}, 404);
  });
  try {
    await h.start(); await h.press('Notificaciones,'); await h.press('Ver novedad');
    assert.ok(h.contains('El aviso ya no está disponible.'));
    assert.equal(h.calls.filter(x => x.url.endsWith('/leer/')).length, 0);
  } finally { await h.stop(); }
});

test('leaving notifications discards a late target and never acknowledges it', async () => {
  const h = harness(); let resolve;
  const pending = new Promise(r => {resolve = r;});
  h.setHandler(url => {
    if (url.includes('/novedades/?filter=')) return feed(h);
    if (url.endsWith('/novedades/community-1/')) return pending;
  });
  try {
    await h.start(); await h.press('Notificaciones,'); await h.press('Ver novedad');
    await h.press('Abrir menú'); await h.press('Panel');
    await act(async () => resolve(h.response({target: 'adoption', interest: {id: 12, animal_name: 'Late animal'}})));
    assert.equal(h.contains('Late animal'), false);
    assert.equal(h.calls.filter(x => x.url.endsWith('/leer/')).length, 0);
  } finally { await h.stop(); }
});

test('old adoption list cannot replace the request selected through a notification', async () => {
  const h = harness(); let resolve;
  const pending = new Promise(r => {resolve = r;});
  h.setHandler(url => {
    if (url.endsWith('/adopciones/mis-intereses/')) return pending;
    if (url.includes('/novedades/?filter=')) return feed(h);
    if (url.endsWith('/novedades/community-1/')) return h.response({target: 'adoption', activity_at: notice.activity_at, interest: {id: 12, animal_name: 'Selected animal', species: 'Perro', status: 'received', status_label: 'Recibido', visit_status: 'none'}});
    if (url.endsWith('/leer/')) return h.response({});
  });
  try {
    await h.start(); await h.press('Abrir menú'); await h.press('Mi actividad');
    await h.press('Notificaciones,'); await h.press('Ver novedad');
    await act(async () => resolve(h.response({interests: [{id: 99, animal_name: 'Stale animal', visit_status: 'none'}]})));
    assert.ok(h.contains('Selected animal')); assert.equal(h.contains('Stale animal'), false);
  } finally { await h.stop(); }
});
