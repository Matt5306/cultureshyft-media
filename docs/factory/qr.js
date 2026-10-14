(() => {
  'use strict';
  let lastError = '';

  function message(error) {
    return error instanceof Error ? error.message : String(error);
  }

  function matrix(value) {
    const url = new URL(String(value));
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Use a full http or https link.');
    if (url.href.length > 140) throw new Error('Shorten the QR link to 140 characters or fewer.');
    if (typeof window.qrcode !== 'function') {
      lastError = 'The QR maker did not load.';
      throw new Error(lastError);
    }
    const code = window.qrcode(0, 'M');
    code.addData(url.href);
    code.make();
    lastError = '';
    return {code, count: code.getModuleCount(), value: url.href};
  }

  function renderElement(element, value) {
    element.replaceChildren();
    if (!String(value || '').trim()) { element.hidden = true; return false; }
    const {code, count} = matrix(value);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `-4 -4 ${count + 8} ${count + 8}`);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Scan this QR code');
    const background = document.createElementNS(svg.namespaceURI, 'rect');
    background.setAttribute('x', '-4'); background.setAttribute('y', '-4');
    background.setAttribute('width', count + 8); background.setAttribute('height', count + 8);
    background.setAttribute('fill', '#fff'); svg.append(background);
    let path = '';
    for (let row = 0; row < count; row++) for (let column = 0; column < count; column++) if (code.isDark(row, column)) path += `M${column} ${row}h1v1h-1z`;
    const modules = document.createElementNS(svg.namespaceURI, 'path');
    modules.setAttribute('d', path); modules.setAttribute('fill', '#14151A'); svg.append(modules);
    element.append(svg); element.hidden = false;
    return true;
  }

  function draw(context, value, x, y, size) {
    let prepared;
    try {
      prepared = matrix(value);
    } catch (error) {
      lastError = message(error);
      // A missing optional vendor must not abort the other social exports. The
      // diagnostics retain the exact problem so the checker and UI can surface it.
      if (typeof window.qrcode !== 'function') return null;
      throw error;
    }
    const {code, count} = prepared;
    const quiet = 4;
    const cell = Math.floor(size / (count + quiet * 2));
    if (cell < 2) throw new Error('This QR link is too long to scan reliably. Use a shorter link.');
    const actual = cell * (count + quiet * 2);
    const offsetX = Math.round(x + (size - actual) / 2);
    const offsetY = Math.round(y + (size - actual) / 2);
    context.save();
    context.fillStyle = '#fff'; context.fillRect(x, y, size, size);
    context.fillStyle = '#14151A';
    for (let row = 0; row < count; row++) for (let column = 0; column < count; column++) {
      if (code.isDark(row, column)) context.fillRect(offsetX + (column + quiet) * cell, offsetY + (row + quiet) * cell, cell, cell);
    }
    context.restore();
    return {x, y, width: size, height: size, modules: count};
  }
  window.factoryQR = Object.freeze({matrix, renderElement, draw, getLastError: () => lastError});
})();
