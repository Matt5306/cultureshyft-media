'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
globalThis.factoryTextFit = require(path.join(root, 'docs', 'factory', 'fit.js'));
const {wrapLines, fitCanvasText, drawCover, canvasBlob} = require(path.join(root, 'docs', 'factory', 'social.js'));

function context() {
  return {
    font: '700 20px Manrope',
    calls: [],
    measureText(text) {
      const match = this.font.match(/([\d.]+)px/);
      const size = match ? Number(match[1]) : 20;
      return {width: Array.from(text).length * size * 0.55};
    },
    drawImage(...args) { this.calls.push(args); }
  };
}

async function run() {
  const shared = globalThis.factoryTextFit.boundedFontSize(10, 100, size => size <= 42);
  assert(shared >= 41.9 && shared <= 42, `unexpected bounded size ${shared}`);

  const ctx = context();
  const wrapped = wrapLines(ctx, 'short supercalifragilisticexpialidocious tail', 120);
  assert(wrapped.length >= 3, 'long unbroken words should split across lines');
  assert(wrapped.every(line => ctx.measureText(line).width <= 120.01), 'wrapped lines must stay within width');

  const fit = fitCanvasText(ctx, 'Make the neighborhood move together', {x: 10, y: 20, width: 220, height: 100}, {minSize: 12, maxSize: 52, maxLines: 3, lineHeight: 1.1, weight: 800});
  assert.equal(fit.shortened, false);
  assert(fit.maxLineWidth <= fit.box.width + 0.01);
  assert(fit.lines.length * fit.lineHeight <= fit.box.height + 0.01);

  const exactHeight = fitCanvasText(ctx, 'Line one\nLine two\nLine three', {x: 0, y: 0, width: 500, height: 116}, {minSize: 20, maxSize: 40, maxLines: 3, lineHeight: 1.2});
  assert.equal(exactHeight.lines.length, 3);
  assert.equal(exactHeight.shortened, false, 'three explicit lines should shrink instead of losing line three');
  assert(exactHeight.lines.length * exactHeight.lineHeight <= exactHeight.box.height + 0.01);

  const cramped = fitCanvasText(ctx, 'one two three four five six seven eight nine', {x: 0, y: 0, width: 70, height: 14}, {minSize: 12, maxSize: 20, maxLines: 1, lineHeight: 1.1});
  assert.equal(cramped.shortened, true);
  assert.equal(cramped.lines.length, 1);
  assert(cramped.maxLineWidth <= cramped.box.width + 0.01);

  const cropContext = context();
  const crop = drawCover(cropContext, {naturalWidth: 400, naturalHeight: 200}, {x: 0, y: 0, width: 100, height: 100}, 1, 0.5);
  assert.deepEqual(crop, {sourceX: 200, sourceY: 0, sourceWidth: 200, sourceHeight: 200, focusX: 1, focusY: 0.5});
  assert.equal(cropContext.calls.length, 1);

  const blob = {size: 123};
  assert.equal(await canvasBlob({toBlob(callback) { callback(blob); }}), blob);
  await assert.rejects(canvasBlob({toBlob(callback) { callback(null); }}), /empty PNG/);
  await assert.rejects(canvasBlob({toBlob() { throw new Error('blocked'); }}), /blocked/);

  const factorySource = fs.readFileSync(path.join(root, 'docs', 'factory', 'factory.js'), 'utf8');
  const socialSource = fs.readFileSync(path.join(root, 'docs', 'factory', 'social.js'), 'utf8');
  assert(factorySource.includes('factoryTextFit.boundedFontSize'), 'print preview must use the shared fitter');
  assert(socialSource.includes('factoryTextFit'), 'social export must use the shared fitter');
  console.log('PASS factory social unit checks: shared fitting, bounds, cover crop, and blob failure recovery');
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
