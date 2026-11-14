const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('appcanina/static/js/success-motion.js', 'utf8');
function run({reduced = false, seen = false, unavailable = false} = {}) {
  const classes = [], reveal = [];
  const element = {dataset: {successMotion: 'visit', motionKey: '1-accepted'}, classList: {add: v => classes.push(v)}, closest: selector => selector === '.toast' ? null : ({classList: {add: v => reveal.push(v)}})};
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

for (const reduced of [false, true]) test(`floating confirmation disappears after 3 seconds, reduced=${reduced}`, () => {
  let timer, delay, removed = false, animation;
  const toast = {remove: () => {removed = true;}, animate: (_frames, options) => {assert.equal(options.duration, 250); animation = {}; return animation;}};
  const element = {dataset: {successMotion: 'found'}, classList: {add() {}}, closest: selector => selector === '.toast' ? toast : null};
  vm.runInNewContext(code, {window: {matchMedia: () => ({matches: reduced})}, document: {querySelectorAll: () => [element]}, setTimeout: (fn, ms) => {timer = fn; delay = ms;}});
  assert.equal(delay, 3000); assert.equal(removed, false);
  timer();
  if (!reduced) {assert.equal(removed, false); animation.onfinish();}
  assert.equal(removed, true);
});
