(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const form = $('brief');
  const flyer = $('flyer');
  const fields = ['headline', 'subheadline', 'date', 'place', 'body', 'cta', 'contact'];
  const layouts = ['poster', 'event', 'announcement'];
  const presets = {
    poster: {headline: 'Make your\nnext move.', subheadline: 'Good people. Fresh ideas. One room.', date: 'Saturday, October 24\n2–6 PM', place: 'The Community Room\n1200 Woodward Ave, Detroit', body: 'Meet local makers and business owners.\nShare what you do. Find your next collaborator.\nEveryone is welcome.', cta: 'Come through. Bring a friend.', contact: 'hello@example.com · 313-555-0142'},
    event: {headline: 'A day for\nthe neighborhood.', subheadline: 'Local sounds. Good food. Real connection.', date: 'OCT 24\nSATURDAY\n2–6 PM', place: 'The Community Room\n1200 Woodward Ave\nDetroit, MI', body: 'Music, food and local makers.\nBring the whole family.\nFree entry. All are welcome.', cta: 'Save the date. See you there.', contact: 'neighborhood@example.com · 313-555-0142'},
    announcement: {headline: 'Something\ngood starts\nhere.', subheadline: 'Your next chapter deserves to be seen.', date: 'Opening Monday\nNovember 2 · 9 AM', place: '24 Grand River Ave\nDetroit, MI', body: 'A new space for ideas, people and possibility.\nStop by, say hello and see what is next.\nMade for this community.', cta: 'Be part of the beginning.', contact: 'hello@example.com · 313-555-0142'}
  };
  let ready = false;
  let uploadVersion = 0;
  let fontFailed = false;
  let shortened = [];
  let qrInvalid = '';
  let renderQueued = false;
  const runtimeErrors = window.factoryRuntimeErrors = window.factoryRuntimeErrors || [];
  const bootstrapRecordRuntimeError = window.factoryRecordRuntimeError;
  function recordRuntimeError(error) {
    if (bootstrapRecordRuntimeError) bootstrapRecordRuntimeError(error);
    else {
      const detail = error instanceof Error ? (error.stack || error.message) : String(error || 'Unknown JavaScript error');
      if (!runtimeErrors.includes(detail)) runtimeErrors.push(detail);
    }
    publishReport();
  }
  window.factoryRecordRuntimeError = recordRuntimeError;
  if (!window.factoryRuntimeErrorListeners) {
    window.addEventListener('error', event => {
      const source = event.filename || event.target?.src || event.target?.href || '';
      recordRuntimeError(`${event.message || 'Resource load failed'}${source ? ` (${source})` : ''}`);
    }, true);
    window.addEventListener('unhandledrejection', event => {
      recordRuntimeError(`Unhandled rejection: ${event.reason instanceof Error ? (event.reason.stack || event.reason.message) : String(event.reason)}`);
    });
    window.factoryRuntimeErrorListeners = true;
  }
  const params = new URLSearchParams(location.search);
  const demo = params.get('demo');
  if (Object.hasOwn(presets, demo)) {
    $('layout').value = demo;
    fields.forEach(key => { $(key).value = key === 'body' ? presets[demo][key] : presets[demo][key].replace(/\n/g, ' '); });
  }
  if (params.get('qr') === '1') $('qr-url').value = 'https://cultureshyftmedia.com/';

  function collectBrief() {
    const values = {};
    [...form.elements].forEach(control => {
      if (!control.name || control.type === 'file') return;
      values[control.name] = control.type === 'checkbox' ? control.checked : control.value;
    });
    return {version: 1, values, photo: window.factoryPhoto.getState()};
  }

  function applyBrief(payload) {
    if (!payload || payload.version !== 1 || !payload.values || typeof payload.values !== 'object') throw new Error('This is not a Flyer Factory brief.');
    uploadVersion++;
    [...form.elements].forEach(control => {
      if (!control.name) return;
      const supplied = Object.hasOwn(payload.values, control.name);
      if (control.type === 'checkbox') control.checked = supplied ? Boolean(payload.values[control.name]) : control.name === 'accent';
      else if (control.type !== 'file') {
        const value = supplied ? String(payload.values[control.name] ?? '') : control.name === 'layout' ? 'poster' : '';
        control.value = Number(control.maxLength) > 0 ? value.slice(0, control.maxLength) : value;
      }
    });
    if (!layouts.includes($('layout').value)) $('layout').value = 'poster';
    window.factoryPhoto.setState(payload.photo || {});
    render();
    form.dispatchEvent(new CustomEvent('factory:briefapplied', {bubbles: true}));
  }

  function fits(element) {
    return element.scrollHeight <= element.clientHeight + 1 && element.scrollWidth <= element.clientWidth + 1;
  }

  // Fit the actual rendered type, including long unbroken words. Preserve input
  // in the form; when even the minimum type cannot fit, show an explicit warning.
  function fitText(element, text, minSize) {
    element.style.removeProperty('font-size');
    element.textContent = text;
    const high = parseFloat(getComputedStyle(element).fontSize);
    if (!fits(element)) {
      const size = window.factoryTextFit.boundedFontSize(minSize, high, candidate => {
        element.style.fontSize = `${candidate}px`;
        return fits(element);
      }, 10);
      element.style.fontSize = `${size}px`;
    }
    if (!fits(element)) shorten(element, text);
  }

  function shorten(element, text) {
    const chars = Array.from(text);
    let low = 0;
    let high = chars.length;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      element.textContent = `${chars.slice(0, mid).join('').trimEnd()}…`;
      if (fits(element)) low = mid; else high = mid - 1;
    }
    element.textContent = `${chars.slice(0, low).join('').trimEnd()}…`;
    shortened.push(element.dataset.fit);
  }

  function scalePreview() {
    const well = $('preview-well');
    const style = getComputedStyle(well);
    const available = well.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const scale = Math.min(1, Math.max(0.1, available / 816));
    $('preview-scale').style.width = `${816 * scale}px`;
    $('preview-scale').style.height = `${1056 * scale}px`;
    flyer.style.transform = `scale(${scale})`;
  }

  function updateNextStep() {
    const missing = fields.filter(key => ['headline', 'contact'].includes(key) && !$(key).value.trim());
    if (fontFailed) {
      $('next-step').textContent = 'The brand font could not load. Your brief is still here. Reload this page to try again before saving.';
    } else if (qrInvalid) {
      $('next-step').textContent = `Fix the QR code link: ${qrInvalid}`;
    } else if (missing.length) {
      $('next-step').textContent = `Next: add your ${missing.join(' and ')}${missing.includes('contact') ? ' line' : ''}.`;
    } else if (shortened.length) {
      const names = {body: 'body', cta: 'call to action', headline: 'headline', subheadline: 'subheadline', date: 'date & time', place: 'place', contact: 'contact line'};
      $('next-step').textContent = `Shorten your ${shortened.map(key => names[key]).join(', ')}: the preview ends with “…”. Your full text is still in the form.`;
    } else {
      $('next-step').textContent = 'Next: check the details in your preview, then save your PDF or download a social image.';
    }
  }

  function render() {
    renderQueued = false;
    const layout = layouts.includes($('layout').value) ? $('layout').value : 'poster';
    flyer.dataset.layout = layout;
    positionPhoto();
    flyer.classList.toggle('no-accent', !$('accent').checked);
    const logoPath = `../logo/web/cultureshyft-horizontal-${$('accent').checked ? 'color-onlight' : 'mono-black'}.png`;
    if ($('flyer-logo').getAttribute('src') !== logoPath) $('flyer-logo').src = logoPath;
    const qrValue = $('qr-url').value.trim();
    qrInvalid = '';
    try {
      window.factoryQR.renderElement($('flyer-qr'), qrValue);
      $('qr-url').setCustomValidity('');
      $('qr-help').textContent = 'Add a full web link to place a scannable code on the flyer and story.';
    } catch (error) {
      $('flyer-qr').hidden = true;
      qrInvalid = error instanceof Error ? error.message : 'Use a full http or https link.';
      $('qr-url').setCustomValidity(qrInvalid);
      $('qr-help').textContent = qrInvalid;
    }
    shortened = [];
    const minimums = {headline: 26, subheadline: 16, date: 18, place: 16, cta: 18, contact: 12};
    fields.forEach(key => {
      const element = $(`flyer-${key}`);
      const raw = $(key).value.trim();
      const text = raw || (key === 'headline' ? 'Your next\nbig thing.' : key === 'contact' ? 'Your contact line goes here' : '');
      // Single-line inputs normalize pasted line breaks; sample line breaks are
      // merely formatting suggestions, never a separate source of content.
      if (key === 'body') {
        element.textContent = text;
        if (!fits(element)) shorten(element, text);
      } else fitText(element, text, minimums[key]);
    });
    document.querySelector('.date-panel .flyer-label').hidden = !$('date').value.trim();
    document.querySelector('.place-panel .flyer-label').hidden = !$('place').value.trim();
    updateNextStep();
    scalePreview();
    publishReport();
  }

  function queueRender() {
    if (!renderQueued) {
      renderQueued = true;
      requestAnimationFrame(render);
    }
  }

  function visible(element) {
    return element.getClientRects().length > 0 && getComputedStyle(element).visibility !== 'hidden';
  }

  window.factoryReport = () => {
    const overflow = [];
    const missing = [];
    // Measure text scroll extents, then every content container's geometry.
    // Decorative photo-art is deliberately cropped, just like an uploaded photo.
    const scale = flyer.getBoundingClientRect().width / 816;
    const tolerance = Math.max(0.8, scale);
    const within = (a, b) => a.left >= b.left - tolerance && a.top >= b.top - tolerance && a.right <= b.right + tolerance && a.bottom <= b.bottom + tolerance;
    flyer.querySelectorAll('*').forEach(element => {
      if (!visible(element) || element.closest('.photo-art')) return;
      const name = element.id || element.className || element.tagName.toLowerCase();
      if (element.matches('[data-fit]') && !fits(element)) overflow.push(`${name}: text exceeds box`);
      if (element.id !== 'flyer-photo' && !within(element.getBoundingClientRect(), element.parentElement.getBoundingClientRect())) overflow.push(`${name}: outside parent`);
    });
    // Positioned panels must also remain separate; clipping is not proof of fit.
    const panels = [...flyer.children].filter(visible);
    for (let a = 0; a < panels.length; a++) {
      for (let b = a + 1; b < panels.length; b++) {
        const x = panels[a].getBoundingClientRect();
        const y = panels[b].getBoundingClientRect();
        if (Math.min(x.right, y.right) - Math.max(x.left, y.left) > tolerance && Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top) > tolerance) overflow.push(`${panels[a].className}: overlaps ${panels[b].className}`);
      }
    }
    const logo = $('flyer-logo');
    const logoPresent = logo.complete && logo.naturalWidth > 0 && visible(logo);
    const contactPresent = Boolean($('contact').value.trim()) && Boolean($('flyer-contact').textContent.trim()) && visible($('flyer-contact'));
    if (!logoPresent) missing.push('logo');
    const photoState = window.factoryPhoto.getState();
    if (photoState.dataUrl && flyer.dataset.layout !== 'announcement' && (!$('flyer-photo').complete || !$('flyer-photo').naturalWidth)) missing.push('photo');
    const qrExpected = Boolean($('qr-url').value.trim());
    const qrPresent = qrExpected && !$('flyer-qr').hidden && Boolean($('flyer-qr').querySelector('svg'));
    if (qrExpected && !qrPresent) missing.push('QR code');
    if (!contactPresent) missing.push('contact');
    if (!$('headline').value.trim()) missing.push('headline');
    if (fontFailed || !document.fonts.check('800 32px Manrope')) missing.push('Manrope font');
    if (!ready) missing.push('preview not ready');
    if (runtimeErrors.length) missing.push(...runtimeErrors);
    const documentScrollWidth = document.documentElement.scrollWidth;
    const documentClientWidth = document.documentElement.clientWidth;
    if (!matchMedia('print').matches && documentScrollWidth > documentClientWidth + 1) overflow.push('page: horizontal scroll');
    return {overflow, missing, ready, diagnostics: {documentScrollWidth, documentClientWidth, viewportWidth: innerWidth, layout: flyer.dataset.layout, preset: $('preset').value, logoPresent, contactPresent, qrExpected, qrPresent, qrError: window.factoryQR?.getLastError?.() || qrInvalid || '', runtimeErrors: [...runtimeErrors], shortened: [...shortened], flyerWidth: flyer.offsetWidth, flyerHeight: flyer.offsetHeight}};
  };

  function publishReport() {
    if (params.get('check') !== '1') return;
    let output = $('factory-check-report');
    if (!output) {
      output = document.createElement('script');
      output.id = 'factory-check-report';
      output.type = 'application/json';
      document.body.append(output);
    }
    output.textContent = JSON.stringify(window.factoryReport());
  }

  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', queueRender);
  $('layout').addEventListener('change', render);
  $('accent').addEventListener('change', render);
  $('flyer-logo').addEventListener('load', publishReport);
  $('flyer-logo').addEventListener('error', () => {
    $('next-step').textContent = 'The logo could not load. Your brief is still here. Reload this page to try again before saving.';
    publishReport();
  });
  window.addEventListener('resize', () => { scalePreview(); publishReport(); });
  new ResizeObserver(scalePreview).observe($('preview-well'));
  window.addEventListener('beforeprint', render);
  window.addEventListener('afterprint', scalePreview);
  $('print-button').addEventListener('click', async () => {
    await window.factoryReady;
    render();
    if (!form.reportValidity()) return;
    // The monochrome logo may have just switched; wait for it before printing.
    try {
      await $('flyer-logo').decode();
      if (window.factoryPhoto.getState().dataUrl) await $('flyer-photo').decode();
    } catch (_) { /* Report below gives recovery guidance. */ }
    const report = window.factoryReport();
    if (report.overflow.length || report.missing.length) {
      $('next-step').textContent = 'The flyer is not ready to print. Your brief is still here. Check the required fields; if the logo or font is missing, reload this page.';
      return;
    }
    window.print();
  });

  function updatePhotoVisual() {
    const state = window.factoryPhoto.getState();
    const image = $('flyer-photo');
    if (state.dataUrl) {
      if (image.src !== state.dataUrl) image.src = state.dataUrl;
      image.hidden = false;
      $('photo-area').classList.add('has-photo');
      $('photo-area').classList.toggle('can-drag', flyer.dataset.layout !== 'announcement');
      $('remove-photo').disabled = false;
      $('photo-controls').hidden = false;
      $('photo-zoom').value = String(Math.round(state.zoom * 100));
      $('photo-zoom-value').value = `${Math.round(state.zoom * 100)}%`;
    } else {
      image.hidden = true;
      image.removeAttribute('src');
      image.style.removeProperty('transform');
      $('photo-area').classList.remove('has-photo', 'can-drag');
      $('remove-photo').disabled = true;
      $('photo-controls').hidden = true;
    }
    queueRender();
  }

  function positionPhoto() {
    const state = window.factoryPhoto.getState();
    const image = $('flyer-photo');
    const area = $('photo-area');
    if (!state.dataUrl || !image.naturalWidth || !image.naturalHeight || flyer.dataset.layout === 'announcement') return;
    const width = area.clientWidth; const height = area.clientHeight;
    const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight) * state.zoom;
    const renderedWidth = image.naturalWidth * scale; const renderedHeight = image.naturalHeight * scale;
    image.style.width = `${renderedWidth}px`; image.style.height = `${renderedHeight}px`;
    image.style.left = `${-(renderedWidth - width) * state.focusX}px`;
    image.style.top = `${-(renderedHeight - height) * state.focusY}px`;
  }
  $('flyer-photo').addEventListener('load', () => { positionPhoto(); publishReport(); });

  $('photo').addEventListener('change', async () => {
    const file = $('photo').files[0];
    if (!file) return;
    const version = ++uploadVersion;
    const fail = message => {
      if (version !== uploadVersion) return;
      $('photo-status').textContent = `${message} Your brief and previous photo are unchanged. Choose a JPG, PNG or WebP up to 12 MB.`;
      $('photo').value = '';
    };
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 12 * 1024 * 1024) {
      fail('That photo has an unsupported format or is too large.');
      return;
    }
    try {
      const prepared = await window.factoryPhoto.fromFile(file);
      if (version !== uploadVersion) return;
      window.factoryPhoto.setState(prepared);
      $('photo-status').textContent = 'Photo ready. Drag it in the preview or use zoom; the crop is saved with your brief.';
    } catch (error) {
      fail(error instanceof Error ? error.message : 'This photo could not open.');
    }
  });
  $('remove-photo').addEventListener('click', () => {
    uploadVersion++;
    window.factoryPhoto.clear();
    $('photo').value = '';
    $('photo-status').textContent = 'Photo removed. You can choose another; your brief is unchanged.';
  });

  $('photo-zoom').addEventListener('input', () => {
    const state = window.factoryPhoto.getState();
    window.factoryPhoto.setState({...state, zoom: Number($('photo-zoom').value) / 100});
  });
  let drag = null;
  $('photo-area').addEventListener('pointerdown', event => {
    if (!window.factoryPhoto.getState().dataUrl || flyer.dataset.layout === 'announcement') return;
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY};
    $('photo-area').setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  $('photo-area').addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const rect = $('photo-area').getBoundingClientRect();
    const state = window.factoryPhoto.getState();
    const imageRect = $('flyer-photo').getBoundingClientRect();
    const overflowX = Math.max(1, imageRect.width - rect.width);
    const overflowY = Math.max(1, imageRect.height - rect.height);
    window.factoryPhoto.setState({...state, focusX: state.focusX - (event.clientX - drag.x) / overflowX, focusY: state.focusY - (event.clientY - drag.y) / overflowY});
    drag.x = event.clientX; drag.y = event.clientY;
  });
  const endDrag = event => { if (drag?.id === event.pointerId) drag = null; };
  $('photo-area').addEventListener('pointerup', endDrag);
  $('photo-area').addEventListener('pointercancel', endDrag);
  window.addEventListener('factory:photochange', updatePhotoVisual);

  $('mobile-print').addEventListener('click', () => $('print-button').click());
  $('mobile-download').addEventListener('click', () => {
    document.querySelector('.export-panel')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    $('social-status').textContent = 'Choose square, story, or Facebook below.';
  });
  window.factoryBrief = Object.freeze({collect: collectBrief, apply: applyBrief});

  const presetReady = (async () => {
    try {
      const response = await fetch('../factory/presets.json');
      if (!response.ok) throw new Error('Samples could not load.');
      const choices = await response.json();
      window.factoryPresets = choices;
      for (const [id, preset] of Object.entries(choices)) {
        const option = document.createElement('option'); option.value = id; option.textContent = preset.label; $('preset').append(option);
      }
      function usePreset(id) {
        const preset = choices[id]; if (!preset) return;
        // Keep customer information and the photo when changing the copy.
        const current = collectBrief();
        applyBrief({...current, values: {...current.values, ...preset.values}});
        $('preset-status').textContent = 'Sample loaded. Replace the example date, place, contact and offer before sharing.';
      }
      $('preset').addEventListener('change', () => usePreset($('preset').value));
      if (!params.has('brief') && Object.hasOwn(choices, demo)) { $('preset').value = demo; usePreset(demo); }
    } catch (_) {
      $('preset-status').textContent = 'Samples could not load. Your brief is safe. Fill in the details below, or reload to try again.';
    }
    if (params.has('brief')) {
      try {
        applyBrief(window.factoryShare.decode(params.get('brief')));
        $('preset-status').textContent = 'Customer brief loaded. Check the details, then save to My flyers.';
      } catch (error) { $('preset-status').textContent = `${error.message} Saved flyers are unchanged. Ask for the copied brief text.`; }
    }
  })();
  updatePhotoVisual();
  render();
  window.factoryPageReady = (async () => {
    await presetReady;
    try {
      const fonts = await document.fonts.load('800 32px Manrope');
      await document.fonts.ready;
      fontFailed = !fonts.length;
    } catch (_) { fontFailed = true; }
    try { await $('flyer-logo').decode(); } catch (_) { /* Report missing logo. */ }
    ready = true;
    // Fonts settle after the first paint: refit the text with the real font and republish the check report.
    render();
    render();
    return window.factoryReport();
  })();
  // social.js extends this promise with deterministic check-mode exports.
  window.factoryReady = window.factoryPageReady;
})();
