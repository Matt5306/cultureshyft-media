'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {calculate, CATALOG} = require('../docs/factory/invoice.js');
const root = path.resolve(__dirname, '..');
const nodes = new Map();
const sandbox = {
  window: {factoryPageReady: {then() {}}},
  document: {getElementById(id) { if (!nodes.has(id)) nodes.set(id, {addEventListener() {}}); return nodes.get(id); }},
  TextEncoder, TextDecoder, btoa, atob, URL, console
};
vm.createContext(sandbox);
for (const file of ['docs/factory/share.js', 'docs/order/order.js']) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), sandbox);
const share = sandbox.window.factoryShare;
const order = sandbox.window.factoryOrder;
const presets = JSON.parse(fs.readFileSync(path.join(root, 'docs/factory/presets.json'), 'utf8'));
assert.equal(Object.keys(presets).length, 8);
for (const [id, preset] of Object.entries(presets)) {
  const payload = {version:1, values:{...preset.values, clientName:'Renée & Youth 🎉', clientEmail:'renee@example.com', extraSizes:'0', extraEdits:'0', printReady:false, rush:false}, photo:{dataUrl:'', focusX:.5, focusY:.5, zoom:1}};
  const token = share.encode(payload);
  assert.match(token, /^[A-Za-z0-9_-]+$/);
  assert.deepEqual(JSON.parse(JSON.stringify(share.decode(token))), payload, id + ' exact Unicode round-trip');
  const prepared = order.prepare(payload);
  assert.equal(prepared.reason, '', id);
  const link = new URL(prepared.link);
  assert.equal(link.search, '', id + ' customer brief stays out of the URL query');
  assert.ok(link.hash.startsWith('#brief='), id + ' customer brief uses the browser-only fragment');
  assert.equal(link.hash.slice('#brief='.length), token, id + ' exact fragment token');
  const mail = new URL(prepared.mailto);
  assert.equal(mail.pathname, 'mark@cultureshyftmedia.com');
  assert.ok(mail.searchParams.get('body').includes(prepared.link));
  assert.ok(mail.searchParams.get('body').includes('Renée & Youth 🎉'));
}
for (const bad of ['', '!', 'a'.repeat(6001), btoa('{"version":2,"values":{}}')]) assert.throws(() => share.decode(bad));
const base = {version:1, values:{...presets.hiring.values}, photo:{dataUrl:'',focusX:.5,focusY:.5,zoom:1}};
for (const values of [{...base.values,rush:'false'}, {...base.values,extraSizes:'99'}, {...base.values,toString:'invalid'}, {...base.values,headline:'x'.repeat(141)}]) assert.throws(() => share.encode({...base,values}));
assert.throws(() => share.encode({...base,photo:{...base.photo,dataUrl:'data:image/png;base64,AA'}}));
const long = {...base,values:{...base.values}};
for (const [key, limit] of Object.entries({headline:140,subheadline:180,date:100,place:140,body:450,cta:100,contact:160,clientName:100,clientEmail:160})) long.values[key] = '界'.repeat(limit);
const fallback = order.prepare(long);
assert.ok(fallback.reason);
assert.equal(fallback.mailto, '');
assert.ok(fallback.text.includes(long.values.body), 'fallback retains complete request');
assert.deepEqual(calculate([{unitPrice:20,quantity:1},{unitPrice:5,quantity:3},{unitPrice:10,quantity:1},{unitPrice:15,quantity:1}]), {subtotal:60,total:60,deposit:30,balance:30});
assert.deepEqual(calculate([{unitPrice:.05,quantity:1}]), {subtotal:.05,total:.05,deposit:.03,balance:.02});
assert.deepEqual(Object.fromEntries(Object.entries(CATALOG).map(([id,item])=>[id,item.unitPrice])), {flyer:20,extraSize:5,extraEdit:5,printReady:10,rush:15});
console.log('PASS order/invoice units: 8 presets, exact Unicode round-trips, mailto contents, length fallback, malformed links, add-on validation, invoice rates and cent math');
