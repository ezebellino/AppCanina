const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('appcanina/static/js/success-motion.js', 'utf8');
function run({reduced = false, seen = false, unavailable = false} = {}) {
  const classes = [], reveal = [];
  const element = {dataset: {successMotion: 'visit', motionKey: '1-accepted'}, classList: {add: v => classes.push(v)}, closest: () => ({classList: {add: v => reveal.push(v)}})};
  const context = {window: {matchMedia: () => ({matches: reduced})}, document: {querySelectorAll: () => [element]}, sessionStorage: {getItem: () => {if (unavailable) throw Error(); return seen;}, setItem() {}}};
  vm.runInNewContext(code, context); vm.runInNewContext(code, context);
  return {classes, reveal};
}
test('confirmed visit plays once and reveals instructions', () => {
  const result = run(); assert.deepEqual(result.classes, ['motion-play']); assert.deepEqual(result.reveal, ['motion-reveal']);
});
test('seen and reduced-motion confirmations stay static', () => {
  for (const options of [{seen: true}, {reduced: true}]) assert.deepEqual(run(options), {classes: [], reveal: []});
});
test('storage restrictions do not break confirmation', () => { assert.deepEqual(run({unavailable: true}).classes, ['motion-play']); });
