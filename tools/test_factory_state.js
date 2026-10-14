'use strict';

// Persistence failure paths run without a browser; browser interactions remain
// in check_factory_browser.py and the main acceptance command.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const factory = path.resolve(__dirname, '../docs/factory');
const draftKey = 'cultureshyft.factory.draft.v1';
const libraryKey = 'cultureshyft.factory.briefs.v1';
const clone = value => JSON.parse(JSON.stringify(value));
const payload = () => ({version: 1, values: {layout: 'poster', headline: 'Keep my work', contact: 'mark@example.com', accent: true}, photo: {dataUrl: '', focusX: 0, focusY: 1, zoom: 1.8}});

function harness(initial = {}) {
  const storage = new Map(Object.entries(initial));
  let rejectWrites = false;
  const nodes = new Map();
  class Node {
    constructor() { this.children = []; this.textContent = ''; this.listeners = {}; this.classList = {add() {}, remove() {}, contains() {return false;}}; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    setAttribute() {}
    focus() {}
    querySelector(selector) {return this.children.find(child => child.className === selector.slice(1));}
  }
  const document = {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, new Node()); return nodes.get(id); },
    createElement() {return new Node();},
    addEventListener() {},
  };
  let current = payload();
  const window = {addEventListener() {}, dispatchEvent() {}, factoryBrief: {collect: () => clone(current), apply: value => {current = clone(value);}}};
  const sandbox = {window, document, location: {search: ''}, URLSearchParams, URL, Blob, console,
    setTimeout() {return 1;}, clearTimeout() {},
    CustomEvent: class {constructor(type, options) {this.type = type; this.detail = options?.detail;}},
    localStorage: {getItem: key => storage.get(key) ?? null, setItem(key, value) {if (rejectWrites) throw new Error('Quota exceeded'); storage.set(key, value);}},
  };
  vm.createContext(sandbox);
  for (const file of ['photo.js', 'briefs.js']) vm.runInContext(fs.readFileSync(path.join(factory, file), 'utf8'), sandbox, {filename: file});
  return {window, nodes, storage, current: () => current, reject: () => {rejectWrites = true;}};
}

const healthy = harness();
assert.equal(healthy.window.factoryBriefs.flush(), true);
assert.deepEqual(JSON.parse(healthy.storage.get(draftKey)).payload, payload());
const recovered = harness({[draftKey]: healthy.storage.get(draftKey)});
assert.deepEqual(recovered.current(), payload(), 'reload must restore full brief and crop');
healthy.reject();
const beforeFailure = healthy.storage.get(draftKey);
assert.equal(healthy.window.factoryBriefs.flush(), false);
assert.equal(healthy.storage.get(draftKey), beforeFailure, 'quota failure must preserve the previous save');
assert.match(healthy.nodes.get('save-status').textContent, /export/i);

for (const damaged of ['{broken JSON', '{"not":"a list"}', '[{"id":"old","payload":null}]']) {
  const instance = harness({[libraryKey]: damaged});
  instance.window.factoryBriefs.saveCurrent();
  assert.equal(instance.storage.get(libraryKey), damaged, 'damaged library must never be silently replaced');
}
const badDraft = '{"payload":{"version":99,"values":{}}}';
const damagedDraft = harness({[draftKey]: badDraft});
assert.equal(damagedDraft.window.factoryBriefs.flush(), false);
assert.equal(damagedDraft.storage.get(draftKey), badDraft);

const deletion = harness();
deletion.window.factoryBriefs.saveCurrent();
const savedCard = deletion.nodes.get('brief-list').children[0];
savedCard.children[1].children[2].listeners.click(); // Delete shows inline choices.
assert.equal(JSON.parse(deletion.storage.get(libraryKey)).length, 1);
savedCard.children[2].children[2].listeners.click(); // Explicit Remove.
assert.equal(JSON.parse(deletion.storage.get(libraryKey)).length, 0);
assert.equal(deletion.window.factoryBriefs.flush({keepInLibrary: true}), true);
assert.equal(JSON.parse(deletion.storage.get(libraryKey)).length, 0, 'switching briefs must not resurrect a deleted flyer');

const validate = healthy.window.factoryBriefs.validateImport;
assert.deepEqual(clone(validate({payload: payload()})), payload());
for (const invalid of [null, {version: 2, values: {}}, {version: 1, values: {headline: 42}}, {version: 1, values: {layout: 'surprise'}}, {version: 1, values: {headline: 'x'.repeat(141)}}, {version: 1, values: {}, photo: {dataUrl: 'https://example.com/photo.jpg'}}, {version: 1, values: {}, photo: {zoom: 'NaN'}}]) {
  assert.throws(() => validate(invalid), 'invalid imports must be rejected before applying');
}

const photo = healthy.window.factoryPhoto;
photo.setState({dataUrl: 'data:image/png;base64,AAAA', focusX: 0, focusY: 1, zoom: 2});
assert.equal(photo.getState().focusX, 0, 'left edge must survive saving');
const copy = photo.getState(); copy.focusX = 1;
assert.equal(photo.getState().focusX, 0, 'snapshots cannot mutate crop state');
photo.moveBy(-10000, 10000, 100, 100);
assert.equal(photo.getState().focusX, 1);
assert.equal(photo.getState().focusY, 0);
photo.clear();
assert.equal(photo.getState().dataUrl, '');
assert.equal(photo.getState().zoom, 1);

const qrcode = require(path.join(factory, 'vendor/qrcode.min.js'));
const qrSandbox = {window: {qrcode}, URL};
vm.createContext(qrSandbox);
vm.runInContext(fs.readFileSync(path.join(factory, 'qr.js'), 'utf8'), qrSandbox);
assert.throws(() => qrSandbox.window.factoryQR.matrix('javascript:alert(1)'));
assert.throws(() => qrSandbox.window.factoryQR.matrix('not a URL'));
const code = qrSandbox.window.factoryQR.matrix('https://example.com/hello world');
assert.equal(code.value, 'https://example.com/hello%20world');
assert.equal(code.count % 4, 1);
assert(code.code.isDark(0, 0), 'top-left finder pattern must exist');
console.log('PASS factory state: autosave/reload, storage failures, damaged-data preservation, import validation, crop endpoints, QR URL validation');
