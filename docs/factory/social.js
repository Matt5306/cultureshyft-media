(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const COLORS = {orange: '#FF5A1F', ink: '#14151A', paper: '#FFFFFF', sand: '#F4F3EF', slate: '#6A6E78', ember: '#FFE8DC'};
  const MODES = {
    square: {width: 1080, height: 1080, label: 'Instagram square'},
    story: {width: 1080, height: 1920, label: 'Instagram story'},
    facebook: {width: 1920, height: 1005, label: 'Facebook event cover'}
  };
  const diagnostics = {};

  function brief() {
    const read = id => ($(id)?.value || '').trim();
    return {
      layout: read('layout') || 'poster',
      headline: read('headline') || 'Your next big thing.',
      subheadline: read('subheadline'),
      date: read('date'),
      place: read('place'),
      body: read('body'),
      cta: read('cta'),
      contact: read('contact') || 'Your contact line goes here',
      qrUrl: read('qr-url'),
      accent: $('accent')?.checked !== false
    };
  }

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  function focusValue(axis) {
    const shared = globalThis.factoryPhoto?.getState?.();
    if (shared && Number.isFinite(Number(shared[axis === 'x' ? 'focusX' : 'focusY']))) return clamp(Number(shared[axis === 'x' ? 'focusX' : 'focusY']), 0, 1);
    const candidates = [`crop-${axis}`, `photo-focus-${axis}`, `focus-${axis}`];
    for (const id of candidates) {
      const control = $(id);
      if (!control || control.value === '') continue;
      const raw = Number(control.value);
      if (!Number.isFinite(raw)) continue;
      if (control.type === 'range' || control.hasAttribute('min') || control.hasAttribute('max')) {
        const min = Number.isFinite(Number(control.min)) && control.min !== '' ? Number(control.min) : 0;
        const max = Number.isFinite(Number(control.max)) && control.max !== '' ? Number(control.max) : 100;
        if (max > min) return clamp((raw - min) / (max - min), 0, 1);
      }
      return clamp(raw > 1 ? raw / 100 : raw, 0, 1);
    }
    const image = $('flyer-photo');
    const dataValue = Number(image?.dataset?.[`focus${axis.toUpperCase()}`]);
    if (Number.isFinite(dataValue) && image?.dataset?.[`focus${axis.toUpperCase()}`] !== undefined) {
      return clamp(dataValue > 1 ? dataValue / 100 : dataValue, 0, 1);
    }
    const position = image ? getComputedStyle(image).objectPosition.split(/\s+/) : [];
    const token = position[axis === 'x' ? 0 : 1];
    if (token?.endsWith('%')) return clamp(parseFloat(token) / 100, 0, 1);
    return 0.5;
  }

  function roundedRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  function drawCover(ctx, image, box, focusX, focusY, zoom = 1) {
    zoom = clamp(Number(zoom) || 1, 1, 2.5);
    const scale = Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight) * zoom;
    const sourceWidth = box.width / scale;
    const sourceHeight = box.height / scale;
    const sourceX = (image.naturalWidth - sourceWidth) * focusX;
    const sourceY = (image.naturalHeight - sourceHeight) * focusY;
    ctx.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, box.x, box.y, box.width, box.height);
    return {sourceX, sourceY, sourceWidth, sourceHeight, focusX, focusY};
  }

  function drawPhotoOrArt(ctx, box, image, accent) {
    ctx.save();
    roundedRect(ctx, box.x, box.y, box.width, box.height, box.radius || 0);
    ctx.clip();
    let crop = null;
    if (image) {
      const zoom = clamp(Number(globalThis.factoryPhoto?.getState?.().zoom) || 1, 1, 2.5);
      crop = drawCover(ctx, image, box, focusValue('x'), focusValue('y'), zoom);
      crop.zoom = zoom;
    } else {
      ctx.fillStyle = COLORS.sand;
      ctx.fillRect(box.x, box.y, box.width, box.height);
      const stripeWidth = box.width * 0.12;
      const gap = stripeWidth * 0.56;
      const start = box.x + box.width * 0.28;
      ctx.translate(start, box.y + box.height / 2);
      ctx.rotate(-0.31);
      [COLORS.ink, '#D5D4CD', accent].forEach((color, index) => {
        ctx.fillStyle = color;
        ctx.fillRect(index * (stripeWidth + gap), -box.height, stripeWidth, box.height * 2);
      });
    }
    ctx.restore();
    return crop;
  }

  function splitLongToken(ctx, token, maxWidth) {
    const parts = [];
    let piece = '';
    for (const character of Array.from(token)) {
      if (piece && ctx.measureText(piece + character).width > maxWidth) {
        parts.push(piece);
        piece = character;
      } else piece += character;
    }
    if (piece) parts.push(piece);
    return parts;
  }

  function wrapLines(ctx, text, maxWidth) {
    const lines = [];
    const paragraphs = String(text || '').replace(/\r/g, '').split('\n');
    paragraphs.forEach((paragraph, paragraphIndex) => {
      const words = paragraph.trim().split(/\s+/).filter(Boolean);
      if (!words.length) {
        if (paragraphIndex < paragraphs.length - 1) lines.push('');
        return;
      }
      let line = '';
      words.forEach(word => {
        const pieces = ctx.measureText(word).width > maxWidth ? splitLongToken(ctx, word, maxWidth) : [word];
        pieces.forEach(piece => {
          const candidate = line ? `${line} ${piece}` : piece;
          if (line && ctx.measureText(candidate).width > maxWidth) {
            lines.push(line);
            line = piece;
          } else line = candidate;
        });
      });
      if (line) lines.push(line);
    });
    return lines;
  }

  function setFont(ctx, weight, size) {
    ctx.font = `${weight} ${size}px Manrope, "Segoe UI", sans-serif`;
  }

  function fitCanvasText(ctx, text, box, options = {}) {
    const maxSize = options.maxSize || 72;
    const weight = options.weight || 700;
    const lineHeight = options.lineHeight || 1.1;
    const minSize = Math.min(options.minSize || 18, maxSize, box.height / lineHeight);
    const maxLines = options.maxLines || Number.POSITIVE_INFINITY;
    let lines = [];
    const fitEngine = globalThis.factoryTextFit;
    if (!fitEngine) throw new Error('The shared text fitter is unavailable.');
    const chosen = fitEngine.boundedFontSize(minSize, maxSize, size => {
      setFont(ctx, weight, size);
      const candidate = wrapLines(ctx, text, box.width);
      return candidate.length <= maxLines && candidate.length * size * lineHeight <= box.height;
    });
    setFont(ctx, weight, chosen);
    lines = wrapLines(ctx, text, box.width);
    const allowedLines = Math.max(1, Math.min(maxLines, Math.floor(box.height / (chosen * lineHeight))));
    let shortened = false;
    if (lines.length > allowedLines) {
      lines = lines.slice(0, allowedLines);
      let last = lines[lines.length - 1].replace(/…$/, '');
      while (last && ctx.measureText(`${last}…`).width > box.width) last = Array.from(last).slice(0, -1).join('').trimEnd();
      lines[lines.length - 1] = `${last}…`;
      shortened = true;
    }
    lines = lines.map(line => {
      if (ctx.measureText(line).width <= box.width + 0.01) return line;
      let clipped = Array.from(line);
      while (clipped.length && ctx.measureText(`${clipped.join('').trimEnd()}…`).width > box.width) clipped.pop();
      shortened = true;
      return clipped.length ? `${clipped.join('').trimEnd()}…` : '';
    });
    const maxLineWidth = lines.reduce((maximum, line) => Math.max(maximum, ctx.measureText(line).width), 0);
    return {size: chosen, lines, lineHeight: chosen * lineHeight, maxLineWidth, shortened, box: {...box}};
  }

  function drawFittedText(ctx, text, box, options = {}) {
    if (!text) return {size: 0, lines: [], lineHeight: 0, maxLineWidth: 0, shortened: false, box: {...box}};
    const fit = fitCanvasText(ctx, text, box, options);
    ctx.save();
    setFont(ctx, options.weight || 700, fit.size);
    ctx.fillStyle = options.color || COLORS.ink;
    ctx.textAlign = options.align || 'left';
    ctx.textBaseline = 'top';
    const x = options.align === 'center' ? box.x + box.width / 2 : options.align === 'right' ? box.x + box.width : box.x;
    fit.lines.forEach((line, index) => ctx.fillText(line, x, box.y + index * fit.lineHeight, box.width));
    ctx.restore();
    return fit;
  }

  function drawLabel(ctx, text, x, y, color = COLORS.slate, align = 'left') {
    ctx.save();
    setFont(ctx, 800, 22);
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = 'top';
    ctx.fillText(text.toUpperCase(), x, y);
    ctx.restore();
  }

  async function loadLogo(onDark = false, useAccent = true) {
    const variant = `${useAccent ? 'color' : 'mono'}-${onDark ? 'ondark' : 'onlight'}`.replace('mono-ondark', 'mono-white').replace('mono-onlight', 'mono-black');
    const image = new Image();
    image.src = `../logo/web/cultureshyft-horizontal-${variant}.png`;
    await image.decode();
    return image;
  }

  function drawLogo(ctx, logo, x, y, width) {
    const height = width * logo.naturalHeight / logo.naturalWidth;
    ctx.drawImage(logo, x, y, width, height);
    return {x, y, width, height};
  }

  function decorateEventMedia(ctx, box, data) {
    if (data.layout !== 'event') return;
    ctx.save();
    ctx.fillStyle = data.accent ? COLORS.orange : COLORS.ink;
    ctx.fillRect(box.x, box.y, Math.max(12, box.width * 0.018), box.height);
    ctx.restore();
  }

  function drawSquare(ctx, data, logo, image) {
    const accent = data.accent ? COLORS.orange : COLORS.ink;
    const fits = {};
    ctx.fillStyle = COLORS.paper;
    ctx.fillRect(0, 0, 1080, 1080);
    const mediaBox = {x: 54, y: 54, width: 972, height: 340, radius: 20};
    const crop = drawPhotoOrArt(ctx, mediaBox, data.layout === 'announcement' ? null : image, accent);
    decorateEventMedia(ctx, mediaBox, data);
    ctx.fillStyle = accent;
    ctx.fillRect(54, 424, 92, 12);
    fits.headline = drawFittedText(ctx, data.headline, {x: 54, y: 462, width: 972, height: 244}, {maxSize: 108, minSize: 46, weight: 800, lineHeight: 1.02, maxLines: 3, align: 'center'});
    const dateWidth = data.place ? 448 : 972;
    if (data.date) {
      drawLabel(ctx, 'When', 54, 742);
      fits.date = drawFittedText(ctx, data.date, {x: 54, y: 780, width: dateWidth, height: 88}, {maxSize: 36, minSize: 23, weight: 700, lineHeight: 1.2, maxLines: 2});
    }
    if (data.place) {
      drawLabel(ctx, 'Where', 578, 742);
      fits.place = drawFittedText(ctx, data.place, {x: 578, y: 780, width: 448, height: 88}, {maxSize: 36, minSize: 23, weight: 700, lineHeight: 1.2, maxLines: 2});
    }
    ctx.fillStyle = '#D8D7D2';
    ctx.fillRect(54, 902, 972, 2);
    fits.contact = drawFittedText(ctx, data.contact, {x: 54, y: 948, width: 550, height: 45}, {maxSize: 24, minSize: 17, weight: 700, lineHeight: 1.2, maxLines: 2});
    const logoBox = drawLogo(ctx, logo, 714, 936, 312);
    return {fits, logoBox, crop, photoUsed: Boolean(image && data.layout !== 'announcement'), safeArea: {x: 0, y: 0, width: 1080, height: 1080}};
  }

  function drawStory(ctx, data, logo, image) {
    const accent = data.accent ? COLORS.orange : COLORS.paper;
    const fits = {};
    const safeArea = {x: 60, y: 250, width: 960, height: 1420};
    ctx.fillStyle = COLORS.ink;
    ctx.fillRect(0, 0, 1080, 1920);
    const mediaBox = {x: 60, y: 250, width: 960, height: 500, radius: 28};
    const crop = drawPhotoOrArt(ctx, mediaBox, data.layout === 'announcement' ? null : image, accent);
    decorateEventMedia(ctx, mediaBox, data);
    ctx.fillStyle = accent;
    ctx.fillRect(60, 790, 120, 14);
    fits.headline = drawFittedText(ctx, data.headline, {x: 60, y: 844, width: 960, height: 292}, {maxSize: 116, minSize: 50, weight: 800, lineHeight: 1.02, maxLines: 3, color: COLORS.paper});
    const detailTop = 1172;
    if (data.date) {
      drawLabel(ctx, 'When', 60, detailTop, '#BFC1C8');
      fits.date = drawFittedText(ctx, data.date, {x: 60, y: detailTop + 38, width: 440, height: 84}, {maxSize: 34, minSize: 22, weight: 700, lineHeight: 1.18, maxLines: 2, color: COLORS.paper});
    }
    if (data.place) {
      drawLabel(ctx, 'Where', 580, detailTop, '#BFC1C8');
      fits.place = drawFittedText(ctx, data.place, {x: 580, y: detailTop + 38, width: 440, height: 84}, {maxSize: 34, minSize: 22, weight: 700, lineHeight: 1.18, maxLines: 2, color: COLORS.paper});
    }
    fits.body = drawFittedText(ctx, data.body, {x: 60, y: 1320, width: 960, height: 116}, {maxSize: 30, minSize: 20, weight: 500, lineHeight: 1.35, maxLines: 3, color: '#E2E2E5'});
    if (data.cta) {
      ctx.fillStyle = accent;
      roundedRect(ctx, 60, 1468, 612, 92, 12);
      ctx.fill();
      fits.cta = drawFittedText(ctx, data.cta, {x: 88, y: 1492, width: 556, height: 48}, {maxSize: 31, minSize: 20, weight: 800, lineHeight: 1.1, maxLines: 1, color: COLORS.ink, align: 'center'});
    }
    let qrBox = null;
    if (data.qrUrl) qrBox = window.factoryQR.draw(ctx, data.qrUrl, 864, 1440, 140);
    fits.contact = drawFittedText(ctx, data.contact, {x: 60, y: 1602, width: 540, height: 44}, {maxSize: 22, minSize: 16, weight: 700, lineHeight: 1.2, maxLines: 2, color: COLORS.paper});
    const logoBox = drawLogo(ctx, logo, 710, 1592, 310);
    return {fits, logoBox, qrBox, crop, photoUsed: Boolean(image && data.layout !== 'announcement'), safeArea};
  }

  function drawFacebook(ctx, data, logo, image) {
    const accent = data.accent ? COLORS.orange : COLORS.ink;
    const fits = {};
    ctx.fillStyle = COLORS.paper;
    ctx.fillRect(0, 0, 1920, 1005);
    const mediaBox = {x: 0, y: 0, width: 760, height: 1005};
    const crop = drawPhotoOrArt(ctx, mediaBox, data.layout === 'announcement' ? null : image, accent);
    decorateEventMedia(ctx, mediaBox, data);
    ctx.fillStyle = accent;
    ctx.fillRect(840, 108, 126, 14);
    fits.headline = drawFittedText(ctx, data.headline, {x: 840, y: 166, width: 960, height: 326}, {maxSize: 126, minSize: 54, weight: 800, lineHeight: 1.02, maxLines: 3});
    if (data.subheadline) fits.subheadline = drawFittedText(ctx, data.subheadline, {x: 840, y: 514, width: 960, height: 86}, {maxSize: 38, minSize: 24, weight: 500, lineHeight: 1.25, maxLines: 2, color: COLORS.slate});
    if (data.date) {
      drawLabel(ctx, 'When', 840, 634);
      fits.date = drawFittedText(ctx, data.date, {x: 840, y: 674, width: 430, height: 82}, {maxSize: 36, minSize: 22, weight: 700, lineHeight: 1.2, maxLines: 2});
    }
    if (data.place) {
      drawLabel(ctx, 'Where', 1360, 634);
      fits.place = drawFittedText(ctx, data.place, {x: 1360, y: 674, width: 440, height: 82}, {maxSize: 36, minSize: 22, weight: 700, lineHeight: 1.2, maxLines: 2});
    }
    ctx.fillStyle = '#D8D7D2';
    ctx.fillRect(840, 814, 960, 2);
    fits.contact = drawFittedText(ctx, data.contact, {x: 840, y: 866, width: 520, height: 44}, {maxSize: 24, minSize: 17, weight: 700, lineHeight: 1.2, maxLines: 2});
    const logoBox = drawLogo(ctx, logo, 1480, 846, 320);
    return {fits, logoBox, crop, photoUsed: Boolean(image && data.layout !== 'announcement'), safeArea: {x: 760, y: 0, width: 1160, height: 1005}};
  }

  async function selectedPhoto(layout) {
    if (layout === 'announcement') return null;
    const image = $('flyer-photo');
    if (!image || image.hidden || !image.getAttribute('src')) return null;
    try {
      if (!image.complete || !image.naturalWidth || !image.naturalHeight) await image.decode();
    } catch (_) {
      throw new Error('The selected photo could not finish loading. Your file is unchanged; wait a moment and try the download again.');
    }
    if (!image.naturalWidth || !image.naturalHeight) throw new Error('The selected photo is not ready. Your file is unchanged; try the download again.');
    return image;
  }

  async function renderCanvas(mode) {
    if (!Object.hasOwn(MODES, mode)) throw new Error(`Unknown social size: ${mode}`);
    if (window.factoryPageReady) await window.factoryPageReady;
    const loadedFonts = await document.fonts.load('800 72px Manrope');
    await document.fonts.ready;
    if (!loadedFonts.length || !document.fonts.check('800 72px Manrope')) throw new Error('The brand font did not load. Your brief is unchanged; try the download again.');
    const config = MODES[mode];
    const canvas = document.createElement('canvas');
    canvas.width = config.width;
    canvas.height = config.height;
    const ctx = canvas.getContext('2d', {alpha: false});
    if (!ctx) throw new Error('This browser could not start the PNG renderer.');
    const data = brief();
    const logo = await loadLogo(mode === 'story', data.accent);
    const image = await selectedPhoto(data.layout);
    let report;
    if (mode === 'square') report = drawSquare(ctx, data, logo, image);
    else if (mode === 'story') report = drawStory(ctx, data, logo, image);
    else report = drawFacebook(ctx, data, logo, image);
    diagnostics[mode] = {width: config.width, height: config.height, layout: data.layout, ...report, qrError: window.factoryQR?.getLastError?.() || ''};
    return canvas;
  }

  function canvasBlob(canvas) {
    return new Promise((resolve, reject) => {
      try {
        canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('The browser returned an empty PNG.')), 'image/png');
      } catch (error) {
        reject(error);
      }
    });
  }

  async function createSocialReport(pageReady, renderSocial, getDiagnostics) {
    try {
      if (pageReady) await pageReady;
      const images = {};
      for (const mode of Object.keys(MODES)) images[mode] = await renderSocial(mode);
      return {ready: true, images, diagnostics: getDiagnostics()};
    } catch (error) {
      return {ready: false, error: error instanceof Error ? error.message : String(error), diagnostics: getDiagnostics()};
    }
  }

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    if (typeof module === 'object' && module.exports) module.exports = {wrapLines, fitCanvasText, drawCover, canvasBlob, createSocialReport};
    return;
  }

  window.factoryRenderSocial = async mode => (await renderCanvas(mode)).toDataURL('image/png');
  window.factorySocialDiagnostics = () => JSON.parse(JSON.stringify(diagnostics));

  async function download(mode, button) {
    const status = $('social-status');
    const label = MODES[mode].label;
    button.disabled = true;
    status.textContent = `Making your ${label}…`;
    try {
      if (!$('brief').reportValidity()) {
        status.textContent = 'Add the required headline and contact line, then download again.';
        return;
      }
      const canvas = await renderCanvas(mode);
      const blob = await canvasBlob(canvas);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `cultureshyft-${mode}.png`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      const shortenedFields = Object.entries(diagnostics[mode]?.fits || {}).filter(([, fit]) => fit.shortened).map(([name]) => name);
      status.textContent = shortenedFields.length
        ? `${label} downloaded, but ${shortenedFields.join(', ')} was shortened to fit. Your full text remains in the form. Shorten it there, then download again.`
        : `${label} downloaded. Next: open the PNG and check every detail before posting.`;
    } catch (error) {
      status.textContent = `${label} could not download. Your brief and photo are safe. Try the download again. If it keeps failing, copy your brief before reloading. ${error instanceof Error ? error.message : ''}`.trim();
    } finally {
      button.disabled = false;
    }
  }

  document.querySelectorAll('[data-social-export]').forEach(button => {
    button.addEventListener('click', () => download(button.dataset.socialExport, button));
  });

  async function runSocialExport() {
    const params = new URLSearchParams(location.search);
    if (params.get('check') !== '1' || params.get('social') !== '1') {
      if (window.factoryPageReady) await window.factoryPageReady;
      return window.factoryReport?.();
    }
    const report = await createSocialReport(
      window.factoryPageReady,
      window.factoryRenderSocial,
      window.factorySocialDiagnostics
    );
    let output = $('factory-social-report');
    if (!output) {
      output = document.createElement('script');
      output.id = 'factory-social-report';
      output.type = 'application/json';
    }
    // Chrome's DOM dump can observe an appended node before asynchronous PNG
    // rendering finishes. Populate it while detached so every visible marker
    // is valid JSON rather than an empty, intermittently unparsable report.
    output.textContent = JSON.stringify(report);
    if (!output.isConnected) document.body.append(output);
    return report;
  }

  // The public readiness contract includes every check-mode export and only
  // resolves after the complete social report is present in the DOM.
  window.factoryReady = runSocialExport();
})();
