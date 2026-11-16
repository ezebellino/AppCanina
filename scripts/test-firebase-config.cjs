const test = require('node:test');
const assert = require('node:assert/strict');
const configure = require('../mobile/app.config.js');
const base = require('../mobile/app.json').expo;

test('local and EAS file configuration preserve app identity and plugins', () => {
  const original = process.env.GOOGLE_SERVICES_JSON;
  try {
    for (const filename of [undefined, '/tmp/eas/GOOGLE_SERVICES_JSON']) {
      if (filename) process.env.GOOGLE_SERVICES_JSON = filename;
      else delete process.env.GOOGLE_SERVICES_JSON;
      const result = configure({config: base});
      assert.equal(result.android.googleServicesFile, filename || './google-services.json');
      assert.equal(result.android.package, base.android.package);
      assert.deepEqual(result.extra, base.extra);
      assert.deepEqual(result.plugins, base.plugins);
      assert.equal(base.android.googleServicesFile, undefined);
    }
  } finally {
    if (original === undefined) delete process.env.GOOGLE_SERVICES_JSON;
    else process.env.GOOGLE_SERVICES_JSON = original;
  }
});
