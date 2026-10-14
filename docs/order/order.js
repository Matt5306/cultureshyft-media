(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const MAX_MAILTO = 8000;
  function prepare(payload) {
    const text = window.factoryShare.readable(payload);
    let link = '', reason = '';
    try {
      const token = window.factoryShare.encode(payload);
      // A local acceptance run still creates a shareable production link.
      link = `https://cultureshyftmedia.com/factory/?brief=${token}`;
    } catch (error) { reason = error.message; }
    const body = text + (link ? `\n\nOpen this brief in Flyer Factory:\n${link}` : '');
    const mailto = `mailto:mark@cultureshyftmedia.com?subject=${encodeURIComponent('Flyer request — ' + payload.values.headline)}&body=${encodeURIComponent(body)}`;
    if (mailto.length > MAX_MAILTO) reason = 'This request is too long for a reliable email link.';
    return {text: body, link, mailto: reason ? '' : mailto, reason};
  }
  function update() {
    const payload = window.factoryBrief.collect(), v = payload.values;
    const result = prepare(payload);
    $('order-copy').value = result.text;
    $('send-mark').href = result.mailto || 'mailto:mark@cultureshyftmedia.com';
    const total = 20 + 5 * Number(v.extraSizes || 0) + 5 * Number(v.extraEdits || 0) + (v.printReady ? 10 : 0) + (v.rush ? 15 : 0);
    $('order-total').textContent = `Requested total: $${total.toFixed(2)} · 50% deposit: $${(total / 2).toFixed(2)} · balance: $${(total / 2).toFixed(2)}. Flyer $20, includes the Instagram square.`;
    $('order-status').textContent = result.reason ? `${result.reason} Your request is still below. Copy this text and email it to Mark.` : 'Next: check your draft, then Send to Mark. Review and press Send in your email app.';
    return result;
  }
  $('brief').addEventListener('input', update);
  $('brief').addEventListener('change', update);
  $('brief').addEventListener('factory:briefapplied', update);
  $('send-mark').addEventListener('click', event => {
    if (!$('brief').reportValidity()) { event.preventDefault(); return; }
    const result = update();
    if (!result.mailto) { event.preventDefault(); $('order-copy').focus(); $('order-copy').select(); }
    else $('order-status').textContent = 'Your email app should open. This page has not sent anything. Review the email and press Send; if it does not open, copy the text below.';
  });
  $('copy-order').addEventListener('click', async () => {
    update();
    try {
      await navigator.clipboard.writeText($('order-copy').value);
      $('order-status').textContent = 'Request copied. Paste it into an email to mark@cultureshyftmedia.com and attach any photos.';
    } catch (_) {
      $('order-copy').focus(); $('order-copy').select();
      $('order-status').textContent = 'Automatic copy is unavailable. Your request is selected below. Use Copy, then paste it into your email.';
    }
  });
  window.factoryOrder = Object.freeze({prepare, update, MAX_MAILTO});
  window.factoryPageReady.then(update);
})();
