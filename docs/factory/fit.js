((root, make) => {
  const api = make();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.factoryTextFit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  function boundedFontSize(minSize, maxSize, fitsAt, passes = 12) {
    if (!Number.isFinite(minSize) || !Number.isFinite(maxSize) || minSize <= 0 || maxSize < minSize) {
      throw new RangeError('Font-size bounds must be positive and ordered.');
    }
    if (typeof fitsAt !== 'function') throw new TypeError('A fit measurement function is required.');
    if (fitsAt(maxSize)) return maxSize;
    let low = minSize;
    let high = maxSize;
    for (let pass = 0; pass < passes; pass++) {
      const size = (low + high) / 2;
      if (fitsAt(size)) low = size; else high = size;
    }
    return low;
  }

  return Object.freeze({boundedFontSize});
});
