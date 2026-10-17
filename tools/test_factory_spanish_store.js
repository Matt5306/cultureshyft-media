'use strict';

// Separate-draft persistence checks run without a browser. The full visible UI
// and provider flow remains covered by check_factory_spanish.py.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const factory = path.resolve(__dirname, '../docs/factory');
const draftKey = 'cultureshyft.factory.draft.v1';
const libraryKey = 'cultureshyft.factory.briefs.v1';
const reviewNote = 'Review before printing. Have someone who speaks Spanish check this translation.';
const clone = value => JSON.parse(JSON.stringify(value));

const englishPayload = () => ({
  version: 1,
  values: {
    layout: 'event', headline: 'CultureShyft neighbors', subheadline: 'Media made to move people.',
    date: 'October 24 at 2 PM', place: '123 Main Street',
    body: 'Jordan Lee has 25 tickets.', cta: 'Call 248-505-0050',
    contact: 'mark@example.test', qrUrl: 'https://example.test/',
    clientName: 'Private customer', clientEmail: 'private@example.test',
    accent: true, printReady: false, rush: false, extraSizes: '3', extraEdits: '0',
  },
  photo: {dataUrl: 'data:image/png;base64,AAAA', focusX: 0.25, focusY: 0.75, zoom: 1.4},
});

function harness(initial = {}, rejectWrites = false) {
  const storage = new Map(Object.entries(initial));
  let pendingSave = null;
  const nodes = new Map();
  class Node {
    constructor() {
      this.children = []; this.textContent = ''; this.listeners = {}; this.hidden = false;
      this.className = ''; this.files = []; this.value = '';
      this.classList = {add() {}, remove() {}, contains() {return false;}};
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    setAttribute() {}
    focus() {}
    click() { this.listeners.click?.(); }
    remove() {}
    querySelector(selector) { return this.children.find(child => child.className === selector.slice(1)); }
  }
  const document = {
    body: new Node(),
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, new Node()); return nodes.get(id); },
    createElement() { return new Node(); },
    addEventListener() {},
  };
  let current = englishPayload();
  const originalBrief = {
    collect: () => clone(current),
    apply: value => { current = clone(value); },
  };
  const window = {
    factoryBrief: originalBrief,
    addEventListener() {}, dispatchEvent() {},
  };
  const localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem(key, value) {
      if (rejectWrites) throw new Error('Quota exceeded');
      storage.set(key, String(value));
    },
  };
  const sandbox = {
    window, document, localStorage, location: {search: '', hash: ''},
    URLSearchParams, URL, Blob, console,
    setTimeout(callback) { pendingSave = callback; return 1; },
    clearTimeout() { pendingSave = null; },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  };
  window.localStorage = localStorage;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(factory, 'briefs.js'), 'utf8'), sandbox, {filename: 'briefs.js'});
  return {
    window, nodes, storage,
    current: () => clone(current),
    tick: () => pendingSave?.(),
    reject: value => { rejectWrites = value; },
  };
}

const healthy = harness();
healthy.window.factoryBriefs.saveCurrent();
const englishOpen = healthy.window.factoryBrief.collect();
const englishDraft = healthy.storage.get(draftKey);
const englishLibrary = clone(JSON.parse(healthy.storage.get(libraryKey)));
assert.equal(englishLibrary.length, 1);

const spanish = clone(englishOpen);
Object.assign(spanish.values, {
  headline: '¿Sueñas con una comunidad más unida?',
  subheadline: 'Media made to move people.',
  body: 'Niñas, niños y familias con Jordan Lee y 25 boletos.',
  cta: '¡Llama al 248-505-0050!',
});
spanish.translation = {
  language: 'es', reviewNote,
  name: 'CultureShyft neighbors (Spanish)',
  social: {
    instagramCaption: '¿Mañana? Sí. Cultura, conexión y niñez.',
    facebookDescription: '¡Acompáñanos con CultureShyft!',
  },
};

healthy.reject(true);
assert.equal(healthy.window.factoryBriefs.saveSeparate(spanish), false);
assert.deepEqual(healthy.window.factoryBrief.collect(), englishOpen, 'failed separate save changed open English flyer');
assert.equal(healthy.storage.get(draftKey), englishDraft, 'failed separate save changed English autosave');
assert.deepEqual(JSON.parse(healthy.storage.get(libraryKey)), englishLibrary, 'failed separate save changed English library entry');

healthy.reject(false);
assert.equal(healthy.window.factoryBriefs.saveSeparate(spanish), true);
assert.deepEqual(healthy.window.factoryBrief.collect(), englishOpen, 'separate save changed open English flyer');
assert.equal(healthy.storage.get(draftKey), englishDraft, 'separate save changed English autosave');
const library = JSON.parse(healthy.storage.get(libraryKey));
assert.equal(library.length, 2);
assert.deepEqual(library[1], englishLibrary[0], 'separate save changed existing English entry');
assert.deepEqual(library[0].payload, spanish);
for (const field of ['date', 'place', 'contact', 'qrUrl', 'clientName', 'clientEmail', 'extraSizes']) {
  assert.equal(library[0].payload.values[field], englishOpen.values[field], `fixed field changed: ${field}`);
}
assert.deepEqual(library[0].payload.photo, englishOpen.photo, 'photo/crop changed in separate draft');
assert.equal(library[0].payload.translation.reviewNote, reviewNote);
for (const character of ['ñ', '¿', '¡', 'á']) {
  assert(JSON.stringify(library[0].payload).includes(character), `Unicode character did not survive save: ${character}`);
}

healthy.window.factoryBriefs.openDrawer();
const cards = healthy.nodes.get('brief-list').children;
const spanishCard = cards.find(card => card.children[0].children[0].textContent.endsWith('(Spanish)'));
assert(spanishCard, 'Spanish saved card was not rendered');
assert.equal(spanishCard.children[0].children[2].textContent, reviewNote, 'saved entry review note is not always visible');
spanishCard.children[1].children[0].listeners.click();
assert.deepEqual(clone(healthy.window.factoryBrief.collect()), spanish, 'opening Spanish entry lost translation metadata');
healthy.tick();
const spanishDraft = healthy.storage.get(draftKey);
assert.deepEqual(JSON.parse(spanishDraft).payload, spanish);

const reloaded = harness({[draftKey]: spanishDraft, [libraryKey]: healthy.storage.get(libraryKey)});
assert.deepEqual(clone(reloaded.window.factoryBrief.collect()), spanish, 'reload lost Spanish text or metadata');
assert.equal(reloaded.nodes.get('brief-translation-note').textContent, reviewNote);
assert.equal(reloaded.nodes.get('brief-translation-note').hidden, false);
console.log('PASS AI card D store checks: separate save, blocked storage, fixed fields, note/social Unicode and reload round-trip');
