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

function harness({reduceMotion = false} = {}) {
  let pushListener;
  const cache = new Map();
  const calls = [];
  const motions = [];
  let handler = () => null;
  const permission = async () => ({status: 'denied'});
  const mocks = {
    'react': React,
    'react-native': {
      AccessibilityInfo: {isReduceMotionEnabled: async () => reduceMotion},
      Animated: {View: 'View', Value: class {interpolate() {return 0;} stopAnimation() {}}, multiply: () => 0, timing: (_value, config) => config, sequence: steps => ({start: done => {motions.push(steps); done({finished: true});}})},
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
    'expo-notifications': {setNotificationHandler() {}, getPermissionsAsync: permission, addNotificationResponseReceivedListener: fn => { pushListener = fn; return {remove() { pushListener = null; }}; }, addNotificationReceivedListener: () => ({remove() {}}), getLastNotificationResponseAsync: async () => null, clearLastNotificationResponseAsync: async () => {}},
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
    async tapPush() { await act(async () => pushListener({notification: {request: {content: {data: {report_id: 999}}}}})); },
    calls, motions, response, setHandler: fn => {handler = fn;},
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


test('tapping push opens authenticated inbox without trusting or reading payload target', async () => {
  const h = harness();
  h.setHandler(url => url.includes('/novedades/?filter=') ? feed(h) : null);
  try {
    await h.start(); await h.tapPush();
    assert.ok(h.contains('Aviso de Luna'));
    assert.equal(h.calls.filter(x => x.url.includes('/avisos/999/') || x.url.endsWith('/leer/')).length, 0);
  } finally { await h.stop(); }
});


test('applicant archives and restores only its own request with the version shown', async () => {
  const h = harness(); let archived = false;
  const item = {id: 7, animal_name: 'Mía', status: 'completed', status_label: 'Adopción concretada', can_archive: true, updated_at: '2026-11-14T10:00:00+00:00', visit_status: 'none'};
  h.setHandler((url, options) => {
    if (url.includes('/adopciones/mis-intereses/')) {
      const showingArchive = url.includes('view=archived');
      return h.response({interests: showingArchive === archived ? [{...item, is_archived: archived}] : [], counts: {all: archived ? 0 : 1, archived: archived ? 1 : 0}});
    }
    if (url.endsWith('/archivo/applicant/7/')) {
      const payload = JSON.parse(options.body);
      assert.equal(payload.expected_updated_at, item.updated_at);
      archived = payload.action === 'archive';
      return h.response({detail: archived ? 'Archivada' : 'Restaurada'});
    }
  });
  try {
    await h.start(); await h.press('Abrir menú'); await h.press('Mi actividad');
    await h.press('Archivar solicitud');
    assert.equal(h.contains('Mía'), false);
    await h.press('Archivadas (1)');
    assert.ok(h.contains('Mía'));
    await h.press('Restaurar en mi bandeja');
    assert.equal(h.contains('Mía'), false);
    await h.press('Mi bandeja (1)');
    assert.ok(h.contains('Mía'));
  } finally { await h.stop(); }
});

test('failed archive keeps request visible and reports conflict', async () => {
  const h = harness();
  h.setHandler(url => {
    if (url.includes('/adopciones/mis-intereses/')) return h.response({interests: [{id: 7, animal_name: 'Mía', status: 'closed', can_archive: true, updated_at: 'old', visit_status: 'none'}]});
    if (url.endsWith('/archivo/applicant/7/')) return h.response({detail: 'La solicitud cambió. Actualizá la bandeja.'}, 409);
  });
  try {
    await h.start(); await h.press('Abrir menú'); await h.press('Mi actividad'); await h.press('Archivar solicitud');
    assert.ok(h.contains('Mía')); assert.ok(h.contains('La solicitud cambió'));
  } finally { await h.stop(); }
});

test('shelter archives via institution scope and retrieves archived requests', async () => {
  const h = harness(); let archived = false;
  const item = {id: 9, animal_name: 'Luna', status: 'closed', status_label: 'No continuó', can_archive: true, updated_at: 'version', visit_status: 'none'};
  h.setHandler((url, options) => {
    if (url.includes('/adopciones/mis-intereses/')) return h.response({interests: [], can_manage_adoption_requests: true});
    if (url.includes('/adopciones/bandeja/?')) return h.response({interests: url.includes('view=archived') === archived ? [{...item, is_archived: archived}] : [], counts: {all: archived ? 0 : 1, archived: archived ? 1 : 0}, status_choices: [], page: 1});
    if (url.endsWith('/archivo/institution/9/')) { archived = JSON.parse(options.body).action === 'archive'; return h.response({detail: 'Guardado'}); }
  });
  try {
    await h.start(); await h.press('Abrir menú'); await h.press('Mi actividad'); await h.press('Solicitudes recibidas');
    await h.press('Archivar solicitud'); assert.equal(h.contains('Luna'), false);
    await h.press('Archivadas (1)'); assert.ok(h.contains('Luna'));
    await h.press('Restaurar en mi bandeja'); assert.equal(h.contains('Luna'), false);
  } finally { await h.stop(); }
});


test('reduced motion still archives without starting animation', async () => {
  const h = harness({reduceMotion: true}); let archived = false;
  h.setHandler(url => {
    if (url.includes('/adopciones/mis-intereses/')) return h.response({interests: archived ? [] : [{id: 7, animal_name: 'Mía', status: 'closed', can_archive: true, updated_at: 'current', visit_status: 'none'}]});
    if (url.endsWith('/archivo/applicant/7/')) {archived = true; return h.response({detail: 'Archivada'});}
  });
  try {
    await h.start(); await h.press('Abrir menú'); await h.press('Mi actividad'); await h.press('Archivar solicitud');
    assert.equal(archived, true); assert.equal(h.motions.length, 0); assert.equal(h.contains('Mía'), false);
  } finally { await h.stop(); }
});
