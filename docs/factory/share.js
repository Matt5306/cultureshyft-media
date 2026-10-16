(() => {
  'use strict';
  const limits = {layout: 20, headline: 140, subheadline: 180, date: 100, place: 140, body: 450, cta: 100, contact: 160, qrUrl: 140, clientName: 100, clientEmail: 160, extraSizes: 2, extraEdits: 2};
  const flags = ['accent', 'printReady', 'rush'];
  const MAX_TOKEN = 6000;
  function validate(payload) {
    if (!payload || payload.version !== 1 || !payload.values || Array.isArray(payload.values)) throw new Error('This link is not a Flyer Factory brief.');
    for (const [key, value] of Object.entries(payload.values)) {
      if (flags.includes(key)) {
        if (typeof value !== 'boolean') throw new Error('A color or add-on setting is damaged.');
      } else if (!Object.hasOwn(limits, key) || typeof value !== 'string' || value.length > limits[key]) throw new Error('A brief field is damaged or too long.');
    }
    if (!['poster', 'event', 'announcement'].includes(payload.values.layout)) throw new Error('Choose a supported layout.');
    for (const key of ['extraSizes', 'extraEdits']) if (payload.values[key] && !/^(?:[0-9]|10)$/.test(payload.values[key])) throw new Error('Choose between 0 and 10 extras.');
    if (payload.photo?.dataUrl) throw new Error('Photos travel separately. Attach the photo to your email.');
    if (payload.photo) for (const [key, low, high] of [['focusX', 0, 1], ['focusY', 0, 1], ['zoom', 1, 2.5]]) {
      if (typeof payload.photo[key] !== 'number' || payload.photo[key] < low || payload.photo[key] > high || !Number.isFinite(payload.photo[key])) throw new Error('The photo settings are damaged.');
    }
    return payload;
  }
  function encode(payload) {
    validate(payload);
    const bytes = new TextEncoder().encode(JSON.stringify(payload));
    const token = btoa(Array.from(bytes, b => String.fromCharCode(b)).join('')).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    if (token.length > MAX_TOKEN) throw new Error('This brief is too long for a reliable email link.');
    return token;
  }
  function decode(token) {
    if (typeof token !== 'string' || token.length > MAX_TOKEN || !/^[A-Za-z0-9_-]+$/.test(token)) throw new Error('The brief link is incomplete or too long.');
    try {
      const bytes = Uint8Array.from(atob(token.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
      return validate(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)));
    } catch (error) { throw new Error(`The brief link could not open. ${error.message}`); }
  }
  function readable(payload) {
    const v = payload.values;
    const labels = {clientName: 'Your name / business', clientEmail: 'Reply email', layout: 'Layout', headline: 'Headline', subheadline: 'Supporting line', date: 'Date and time', place: 'Place', body: 'Details', cta: 'What should people do?', contact: 'Public contact', qrUrl: 'QR link'};
    return ['FLYER REQUEST — CultureShyft Media', 'Flyer $20, includes the Instagram square', ...Object.entries(labels).map(([key, label]) => `${label}: ${v[key] || 'Not supplied'}`), `Orange accent: ${v.accent ? 'Yes' : 'No'}`, `Extra sizes ($5 each): ${v.extraSizes || 0}`, `Extra edit rounds ($5 each): ${v.extraEdits || 0}`, `Print preparation (+$10): ${v.printReady ? 'Requested' : 'No'}`, `Rush (+$15, subject to availability): ${v.rush ? 'Requested' : 'No'}`, '50% deposit to begin. Balance due on delivery.', 'Please confirm the price and delivery date. Photos are attached separately.'].join('\n');
  }
  window.factoryShare = Object.freeze({encode, decode, validate, readable, MAX_TOKEN});
})();
