'use strict';

// Pure translation-parser and preservation checks run without a browser. The
// full provider, UI, storage and reload flow remains in check_factory_spanish.py.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const aiSource = fs.readFileSync(path.join(root, 'docs', 'factory', 'ai.js'), 'utf8');
const fakeKey = 'sk-' + 'TEST' + 'FAKE'.repeat(8);
const settings = JSON.stringify({
  provider: 'gemini', model: 'gemini-3.6-flash',
  baseUrl: 'http://localhost:1234/v1', keys: {gemini: fakeKey}
});

class Node {
  constructor() {
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.listeners = {};
    this.dataset = {};
    this.selectedOptions = [];
    this.classList = {add() {}, remove() {}, contains() {return false;}};
  }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setAttribute() {}
  removeAttribute() {}
  replaceChildren() {}
  append() {}
  focus() {}
  showModal() {}
  close() {}
  scrollIntoView() {}
}

const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, new Node());
  return nodes.get(id);
};
node('ai-provider').value = 'gemini';
node('headline').value = 'Headline';
node('contact').value = 'mark@example.test';

const makeStorage = initial => {
  const values = new Map(Object.entries(initial));
  return {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key),
  };
};
const localStorage = makeStorage({'cultureshyft.factory.ai.v1': settings});
const sessionStorage = makeStorage({});
const document = {
  getElementById: node,
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => new Node(),
  addEventListener() {},
};
const payload = {version: 1, values: {headline: 'Headline', subheadline: '', body: '', cta: '', contact: 'mark@example.test'}};
const window = {
  localStorage, sessionStorage,
  factoryBrief: {collect: () => JSON.parse(JSON.stringify(payload))},
  factoryBriefs: {REVIEW_NOTE: 'Review before printing. Have someone who speaks Spanish check this translation.'},
  addEventListener() {},
};
const sandbox = {
  window, document, localStorage, sessionStorage,
  navigator: {onLine: true}, location: {href: 'file:///factory/index.html'},
  URL, URLSearchParams, AbortController, DOMException,
  setTimeout, clearTimeout, console,
};
vm.createContext(sandbox);
vm.runInContext(aiSource, sandbox, {filename: 'ai.js'});

const {parseSpanish, verifySpanishPreservation} = window.factoryAI;
const source = {
  headline: 'CultureShyft neighbors',
  subheadline: 'Media made to move people.',
  body: 'Jordan Lee has 25 tickets at 123 Main Street. Visit https://example.test/path.',
  cta: 'Call 248-505-0050',
};
const translated = {
  headline: 'Vecinos de CultureShyft',
  subheadline: 'Media made to move people.',
  body: 'Jordan Lee tiene 25 boletos en 123 Main Street. Visita https://example.test/path.',
  cta: 'Llama al 248-505-0050',
};

const parsed = parseSpanish(JSON.stringify(translated), source);
assert.deepEqual(JSON.parse(JSON.stringify(parsed)), translated);
const unicode = {...translated, headline: '¿Niñez, sueños y conexión?', cta: '¡Llámanos al 248-505-0050!'};
assert.deepEqual(JSON.parse(JSON.stringify(parseSpanish(JSON.stringify(unicode), source))), unicode);

for (const invalid of [
  '```json\n' + JSON.stringify(translated) + '\n```',
  'Here is the answer: ' + JSON.stringify(translated),
  JSON.stringify({...translated, extra: 'no'}),
  JSON.stringify({headline: translated.headline}),
  JSON.stringify({...translated, body: null}),
]) {
  assert.throws(() => parseSpanish(invalid, source), /invalid_json/);
}

const long = 'Una oración completa. '.repeat(30).trim();
const longResult = parseSpanish(JSON.stringify({...translated, headline: long}), source);
assert.equal(longResult.headline, long, 'overlength text must remain available for manual shortening');
assert(longResult.headline.length > 140);
const padded = parseSpanish(JSON.stringify({...translated, headline: '  Vecinos de CultureShyft  '}), source);
assert.equal(padded.headline, 'Vecinos de CultureShyft', 'outer whitespace should be trimmed');
const echoed = parseSpanish(JSON.stringify({...translated, headline: fakeKey}), source);
assert.equal(echoed.headline, '[key removed]');

assert.deepEqual(JSON.parse(JSON.stringify(verifySpanishPreservation(source.body, translated.body))), []);
for (const unsafe of [
  'Jordan Lee tiene boletos en Main Street.',
  'Jordan Lee tiene 26 boletos en 123 Main Street. Visita https://example.test/path.',
  'Jordan Lee tiene 25 boletos en 124 Main Street. Visita https://example.test/path.',
  'Jordan Lee tiene 25 boletos en 123 Main Street. Visita https://changed.test/path.',
]) {
  assert(verifySpanishPreservation(source.body, unsafe).length > 0, `unsafe translation was not flagged: ${unsafe}`);
}
assert(verifySpanishPreservation(source.headline, 'Vecinos').some(message => /CultureShyft/.test(message)));
assert(verifySpanishPreservation(source.subheadline, 'Medios que mueven a la gente.').some(message => /Media made/.test(message)));

assert(!aiSource.includes('.innerHTML'), 'AI output must never use innerHTML');
assert(aiSource.includes('input.value = value'), 'Spanish output must be inserted as a text control value');
assert(aiSource.includes('original.textContent = spanishPreview.source[field]'), 'English comparison must use textContent');
console.log('PASS AI card D unit checks: strict JSON, Unicode, no truncation, key redaction, preservation warnings and text-only insertion');
