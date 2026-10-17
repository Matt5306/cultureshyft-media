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

// Address-only mutations: no changed numbers, URLs or brand text can mask this.
for (const address of [
  '123 Main Street, Apt A, Detroit',
  '123 Main St. Apt. A, Detroit, MI',
  '123 Main Street Unit A, Detroit',
  '123 Main Street, Suite A, Detroit',
  '123 Main Street #A, Detroit',
  '123 Main Street, Detroit, MI',
  '123 Main Street, New York, NY 10001',
  '123 Main Street, St. Clair Shores, MI',
]) {
  const english = `Meet at ${address}. Bring a friend.`;
  const spanish = `Ven a ${address}. Trae a alguien.`;
  assert.equal(verifySpanishPreservation(english, spanish).length, 0, address);
  for (const changed of [
    address.replace(/\bA\b/, 'B'),
    address.replace('Detroit', 'Chicago').replace('New York', 'Los Angeles'),
    address.replace('Clair Shores', 'Louis'),
    address.replace(/, (?:Detroit|New York)/, ''),
    address.replace(/,? (?:Apt\.?|Unit|Suite|#) ?A/, ''),
    address.replace('MI', 'OH').replace('NY', 'CA'),
  ].filter(value => value !== address)) {
    const warnings = verifySpanishPreservation(english, `Ven a ${changed}. Trae a alguien.`);
    assert.equal(warnings.length, 1, `Expected only an address warning: ${changed}`);
    assert.match(warnings[0], /address/, changed);
  }
}

// Unit and locality lines separated by line breaks are part of the address.
for (const [english, changed] of [
  ['123 Main Street\nApt A\nDetroit', '123 Main Street\nApt B\nChicago'],
  ['123 Main Street\nApt A\nDetroit', '123 Main Street\nApt B\nDetroit'],
  ['123 Main Street\nApt A\nDetroit', '123 Main Street\nApt A\nChicago'],
  ['123 Main Street\nApt A\nDetroit', '123 Main Street\nDetroit'],
  ['123 Main Street\nApt A\nDetroit', '123 Main Street\nApt A'],
  ['Meet us:\n123 Main Street,\nDetroit, MI\nBring a friend.', 'Ven:\n123 Main Street,\nChicago, MI\nTrae a alguien.'],
  ['Meet us:\n123 Main Street\nSuite A\nSt. Clair Shores, MI 48080', 'Ven:\n123 Main Street\nSuite A\nSt. Louis, MI 48080'],
]) {
  assert.equal(verifySpanishPreservation(english, english.replace('Meet us:', 'Ven:').replace('Bring a friend.', 'Trae a alguien.')).length, 0, `exact copy must not warn: ${english}`);
  const warnings = verifySpanishPreservation(english, changed);
  assert.equal(warnings.length, 1, `Expected only an address warning: ${JSON.stringify(changed)}`);
  assert.match(warnings[0], /address/, changed);
}
// Ordinary prose after a comma or on the next line is not a locality, so
// translating it must not raise a false address warning.
for (const [english, spanish] of [
  ['123 Main Street, bring a friend.', '123 Main Street, trae a un amigo.'],
  ['Meet at 123 Main Street, then grab food.', 'Nos vemos en 123 Main Street, luego vamos a comer.'],
  ['123 Main Street, 7 PM', '123 Main Street, 7 p. m.'],
  ['Meet at 123 Main Street, 7 PM sharp.', 'Nos vemos en 123 Main Street, 7 p. m. en punto.'],
  ['123 Main Street, Saturday.', '123 Main Street, sábado.'],
  ['123 Main Street, Jordan will meet you.', '123 Main Street, Jordan te espera.'],
  ['123 Main Street\nbring a friend', '123 Main Street\ntrae a un amigo'],
  ['123 Main Street, Apt A, then grab food.', '123 Main Street, Apt A, luego vamos a comer.'],
  ['123 Main Street, Detroit, then grab food.', '123 Main Street, Detroit, luego vamos a comer.'],
]) {
  assert.deepEqual(JSON.parse(JSON.stringify(verifySpanishPreservation(english, spanish))), [], `false address warning: ${JSON.stringify(spanish)}`);
}
// Comma-separated city, state and ZIP stay protected next to that prose.
for (const [english, changed] of [
  ['123 Main Street, Detroit, then grab food.', '123 Main Street, Chicago, luego vamos a comer.'],
  ['123 Main Street, Detroit, MI 48226. Bring a friend.', '123 Main Street, Detroit, OH 48226. Trae a alguien.'],
  ['123 Main Street, Apt A, then grab food.', '123 Main Street, Apt B, luego vamos a comer.'],
]) {
  const warnings = verifySpanishPreservation(english, changed);
  assert.equal(warnings.length, 1, `Expected only an address warning: ${changed}`);
  assert.match(warnings[0], /address/, changed);
}

assert(!aiSource.includes('.innerHTML'), 'AI output must never use innerHTML');
assert(aiSource.includes('input.value = value'), 'Spanish output must be inserted as a text control value');
assert(aiSource.includes('original.textContent = spanishPreview.source[field]'), 'English comparison must use textContent');
console.log('PASS AI card D unit checks: strict JSON, Unicode, no truncation, key redaction, preservation warnings and text-only insertion');
