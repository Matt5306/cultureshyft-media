(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const DRAFT_KEY = 'cultureshyft.factory.draft.v1';
  const BRIEFS_KEY = 'cultureshyft.factory.briefs.v1';
  const params = new URLSearchParams(location.search);
  const hasSharedBrief = params.has('brief') || new URLSearchParams(location.hash.slice(1)).has('brief');
  let demoMode = params.has('demo') || hasSharedBrief;
  let activeId = null;
  let deletedActive = false;
  let timer = 0;
  const blockedKeys = new Set();
  const REVIEW_NOTE = 'Review before printing. Have someone who speaks Spanish check this translation.';
  let translation = null;
  const originalBrief = window.factoryBrief;
  // Carry translation metadata through open, autosave and JSON export without
  // putting it in the flyer form or changing the English draft on separate save.
  window.factoryBrief = Object.freeze({
    collect() {
      const payload = originalBrief.collect();
      if (translation) payload.translation = JSON.parse(JSON.stringify(translation));
      return payload;
    },
    apply(payload) {
      validateImport(payload);
      translation = payload.translation ? JSON.parse(JSON.stringify(payload.translation)) : null;
      $('brief-translation-note').hidden = !translation;
      $('brief-translation-note').textContent = translation ? REVIEW_NOTE : '';
      originalBrief.apply(payload);
    }
  });

  const status = message => { $('save-status').textContent = message; };
  const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
  const titleOf = payload => String(payload?.translation?.name || payload?.values?.headline || '').trim() || 'Untitled flyer';

  function read(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : fallback;
    } catch (_) {
      blockedKeys.add(key);
      status('Saved work on this device is damaged. It will not be overwritten. Your open brief is unchanged; export it now for a safe copy.');
      return fallback;
    }
  }

  function write(key, value) {
    if (blockedKeys.has(key)) {
      status('Damaged saved work will not be overwritten. Export your open brief before clearing this site’s browser data.');
      return false;
    }
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      status('This device is out of browser storage. Your open brief is still here; export it now before closing this page.');
      return false;
    }
  }

  function savedBriefs() {
    const result = read(BRIEFS_KEY, []);
    if (!Array.isArray(result)) {
      blockedKeys.add(BRIEFS_KEY);
      status('The saved flyer list is damaged and will not be overwritten. Export your open brief before clearing browser data.');
      return [];
    }
    let malformed = false;
    for (const item of result) {
      try { if (!item || typeof item.id !== 'string') throw new Error('entry'); validateImport(item.payload); }
      catch (_) { malformed = true; break; }
    }
    if (malformed) {
      blockedKeys.add(BRIEFS_KEY);
      status('One or more saved flyers are damaged. The list will not be overwritten; export your open brief before clearing browser data.');
      return [];
    }
    return result;
  }

  function flush(options = {}) {
    clearTimeout(timer);
    const now = new Date().toISOString();
    const payload = window.factoryBrief.collect();
    let id = activeId;
    const briefs = savedBriefs();
    if (options.keepInLibrary && !deletedActive && !id && (titleOf(payload) !== 'Untitled flyer' || payload.values.contact)) id = uid();
    if (id) {
      const entry = {id, updatedAt: now, payload};
      const index = briefs.findIndex(item => item.id === id);
      if (index >= 0) briefs[index] = entry; else briefs.unshift(entry);
      if (!write(BRIEFS_KEY, briefs)) return false;
      activeId = id;
    }
    if (!write(DRAFT_KEY, {updatedAt: now, activeId, deletedActive, payload})) return false;
    status('Saved on this device just now.');
    return true;
  }

  function autosave() {
    if (demoMode) return;
    deletedActive = false;
    clearTimeout(timer);
    timer = setTimeout(() => flush(), 300);
  }

  function saveCurrent() {
    const briefs = savedBriefs();
    const now = new Date().toISOString();
    const entry = {id: activeId || uid(), updatedAt: now, payload: window.factoryBrief.collect()};
    const index = briefs.findIndex(item => item.id === entry.id);
    if (index >= 0) briefs[index] = entry; else briefs.unshift(entry);
    if (!write(BRIEFS_KEY, briefs)) return;
    activeId = entry.id;
    deletedActive = false;
    if (!write(DRAFT_KEY, {updatedAt: now, activeId, deletedActive, payload: entry.payload})) return;
    // The draft now holds exactly this form. A debounced autosave queued just
    // before this save (tapping Save blurs a field, which fires change) would
    // only rewrite the same payload with a new time 300 ms later, so cancel it.
    // On a failed write above it stays queued as the fallback.
    clearTimeout(timer);
    demoMode = false;
    status(`“${titleOf(entry.payload)}” is saved in My flyers.`);
    renderList();
  }

  function formatDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? 'Saved on this device' : new Intl.DateTimeFormat(undefined, {month: 'short', day: 'numeric', year: 'numeric'}).format(date);
  }

  function saveSeparate(payload) {
    try {
      const copy = JSON.parse(JSON.stringify(validateImport(payload)));
      const briefs = savedBriefs();
      briefs.unshift({id: uid(), updatedAt: new Date().toISOString(), payload: copy});
      if (!write(BRIEFS_KEY, briefs)) return false;
      renderList();
      return true;
    } catch (_) { return false; }
  }

  function action(label, className, handler) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = className; button.textContent = label;
    button.addEventListener('click', handler);
    return button;
  }

  function renderList() {
    const list = $('brief-list');
    list.replaceChildren();
    const briefs = savedBriefs();
    if (!briefs.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-briefs'; empty.textContent = 'No saved flyers yet. Close this drawer and choose “Save to My flyers.”';
      list.append(empty); return;
    }
    briefs.forEach(entry => {
      const card = document.createElement('article'); card.className = 'brief-card';
      const copy = document.createElement('div');
      const heading = document.createElement('h3'); heading.textContent = titleOf(entry.payload);
      const date = document.createElement('p'); date.textContent = formatDate(entry.updatedAt);
      copy.append(heading, date);
      if (entry.payload.translation) {
        const note = document.createElement('p');
        note.className = 'translation-review-note'; note.textContent = REVIEW_NOTE;
        copy.append(note);
      }
      const actions = document.createElement('div'); actions.className = 'brief-card-actions';
      actions.append(
        action('Open', 'brief-open', () => {
          if (!demoMode && !flush({keepInLibrary: true})) return;
          window.factoryBrief.apply(entry.payload); activeId = entry.id; closeDrawer();
          demoMode = false;
          status(`Opened “${titleOf(entry.payload)}.” Changes autosave as your current brief.`); autosave();
        }),
        action('Duplicate', 'quiet-button', () => {
          if (!demoMode && !flush({keepInLibrary: true})) return;
          const duplicate = {id: uid(), updatedAt: new Date().toISOString(), payload: JSON.parse(JSON.stringify(entry.payload))};
          duplicate.payload.values.headline = `${String(duplicate.payload.values.headline || '').trim() || 'Untitled flyer'} copy`.slice(0, 140);
          if (duplicate.payload.translation) duplicate.payload.translation.name = `${titleOf(entry.payload)} copy`.slice(0, 160);
          const next = savedBriefs(); next.unshift(duplicate);
          if (write(BRIEFS_KEY, next)) { activeId = duplicate.id; window.factoryBrief.apply(duplicate.payload); renderList(); status('Copy created and opened.'); }
        }),
        action('Delete', 'quiet-button danger-button', () => showDelete(card, entry))
      );
      card.append(copy, actions); list.append(card);
    });
  }

  function showDelete(card, entry) {
    card.querySelector('.brief-card-actions').hidden = true;
    const confirm = document.createElement('div'); confirm.className = 'delete-confirm';
    const prompt = document.createElement('p'); prompt.textContent = `Remove “${titleOf(entry.payload)}” from this device? Export it first if you may need it later.`;
    confirm.append(prompt,
      action('Keep it', 'quiet-button', () => { confirm.remove(); card.querySelector('.brief-card-actions').hidden = false; }),
      action('Remove', 'danger-button', () => {
        const next = savedBriefs().filter(item => item.id !== entry.id);
        if (write(BRIEFS_KEY, next)) {
          if (activeId === entry.id) {
            activeId = null;
            deletedActive = true;
            if (!write(DRAFT_KEY, {updatedAt: new Date().toISOString(), activeId: null, deletedActive, payload: window.factoryBrief.collect()})) { renderList(); return; }
          }
          renderList(); status('Saved flyer removed. Your open brief is unchanged.');
        }
      })
    );
    card.append(confirm);
  }

  function openDrawer() {
    if (!demoMode && !flush()) return;
    renderList();
    $('briefs-drawer').classList.add('open'); $('briefs-drawer').setAttribute('aria-hidden', 'false');
    $('drawer-scrim').hidden = false; $('open-briefs').setAttribute('aria-expanded', 'true'); $('close-briefs').focus();
  }
  function closeDrawer() {
    $('briefs-drawer').classList.remove('open'); $('briefs-drawer').setAttribute('aria-hidden', 'true');
    $('drawer-scrim').hidden = true; $('open-briefs').setAttribute('aria-expanded', 'false');
  }

  function validateImport(candidate) {
    const payload = candidate?.payload || candidate;
    if (!payload || payload.version !== 1 || !payload.values || typeof payload.values !== 'object') throw new Error('That file is not a Flyer Factory brief.');
    if (payload.translation) {
      const info = payload.translation;
      if (info.language !== 'es' || info.reviewNote !== REVIEW_NOTE || typeof info.name !== 'string' || info.name.length > 160 || !info.social || typeof info.social !== 'object' || Array.isArray(info.social)) throw new Error('The Spanish draft details are damaged.');
      for (const [field, limit] of Object.entries({instagramCaption: 2200, facebookDescription: 5000})) {
        if (Object.hasOwn(info.social, field) && (typeof info.social[field] !== 'string' || info.social[field].length > limit)) throw new Error('The Spanish post is too long or damaged.');
      }
    }
    const maximums = {layout: 20, headline: 140, subheadline: 180, date: 100, place: 140, body: 450, cta: 100, contact: 160, qrUrl: 140, clientName: 100, clientEmail: 160, extraSizes: 2, extraEdits: 2};
    for (const [key, maximum] of Object.entries(maximums)) {
      if (Object.hasOwn(payload.values, key) && typeof payload.values[key] !== 'string') throw new Error(`The ${key} field is damaged.`);
      if (String(payload.values[key] || '').length > maximum) throw new Error(`The ${key} field is too long.`);
    }
    if (!['poster', 'event', 'announcement'].includes(payload.values.layout || 'poster')) throw new Error('The layout is not recognized.');
    for (const flag of ['accent', 'printReady', 'rush']) if (Object.hasOwn(payload.values, flag) && typeof payload.values[flag] !== 'boolean') throw new Error('A color or add-on setting is damaged.');
    for (const key of ['extraSizes', 'extraEdits']) if (payload.values[key] && !/^(?:[0-9]|10)$/.test(payload.values[key])) throw new Error('The extra quantity is outside the supported range.');
    if (payload.photo?.dataUrl && !/^data:image\/(jpeg|png|webp);base64,/i.test(payload.photo.dataUrl)) throw new Error('The saved photo is damaged.');
    if (payload.photo?.dataUrl?.length > 5 * 1024 * 1024) throw new Error('The saved photo is too large for this device.');
    for (const key of ['focusX', 'focusY', 'zoom']) if (payload.photo && Object.hasOwn(payload.photo, key) && !Number.isFinite(Number(payload.photo[key]))) throw new Error('The photo crop settings are damaged.');
    if (payload.photo && ((Object.hasOwn(payload.photo, 'focusX') && (Number(payload.photo.focusX) < 0 || Number(payload.photo.focusX) > 1)) || (Object.hasOwn(payload.photo, 'focusY') && (Number(payload.photo.focusY) < 0 || Number(payload.photo.focusY) > 1)) || (Object.hasOwn(payload.photo, 'zoom') && (Number(payload.photo.zoom) < 1 || Number(payload.photo.zoom) > 2.5)))) throw new Error('The photo crop settings are outside the supported range.');
    return payload;
  }

  async function validatePhoto(payload) {
    if (!payload.photo?.dataUrl) return payload;
    const image = new Image(); image.src = payload.photo.dataUrl;
    try { await image.decode(); } catch (_) { throw new Error('The saved photo cannot be opened.'); }
    if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 30000000) throw new Error('The saved photo dimensions are not safe to open.');
    return payload;
  }

  $('brief').addEventListener('factory:briefapplied', event => {
    if (!event.detail || !Object.hasOwn(event.detail, 'translation')) return;
    translation = event.detail.translation ? JSON.parse(JSON.stringify(event.detail.translation)) : null;
    $('brief-translation-note').hidden = !translation;
    $('brief-translation-note').textContent = translation ? REVIEW_NOTE : '';
  });
  $('brief').addEventListener('input', autosave);
  $('brief').addEventListener('change', autosave);
  $('brief').addEventListener('factory:briefapplied', autosave);
  window.addEventListener('factory:photochange', autosave);
  $('save-brief').addEventListener('click', saveCurrent);
  $('open-briefs').addEventListener('click', openDrawer);
  $('close-briefs').addEventListener('click', closeDrawer);
  $('drawer-scrim').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && $('briefs-drawer').classList.contains('open')) closeDrawer(); });
  window.addEventListener('pagehide', () => { if (!demoMode) flush(); });
  document.addEventListener('visibilitychange', () => { if (!demoMode && document.visibilityState === 'hidden') flush(); });

  $('export-brief').addEventListener('click', () => {
    const exported = {format: 'CultureShyft Flyer Factory brief', exportedAt: new Date().toISOString(), payload: window.factoryBrief.collect()};
    const blob = new Blob([JSON.stringify(exported, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = `${titleOf(exported.payload).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'flyer'}-brief.json`;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    status('Brief exported. Keep the JSON file with the project photos.');
  });

  $('import-brief').addEventListener('change', async () => {
    const file = $('import-brief').files[0]; $('import-brief').value = '';
    if (!file) return;
    if (file.size > 16 * 1024 * 1024) { status('That brief is too large to import. Your open brief is unchanged.'); return; }
    try {
      const payload = await validatePhoto(validateImport(JSON.parse(await file.text())));
      if (!flush({keepInLibrary: true})) return;
      window.factoryBrief.apply(payload); activeId = null; autosave();
      status('Brief imported and opened. Choose “Save to My flyers” to keep it in your list.');
    } catch (error) {
      status(`${error instanceof Error ? error.message : 'That brief could not be imported.'} Your open brief is unchanged.`);
    }
  });

  if (!params.has('demo') && !hasSharedBrief) {
    const draft = read(DRAFT_KEY, null);
    if (draft?.payload) {
      try { window.factoryBrief.apply(validateImport(draft)); activeId = typeof draft.activeId === 'string' ? draft.activeId : null; deletedActive = draft.deletedActive === true; status(`Recovered your autosaved brief from ${formatDate(draft.updatedAt)}.`); }
      catch (_) { blockedKeys.add(DRAFT_KEY); status('The last autosave is damaged and will not be overwritten. Start here, then export your new brief before clearing browser data.'); }
    }
  } else {
    status('Sample preview. Choose “Save to My flyers” to keep this sample and turn on autosave for your edits.');
  }
  window.factoryBriefs = Object.freeze({saved: savedBriefs, saveCurrent, saveSeparate, autosave, flush, validateImport, openDrawer, REVIEW_NOTE});
})();
