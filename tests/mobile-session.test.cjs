const test = require('node:test');
const assert = require('node:assert/strict');
const {createSessionClient} = require('../mobile/session-client.cjs');
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; };
const reply = (status, data = {}) => ({status, ok: status < 400, json: async () => data});
function setup(fetchImpl, storage = {}) {
  const values = new Map([['community-token', 'old'], ['community-biometric-enabled', 'true']]);
  const notices = [];
  const client = createSessionClient({fetchImpl, logoutUrl: '/logout', timeoutMs: 30,
    storage: {setItemAsync: async (k,v) => values.set(k,v), deleteItemAsync: async k => values.delete(k), ...storage},
    onEnd: notice => notices.push(notice)});
  return {client, values, notices};
}
test('logout revokes remotely, removes saved access, and rejects reuse', async () => {
  const calls = [];
  const {client, values, notices} = setup(async (...args) => {calls.push(args); return reply(200);});
  await client.end('Done', 'old');
  assert.equal(calls[0][1].headers.Authorization, 'Bearer old');
  assert.equal(calls[0][1].method, 'POST');
  assert.equal(values.size, 0);
  assert.deepEqual(notices, ['Done']);
  await assert.rejects(client.request('/animals'), /terminó/);
  await client.end('Again', 'old');
  assert.equal(calls.length, 1);
});
test('401 ends session; permission 403 and login 401 do not', async () => {
  for (const status of [401, 403]) {
    const {client, notices} = setup(async () => reply(status));
    if (status === 401) {
      await assert.rejects(client.request('/animals', {headers:{Authorization:'Bearer old'}}));
      assert.equal(notices.length, 1);
    } else {
      assert.equal((await client.request('/animals', {headers:{Authorization:'Bearer old'}})).status, 403);
      assert.equal(notices.length, 0);
    }
  }
  const {client, notices} = setup(async () => reply(401));
  assert.equal((await client.request('/login')).status, 401);
  assert.equal(notices.length, 0);
});
test('late body and late unauthorized replies cannot affect a replacement account', async () => {
  for (const status of [200, 401]) {
    const pending = deferred();
    const old = setup(async () => pending.promise);
    const request = old.client.request('/animals', {headers:{Authorization:'Bearer old'}});
    const rejected = assert.rejects(request, /terminó/);
    await old.client.end('Closed');
    const next = setup(async () => reply(200, {animal:'new account'}));
    pending.resolve(reply(status, {animal:'old private history'}));
    await rejected;
    assert.equal(old.notices.length, 1);
    assert.deepEqual(await (await next.client.request('/animals')).json(), {animal:'new account'});
    assert.equal(next.notices.length, 0);
  }
  const body = deferred();
  const {client} = setup(async () => ({...reply(200), json: () => body.promise}));
  const pending = client.request('/animals');
  const rejected = assert.rejects(pending, /terminó/);
  await Promise.resolve();
  await client.end('Closed');
  body.resolve({secret: true});
  await rejected;
});
test('logout waits for storage writes and prevents delayed reactivation', async () => {
  const pending = deferred();
  const values = new Map();
  const {client} = setup(async () => reply(200), {
    setItemAsync: async (k,v) => {await pending.promise; values.set(k,v);},
    deleteItemAsync: async k => values.delete(k),
  });
  const writing = client.store('community-token', 'old');
  const rejected = assert.rejects(writing, /terminó/);
  await Promise.resolve(); await Promise.resolve();
  const ending = client.end('Closed');
  pending.resolve();
  await rejected; await ending;
  assert.equal(values.size, 0);
  await assert.rejects(client.store('community-token', 'late'), /terminó/);
});
test('offline logout still clears local access and reports unconfirmed server revocation', async () => {
  const {client, notices, values} = setup(async () => {throw Error('offline');});
  await client.end('Done', 'old');
  assert.equal(values.size, 0);
  assert.match(notices[0], /no pudimos confirmar/);
});
test('hung logout is bounded and still clears local access', async () => {
  const {client, notices, values} = setup((url, {signal}) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(Error('timeout')))));
  await client.end('Done', 'old');
  assert.equal(values.size, 0);
  assert.match(notices[0], /no pudimos confirmar/);
});
test('storage deletion failure is reported, never claimed as successful cleanup', async () => {
  const {client, notices} = setup(async () => reply(200), {deleteItemAsync: async () => {throw Error('storage');}});
  await client.end('Done', 'old');
  assert.match(notices[0], /no pudimos borrar/);
});
