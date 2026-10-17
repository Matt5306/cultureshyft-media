(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const STORAGE_KEY = 'cultureshyft.factory.ai.v1';
  const TIMEOUT_MS = 30000;
  const FIELD_LIMITS = Object.freeze({headline: 140, subheadline: 180, body: 450, cta: 100});
  const PROVIDERS = Object.freeze({
    gemini: Object.freeze({label: 'Gemini', adapter: 'gemini', model: 'gemini-3.6-flash', modelPlaceholder: '', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', keyRequired: true}),
    openai: Object.freeze({label: 'OpenAI', adapter: 'openai', model: 'gpt-6-luna', modelPlaceholder: '', baseUrl: 'https://api.openai.com/v1', keyRequired: true}),
    claude: Object.freeze({label: 'Claude', adapter: 'anthropic', model: 'claude-haiku-5-5', modelPlaceholder: '', baseUrl: 'https://api.anthropic.com/v1', keyRequired: true}),
    openrouter: Object.freeze({label: 'OpenRouter', adapter: 'openai', model: '', modelPlaceholder: 'provider/model', baseUrl: 'https://openrouter.ai/api/v1', keyRequired: true}),
    local: Object.freeze({label: 'Local AI', adapter: 'openai', model: '', modelPlaceholder: 'model name shown in LM Studio / Ollama', baseUrl: 'http://localhost:1234/v1', keyRequired: false})
  });
  const SYSTEM_PROMPT = `You write flyer copy for CultureShyft Media.
Voice: bold, warm, quick, and clear. Be confident without hype. Say "flyer", not "collateral". Speak to "you". Use short sentences with one idea each. Lead with what the reader gets. Write numbers as digits. Do not use exclamation marks. Spell CultureShyft exactly.
Return only a JSON object with string keys headline, subheadline, body, and cta. Maximum lengths: headline 140 characters; subheadline 180; body 450; cta 100. Never invent a date, place, price, contact detail, guarantee, or private customer detail.`;

  class AIError extends Error {
    constructor(code, status = 0) { super(code); this.name = 'AIError'; this.code = code; this.status = status; }
  }

  let storageAvailable = true;
  let storageWarning = '';
  let storageWarningShown = false;
  let activeRequest = null;
  let suggestions = null;
  let suggestionSnapshot = null;
  let undoValues = null;
  let dialogKeys = {};
  let dialogProvider = 'gemini';
  let dialogOpener = null;

  const defaultSettings = () => ({provider: 'gemini', model: PROVIDERS.gemini.model, baseUrl: PROVIDERS.local.baseUrl, keys: {}});
  function warnStorage() {
    storageAvailable = false;
    storageWarning = 'This browser blocked or ran out of storage. AI settings will stay in memory until you close this tab.';
  }
  function loadSettings() {
    const fallback = defaultSettings();
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return fallback;
      const saved = JSON.parse(raw);
      if (!saved || !Object.hasOwn(PROVIDERS, saved.provider) || typeof saved.model !== 'string' || typeof saved.baseUrl !== 'string' || !saved.keys || typeof saved.keys !== 'object' || Array.isArray(saved.keys)) throw new Error('invalid');
      const keys = {};
      for (const provider of Object.keys(PROVIDERS)) if (typeof saved.keys[provider] === 'string') keys[provider] = saved.keys[provider].slice(0, 500);
      return {provider: saved.provider, model: saved.model.slice(0, 200), baseUrl: saved.baseUrl.slice(0, 300) || PROVIDERS.local.baseUrl, keys};
    } catch (_) {
      warnStorage();
      return fallback;
    }
  }
  let settings = loadSettings();

  function persistSettings() {
    if (!storageAvailable) { showStorageWarning(); return false; }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
      return true;
    } catch (_) {
      warnStorage();
      showStorageWarning();
      return false;
    }
  }
  function showStorageWarning() {
    if (!storageWarning || storageWarningShown) return;
    const warning = $('ai-storage-warning');
    warning.textContent = storageWarning;
    warning.hidden = false;
    storageWarningShown = true;
  }

  function hasSecretShape(value) {
    return /(?:AIza[\w-]{16,}|sk-(?:ant-|proj-|or-)?[\w-]{12,}|bearer\s+[\w.-]{12,})/i.test(value);
  }
  function containsKnownKey(value) {
    return Object.values({...settings.keys, ...dialogKeys}).some(key => key && key.length >= 4 && value.includes(key));
  }
  function cleanModel(value, required = true) {
    const model = String(value || '').trim();
    if (required && !model) throw new AIError('model_required');
    if (model.length > 200 || /[?#\\\u0000-\u001f]/.test(model) || model.includes('://') || hasSecretShape(model) || containsKnownKey(model)) throw new AIError('model_invalid');
    return model;
  }
  function cleanKey(value, required) {
    const key = String(value || '').trim();
    if (required && !key) throw new AIError('key_required');
    if (key.length > 500 || /[\r\n]/.test(key)) throw new AIError('key_invalid');
    return key;
  }
  function cleanBaseUrl(value) {
    const raw = String(value || '').trim();
    if (!raw || raw.length > 300 || hasSecretShape(raw) || containsKnownKey(raw)) throw new AIError('base_invalid');
    let url;
    try { url = new URL(raw); } catch (_) { throw new AIError('base_invalid'); }
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password || url.search || url.hash) throw new AIError('base_invalid');
    return url.href.replace(/\/$/, '');
  }

  function configFromSettings() {
    const provider = Object.hasOwn(PROVIDERS, settings.provider) ? settings.provider : 'gemini';
    const definition = PROVIDERS[provider];
    return {
      provider,
      definition,
      model: cleanModel(settings.model || definition.model),
      baseUrl: provider === 'local' ? cleanBaseUrl(settings.baseUrl) : definition.baseUrl,
      key: cleanKey(settings.keys[provider], definition.keyRequired)
    };
  }
  function configFromDialog(required = true) {
    const provider = $('ai-provider').value;
    const definition = PROVIDERS[provider];
    if (!definition) throw new AIError('provider_invalid');
    const key = provider === 'local' ? '' : cleanKey($('ai-api-key').value, required && definition.keyRequired);
    return {
      provider,
      definition,
      model: cleanModel($('ai-model').value, required),
      baseUrl: provider === 'local' ? cleanBaseUrl($('ai-base-url').value) : definition.baseUrl,
      key
    };
  }
  function isConfigured() {
    try { configFromSettings(); return true; } catch (_) { return false; }
  }

  function requestOptions(headers, body, signal) {
    return {method: 'POST', headers, body: JSON.stringify(body), signal, credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer', cache: 'no-store'};
  }
  async function responseData(response) {
    if (!response.ok) throw new AIError('http', response.status);
    try { return await response.json(); } catch (_) { throw new AIError('malformed_response'); }
  }
  function requireText(text) {
    if (typeof text !== 'string' || !text.trim()) throw new AIError('blocked');
    return text.trim();
  }

  async function callGemini(config, prompts, signal) {
    const url = `${config.definition.baseUrl}/models/${encodeURIComponent(config.model)}:generateContent`;
    const body = {
      systemInstruction: {parts: [{text: prompts.system}]},
      contents: [{role: 'user', parts: [{text: prompts.user}]}],
      generationConfig: {responseMimeType: 'application/json', maxOutputTokens: prompts.test ? 40 : 700}
    };
    const data = await responseData(await fetch(url, requestOptions({'Content-Type': 'application/json', 'x-goog-api-key': config.key}, body, signal)));
    if (data?.promptFeedback?.blockReason || !Array.isArray(data?.candidates) || !data.candidates.length) throw new AIError('blocked');
    const candidate = data.candidates[0];
    if (/SAFETY|BLOCKLIST|PROHIBITED|RECITATION|SPII/i.test(String(candidate?.finishReason || ''))) throw new AIError('blocked');
    return requireText(candidate?.content?.parts?.map(part => part?.text || '').join(''));
  }

  async function callOpenAICompatible(config, prompts, signal) {
    const endpoint = `${config.baseUrl.replace(/\/$/, '')}/chat/completions`;
    const headers = {'Content-Type': 'application/json'};
    if (config.key) headers.Authorization = `Bearer ${config.key}`;
    const body = {model: config.model, messages: [{role: 'system', content: prompts.system}, {role: 'user', content: prompts.user}], max_tokens: prompts.test ? 40 : 700, response_format: {type: 'json_object'}};
    const data = await responseData(await fetch(endpoint, requestOptions(headers, body, signal)));
    const choice = data?.choices?.[0];
    if (choice?.message?.refusal || choice?.finish_reason === 'content_filter') throw new AIError('blocked');
    const content = choice?.message?.content;
    const text = Array.isArray(content) ? content.map(part => typeof part === 'string' ? part : part?.text || '').join('') : content;
    return requireText(text);
  }

  async function callAnthropic(config, prompts, signal) {
    const body = {model: config.model, max_tokens: prompts.test ? 40 : 700, system: prompts.system, messages: [{role: 'user', content: prompts.user}]};
    const headers = {'Content-Type': 'application/json', 'x-api-key': config.key, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true'};
    const data = await responseData(await fetch(`${config.definition.baseUrl}/messages`, requestOptions(headers, body, signal)));
    if (data?.stop_reason === 'refusal' || data?.content?.some(part => part?.type === 'refusal')) throw new AIError('blocked');
    return requireText(data?.content?.filter(part => part?.type === 'text').map(part => part.text || '').join(''));
  }

  function callProvider(config, prompts, signal) {
    if (config.definition.adapter === 'gemini') return callGemini(config, prompts, signal);
    if (config.definition.adapter === 'openai') return callOpenAICompatible(config, prompts, signal);
    return callAnthropic(config, prompts, signal);
  }

  function setBusy(kind, busy) {
    $('ai-write-button').disabled = busy;
    $('ai-test-connection').disabled = busy;
    $('ai-save-settings').disabled = busy;
    $('ai-write-button').textContent = busy && kind === 'write' ? 'Working...' : 'Write it for me';
    $('ai-cancel-button').hidden = !(busy && kind === 'write');
    $('ai-test-connection').textContent = busy && kind === 'test' ? 'Working...' : 'Test connection';
    $('ai-test-cancel-button').hidden = !(busy && kind === 'test');
  }
  async function withRequest(kind, task) {
    if (activeRequest) throw new AIError('busy');
    const record = {kind, controller: new AbortController(), reason: '', timer: 0};
    activeRequest = record;
    setBusy(kind, true);
    record.timer = setTimeout(() => { record.reason = 'timeout'; record.controller.abort(); }, TIMEOUT_MS);
    try {
      const value = await task(record.controller.signal);
      if (record.controller.signal.aborted) throw new AIError(record.reason || 'cancelled');
      return value;
    } catch (error) {
      if (record.reason === 'timeout') throw new AIError('timeout');
      if (record.reason === 'cancelled') throw new AIError('cancelled');
      throw error;
    } finally {
      clearTimeout(record.timer);
      if (activeRequest === record) activeRequest = null;
      setBusy('', false);
    }
  }
  function cancelRequest(kind) {
    if (!activeRequest || (kind && activeRequest.kind !== kind)) return;
    activeRequest.reason = 'cancelled';
    activeRequest.controller.abort();
  }

  function localConnectionFix() {
    return 'Could not reach the local AI server. In LM Studio, turn on Enable CORS in the Developer tab and Start server. For Ollama, set OLLAMA_ORIGINS=https://cultureshyftmedia.com, then restart Ollama. Safari on iPad usually cannot reach a local http:// server from this https page, so use Gemini on the iPad.';
  }
  function messageFor(error, config) {
    const code = error instanceof AIError ? error.code : 'connection';
    const label = config?.definition?.label || 'The AI provider';
    if (code === 'cancelled') return 'Cancelled. Nothing changed.';
    if (code === 'timeout') return 'The AI did not answer within 30 seconds. Try again, or choose another model.';
    if (code === 'busy') return 'One AI request is already working. Cancel it before starting another.';
    if (code === 'key_required') return `Add your ${label} API key, then try again.`;
    if (code === 'key_invalid') return 'That key contains characters a key cannot use. Paste the key again.';
    if (code === 'model_required') return 'Enter the model name shown by your provider, then try again.';
    if (code === 'model_invalid') return 'That model name is not safe to use. Copy only the model name from your provider.';
    if (code === 'base_invalid') return 'Enter the Local AI base URL without a key, query, or # section. Use http://localhost:1234/v1 for LM Studio or http://localhost:11434/v1 for Ollama.';
    if (code === 'blocked') return `${label} blocked the content or returned no usable text. Remove sensitive details and try again.`;
    if (code === 'malformed_response' || code === 'invalid_json') return `${label} answered, but the answer was not valid JSON. Try again or choose another model.`;
    if (code === 'http') {
      if (error.status === 400 || error.status === 401) return config?.provider === 'gemini' ? 'Gemini did not accept that key. Open Google AI Studio, make a new key, paste it here.' : `${label} did not accept that key. Make a new key in your provider account, then paste it here.`;
      if (error.status === 403) return `${label} refused this request. Check that the key can use this model and that browser access is allowed.`;
      if (error.status === 404) return `${label} could not find that model. Copy the current model name from your provider and try again.`;
      if (error.status === 429) return `${label} reached its quota or rate limit. Wait a minute or try another model.`;
      if (error.status >= 500) return `${label} is temporarily unavailable. Your flyer is unchanged; wait a minute and try again.`;
      return `${label} refused the request. Check the provider, model, and key, then try again.`;
    }
    if (navigator.onLine === false) return 'You appear to be offline. Reconnect to the internet, then try again. Nothing changed.';
    if (config?.provider === 'local') return localConnectionFix();
    return `Could not make a connection to ${label}. Check your internet connection and provider settings, then try again.`;
  }

  function scrubSuggestion(value, config) {
    let text = String(value || '').trim();
    const keys = new Set([config?.key, ...Object.values(settings.keys), ...Object.values(dialogKeys)]);
    for (const key of keys) if (key && key.length >= 4) text = text.split(key).join('[key removed]');
    return text.replace(/(?:AIza[\w-]{16,}|sk-(?:ant-|proj-|or-)?[\w-]{12,}|bearer\s+[\w.-]{12,})/gi, '[key removed]');
  }
  function parseSuggestion(raw, config) {
    let text = String(raw || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');
    const start = text.indexOf('{'); const end = text.lastIndexOf('}');
    if (start < 0 || end <= start) throw new AIError('invalid_json');
    let parsed;
    try { parsed = JSON.parse(text.slice(start, end + 1)); } catch (_) { throw new AIError('invalid_json'); }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new AIError('invalid_json');
    const result = {};
    for (const [field, limit] of Object.entries(FIELD_LIMITS)) {
      if (typeof parsed[field] !== 'string') throw new AIError('invalid_json');
      result[field] = scrubSuggestion(parsed[field], config).slice(0, limit).trim();
    }
    return result;
  }

  function briefSnapshot() {
    return {headline: $('headline').value, subheadline: $('subheadline').value, body: $('body').value, cta: $('cta').value};
  }
  function generationPrompts(snapshot) {
    const selected = $('preset').value ? $('preset').selectedOptions[0]?.textContent || $('preset').value : 'No sample selected';
    const safeBrief = {occasion: selected, headline: snapshot.headline, subheadline: snapshot.subheadline, date: $('date').value, place: $('place').value, body: snapshot.body, cta: snapshot.cta};
    const user = `Write the 4 requested fields using only this flyer information. Keep accurate details already supplied.
Occasion: ${safeBrief.occasion}
Headline: ${safeBrief.headline}
Subheadline: ${safeBrief.subheadline}
Date and time: ${safeBrief.date}
Place: ${safeBrief.place}
Body: ${safeBrief.body}
Call to action: ${safeBrief.cta}`;
    return {system: SYSTEM_PROMPT, user, test: false};
  }
  const testPrompts = () => ({system: 'This is a connection test. Return JSON only.', user: 'Return exactly {"ok":true}.', test: true});

  function renderSuggestions() {
    const labels = {headline: 'Headline', subheadline: 'Subheadline', body: 'Body', cta: 'Call to action'};
    const list = $('ai-comparison-list');
    list.replaceChildren();
    for (const field of Object.keys(FIELD_LIMITS)) {
      const row = document.createElement('article'); row.className = 'ai-comparison'; row.dataset.aiField = field;
      const heading = document.createElement('h3'); heading.textContent = labels[field];
      const current = document.createElement('p'); current.className = 'ai-copy ai-current'; current.textContent = suggestionSnapshot[field] || '—';
      const suggested = document.createElement('p'); suggested.className = 'ai-copy ai-suggested'; suggested.textContent = suggestions[field] || '—';
      const use = document.createElement('button'); use.type = 'button'; use.className = 'quiet-button'; use.dataset.aiUse = field; use.textContent = 'Use this';
      use.addEventListener('click', () => applySuggestion([field]));
      row.append(heading, current, suggested, use); list.append(row);
    }
    $('ai-suggestions').hidden = false;
    $('ai-undo').hidden = !undoValues;
  }
  function setField(field, value) {
    $(field).value = String(value).slice(0, FIELD_LIMITS[field]);
    $(field).dispatchEvent(new Event('input', {bubbles: true}));
  }
  function applySuggestion(fields) {
    if (!suggestions) return;
    const previous = briefSnapshot();
    fields.forEach(field => setField(field, suggestions[field]));
    undoValues = previous;
    $('ai-undo').hidden = false;
    $('ai-write-status').textContent = fields.length === 1 ? 'Suggestion used. Check it in the flyer. Undo is available.' : 'Suggestions used. Check every detail in the flyer. Undo is available.';
  }
  function undo() {
    if (!undoValues) return;
    const restore = undoValues; undoValues = null;
    Object.keys(FIELD_LIMITS).forEach(field => setField(field, restore[field]));
    $('ai-undo').hidden = true;
    $('ai-write-status').textContent = 'Undone. Your exact previous text is back.';
  }

  async function writeForMe() {
    if (!isConfigured()) {
      $('ai-write-status').textContent = 'Connect an AI provider first.';
      openSettings($('ai-write-button'));
      return;
    }
    let config;
    try { config = configFromSettings(); } catch (error) { $('ai-write-status').textContent = messageFor(error); openSettings($('ai-write-button')); return; }
    const snapshot = briefSnapshot();
    $('ai-write-status').textContent = `${config.definition.label} is writing. Your flyer will not change until you use a suggestion.`;
    try {
      const raw = await withRequest('write', signal => callProvider(config, generationPrompts(snapshot), signal));
      suggestions = parseSuggestion(raw, config);
      suggestionSnapshot = snapshot;
      renderSuggestions();
      $('ai-write-status').textContent = 'Suggestion ready. Compare it with your text, then choose what to use.';
    } catch (error) {
      $('ai-write-status').textContent = messageFor(error, config);
    }
  }

  function rememberDialogKey() {
    if (dialogProvider !== 'local') dialogKeys[dialogProvider] = $('ai-api-key').value;
  }
  function updateProviderFields(resetModel) {
    rememberDialogKey();
    const provider = $('ai-provider').value;
    const definition = PROVIDERS[provider];
    dialogProvider = provider;
    if (resetModel) $('ai-model').value = definition.model;
    $('ai-model').placeholder = definition.modelPlaceholder;
    $('ai-base-url-group').hidden = provider !== 'local';
    $('ai-key-group').hidden = provider === 'local';
    $('ai-forget-key').hidden = provider === 'local';
    $('ai-api-key').value = provider === 'local' ? '' : dialogKeys[provider] || '';
    $('ai-api-key').type = 'password'; $('ai-show-key').textContent = 'Show'; $('ai-show-key').setAttribute('aria-pressed', 'false');
    $('ai-forget-confirm').hidden = true;
    $('ai-settings-status').textContent = '';
  }
  function openSettings(opener = document.activeElement) {
    dialogOpener = opener instanceof HTMLElement ? opener : null;
    dialogKeys = {...settings.keys};
    dialogProvider = settings.provider;
    $('ai-provider').value = settings.provider;
    $('ai-model').value = settings.model || PROVIDERS[settings.provider].model;
    $('ai-base-url').value = settings.baseUrl || PROVIDERS.local.baseUrl;
    $('ai-api-key').value = dialogKeys[settings.provider] || '';
    updateProviderFields(false);
    if (storageWarning && !storageWarningShown) showStorageWarning();
    $('ai-settings-dialog').showModal();
    $('ai-provider').focus();
  }
  function closeSettings() {
    if (activeRequest?.kind === 'test') cancelRequest('test');
    if ($('ai-settings-dialog').open) $('ai-settings-dialog').close();
    $('ai-api-key').value = '';
    $('ai-api-key').type = 'password';
    $('ai-show-key').textContent = 'Show';
    $('ai-show-key').setAttribute('aria-pressed', 'false');
    dialogKeys = {};
    const opener = dialogOpener; dialogOpener = null;
    if (opener?.isConnected) opener.focus();
  }
  function saveSettings(event) {
    event.preventDefault();
    rememberDialogKey();
    let config;
    try { config = configFromDialog(false); } catch (error) { $('ai-settings-status').textContent = messageFor(error); return; }
    const keys = {...settings.keys, ...dialogKeys};
    if (config.provider !== 'local') keys[config.provider] = config.key;
    let baseUrl;
    try { baseUrl = cleanBaseUrl($('ai-base-url').value); } catch (error) { $('ai-settings-status').textContent = messageFor(error); return; }
    settings = {provider: config.provider, model: config.model, baseUrl, keys};
    const saved = persistSettings();
    if (saved) {
      $('ai-write-status').textContent = 'AI helper settings saved on this browser.';
      closeSettings();
    } else {
      $('ai-settings-status').textContent = 'Settings are ready for this tab only. Keep this page open to use them.';
    }
  }
  async function testConnection() {
    let config;
    try { config = configFromDialog(true); } catch (error) { $('ai-settings-status').textContent = messageFor(error); return; }
    $('ai-settings-status').textContent = `Testing ${config.definition.label}…`;
    try {
      await withRequest('test', signal => callProvider(config, testPrompts(), signal));
      $('ai-settings-status').textContent = `Connected. ${config.definition.label} answered.`;
    } catch (error) {
      $('ai-settings-status').textContent = messageFor(error, config);
    }
  }
  function forgetKey() {
    const provider = $('ai-provider').value;
    const targets = new Set([$('ai-api-key').value.trim(), dialogKeys[provider], settings.keys[provider]].filter(Boolean));
    const stores = [];
    const blocked = [];
    const reset = [];
    // Read both owned settings records before deleting: a stored copy can differ
    // from the current dialog or memory (for example after an unsaved edit).
    for (const name of ['localStorage', 'sessionStorage']) {
      try {
        const storage = window[name];
        const raw = storage.getItem(STORAGE_KEY);
        const saved = raw ? JSON.parse(raw) : null;
        if (saved && (!saved.keys || typeof saved.keys !== 'object' || Array.isArray(saved.keys))) throw new Error('invalid');
        if (saved?.keys[provider]) targets.add(saved.keys[provider]);
        stores.push({name, storage, saved});
      } catch (_) {
        try { window[name].removeItem(STORAGE_KEY); reset.push(name); }
        catch (_) { blocked.push(name); }
      }
    }
    const removed = new Set();
    function removeCopies(keys) {
      for (const [slot, key] of Object.entries(keys)) {
        if (slot === provider || targets.has(key)) {
          if (key) removed.add(PROVIDERS[slot]?.label || slot);
          delete keys[slot];
        }
      }
    }
    cancelRequest();
    removeCopies(dialogKeys);
    removeCopies(settings.keys);
    $('ai-api-key').value = '';
    for (const {name, storage, saved} of stores) {
      if (!saved) continue;
      removeCopies(saved.keys);
      try { storage.setItem(STORAGE_KEY, JSON.stringify(saved)); }
      catch (_) {
        try { storage.removeItem(STORAGE_KEY); reset.push(name); }
        catch (_) { blocked.push(name); }
      }
    }
    $('ai-forget-confirm').hidden = true;
    const slots = [...removed].join(', ') || PROVIDERS[provider].label;
    let message = `Key forgotten from ${slots} in this tab's memory and local/session storage. All matching provider copies were removed.`;
    if (reset.length) message += ` ${reset.join(' and ')} would not update, so its saved AI settings were removed. Other settings in this open tab remain available.`;
    if (blocked.length) message = `Key removed from this tab's memory (${slots}), but ${blocked.join(' and ')} blocked removal. Your flyers are unchanged. Revoke the key with your provider; export your flyers and invoices before clearing this site's browser data.`;
    $('ai-settings-status').textContent = message;
  }

  $('open-ai-settings').addEventListener('click', event => openSettings(event.currentTarget));
  $('ai-close-settings').addEventListener('click', closeSettings);
  $('ai-settings-dialog').addEventListener('cancel', event => { event.preventDefault(); closeSettings(); });
  $('ai-settings-dialog').addEventListener('click', event => { if (event.target === $('ai-settings-dialog')) closeSettings(); });
  $('ai-settings-form').addEventListener('submit', saveSettings);
  $('ai-provider').addEventListener('change', () => updateProviderFields(true));
  $('ai-show-key').addEventListener('click', () => {
    const show = $('ai-api-key').type === 'password';
    $('ai-api-key').type = show ? 'text' : 'password'; $('ai-show-key').textContent = show ? 'Hide' : 'Show'; $('ai-show-key').setAttribute('aria-pressed', String(show));
  });
  $('ai-test-connection').addEventListener('click', testConnection);
  $('ai-test-cancel-button').addEventListener('click', () => cancelRequest('test'));
  $('ai-forget-key').addEventListener('click', () => { $('ai-forget-confirm').hidden = false; $('ai-forget-confirm-no').focus(); });
  $('ai-forget-confirm-no').addEventListener('click', () => { $('ai-forget-confirm').hidden = true; $('ai-forget-key').focus(); });
  $('ai-forget-confirm-yes').addEventListener('click', forgetKey);
  $('ai-write-button').addEventListener('click', writeForMe);
  $('ai-cancel-button').addEventListener('click', () => cancelRequest('write'));
  $('ai-use-all').addEventListener('click', () => applySuggestion(Object.keys(FIELD_LIMITS)));
  $('ai-undo').addEventListener('click', undo);
  for (const field of Object.keys(FIELD_LIMITS)) $(field).addEventListener('input', () => {
    undoValues = null;
    $('ai-undo').hidden = true;
  });

  window.factoryAI = Object.freeze({PROVIDERS, openSettings, parseSuggestion});
})();
