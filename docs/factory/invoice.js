(() => {
  'use strict';

  const CATALOG = Object.freeze({
    flyer: Object.freeze({id: 'flyer', label: 'Flyer', detail: 'US Letter PDF + Instagram square PNG, 1 edit round', unitPrice: 20}),
    extraSize: Object.freeze({id: 'extraSize', label: 'Additional size', detail: 'One additional social or print size', unitPrice: 5}),
    extraEdit: Object.freeze({id: 'extraEdit', label: 'Additional edit round', detail: 'One edit round beyond the included round', unitPrice: 5}),
    printReady: Object.freeze({id: 'printReady', label: 'Print-ready add-on', detail: 'Commercial printer preparation', unitPrice: 10}),
    rush: Object.freeze({id: 'rush', label: 'Rush add-on', detail: '24-hour turnaround, when available', unitPrice: 15})
  });
  const STORAGE = Object.freeze({counter: 'csm.invoice.counter.v1', settings: 'csm.invoice.payment.v1', draft: 'csm.invoice.draft.v1'});
  const DEMO = Object.freeze({
    invoiceNumber: 'CSM-20261011-01', invoiceDate: '2026-10-11', dueDate: '2026-10-25',
    clientName: 'Jordan Brooks', clientEmail: 'jordan@example.com', organisation: 'Bright Path Community Center',
    project: 'Fall community fundraiser', notes: '50% deposit starts the project. Balance is due when the final files are delivered.',
    quantities: {flyer: 1, extraSize: 1, extraEdit: 0, printReady: 1, rush: 1},
    payment: {cashApp: '$CultureShyft', zelle: 'mark@cultureshyftmedia.com', paypal: 'https://paypal.me/CultureShyft'}
  });
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const INVOICE_NUMBER = /^CSM-\d{8}-\d{2,12}$/;
  const clampQuantity = value => Math.max(0, Math.min(99, Math.floor(Number(value) || 0)));
  const cents = value => Math.round((Number(value) || 0) * 100);

  // Pure and intentionally small: the browser check and Node can exercise the
  // same invoice arithmetic without depending on DOM state.
  function calculate(lines) {
    const subtotalCents = (Array.isArray(lines) ? lines : []).reduce((sum, line) => {
      const quantity = clampQuantity(line?.quantity ?? line?.qty);
      const unitCents = Math.max(0, cents(line?.unitPrice ?? line?.price));
      return sum + quantity * unitCents;
    }, 0);
    const depositCents = Math.round(subtotalCents / 2);
    const balanceCents = subtotalCents - depositCents;
    return {
      subtotal: subtotalCents / 100,
      total: subtotalCents / 100,
      deposit: depositCents / 100,
      balance: balanceCents / 100
    };
  }

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    if (typeof module === 'object' && module.exports) module.exports = {calculate, CATALOG};
    return;
  }

  const $ = id => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const demoMode = params.get('demo') === 'invoice';
  const runtimeErrors = [];
  let storageWarning = '';
  let active = false;
  let currentNumber = '';
  let demoPayment = null;
  let previousReport = window.factoryReport;
  let scaleObserver = null;
  let initialized = false;
  let counterNeedsManual = false;
  let recoverableDraft = null;
  const damagedStorage = new Map();

  const money = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(Number(value) || 0);
  const today = () => {
    const date = new Date();
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 10);
  };
  const addDays = (dateText, days) => {
    const parts = String(dateText).split('-').map(Number);
    const date = parts.length === 3 && parts.every(Number.isFinite) ? new Date(parts[0], parts[1] - 1, parts[2]) : new Date();
    date.setDate(date.getDate() + days);
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 10);
  };
  const displayDate = value => {
    const [year, month, day] = String(value || '').split('-').map(Number);
    if (![year, month, day].every(Number.isFinite)) return '';
    return new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', year: 'numeric'}).format(new Date(year, month - 1, day));
  };
  const storageRead = (key, fallback, validator = () => true) => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return fallback;
      try {
        const parsed = JSON.parse(raw);
        if (!validator(parsed)) throw new Error('Saved value has the wrong shape.');
        return parsed;
      }
      catch (_) {
        damagedStorage.set(key, raw);
        storageWarning = 'Saved invoice data is unreadable. It was preserved, and the recovery control below can archive and replace it.';
        return fallback;
      }
    } catch (_) {
      storageWarning = 'This browser blocked saved invoice settings. The invoice still works, but keep this page open until you download it.';
      return fallback;
    }
  };
  const storageWrite = (key, value) => {
    if (damagedStorage.has(key)) {
      storageWarning = 'Unreadable saved data was preserved. Use the matching recovery control before saving over it.';
      return false;
    }
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      storageWarning = 'This browser could not save the invoice on this device. Your work is still on this page; download it before closing.';
      return false;
    }
  };
  const repairStorage = key => {
    if (!damagedStorage.has(key)) return true;
    try {
      const archiveKey = `${key}.recovery.${Date.now()}`;
      localStorage.setItem(archiveKey, damagedStorage.get(key));
      localStorage.removeItem(key);
      damagedStorage.delete(key);
      storageWarning = `The unreadable value was archived on this device as ${archiveKey}.`;
      return true;
    } catch (_) {
      storageWarning = 'This browser could not archive the unreadable value. Nothing was removed or overwritten. Keep this page open and enter the invoice number manually.';
      return false;
    }
  };
  const escapeText = value => String(value ?? '').replace(/[\u0000-\u001f\u007f]/g, ' ').trim();
  const short = (value, length) => escapeText(value).slice(0, length);
  function nextInvoiceNumber() {
    const date = today().replace(/-/g, '');
    if (counterNeedsManual && !damagedStorage.has(STORAGE.counter)) return `CSM-${date}-??`;
    const saved = storageRead(STORAGE.counter, {date, count: 0}, value => Boolean(
      value && typeof value === 'object' && /^\d{8}$/.test(value.date)
      && Number.isSafeInteger(Number(value.count)) && Number(value.count) >= 0
    ));
    if (damagedStorage.has(STORAGE.counter)) { counterNeedsManual = true; return `CSM-${date}-??`; }
    const previousCount = saved?.date === date && Number.isSafeInteger(Number(saved.count))
      ? Math.max(0, Number(saved.count))
      : 0;
    const count = previousCount + 1;
    if (!storageWrite(STORAGE.counter, {date, count})) { counterNeedsManual = true; return `CSM-${date}-??`; }
    counterNeedsManual = false;
    return `CSM-${date}-${String(count).padStart(2, '0')}`;
  }

  function paymentSettings() {
    if (demoPayment) return {...demoPayment};
    const saved = storageRead(STORAGE.settings, {}, value => Boolean(
      value && typeof value === 'object' && !Array.isArray(value)
      && ['cashApp', 'zelle', 'paypal'].every(key => value[key] === undefined || typeof value[key] === 'string')
    ));
    return {
      cashApp: short(saved?.cashApp, 40),
      zelle: short(saved?.zelle, 120),
      paypal: short(saved?.paypal, 180)
    };
  }

  function paymentEntries(settings = paymentSettings()) {
    const entries = [];
    const cashRaw = short(settings.cashApp, 40).replace(/^\$/, '');
    if (cashRaw && /^[A-Za-z0-9_]{1,30}$/.test(cashRaw)) entries.push({label: `Cash App $${cashRaw}`, href: `https://cash.app/$${encodeURIComponent(cashRaw)}`});
    const zelle = short(settings.zelle, 120);
    if (zelle) {
      if (EMAIL.test(zelle)) entries.push({label: `Zelle ${zelle}`, href: `mailto:${zelle}`});
      else {
        const phone = zelle.replace(/[^+\d]/g, '');
        if (/^\+?\d{7,15}$/.test(phone)) entries.push({label: `Zelle ${zelle}`, href: `tel:${phone}`});
      }
    }
    const paypal = short(settings.paypal, 180);
    if (paypal) {
      let parsed = null;
      try { parsed = new URL(paypal.startsWith('http') ? paypal : `https://paypal.me/${paypal.replace(/^@/, '')}`); } catch (_) { /* Invalid entries stay editable in Settings. */ }
      if (parsed && parsed.protocol === 'https:' && /(^|\.)paypal\.me$/i.test(parsed.hostname)) entries.push({label: `PayPal ${paypal}`, href: parsed.href});
    }
    return entries;
  }

  function invalidPaymentFields(settings) {
    const invalid = [];
    const cash = short(settings.cashApp, 40);
    if (cash && !/^[A-Za-z0-9_]{1,30}$/.test(cash.replace(/^\$/, ''))) invalid.push('Cash App cashtag');
    const zelle = short(settings.zelle, 120);
    if (zelle) {
      const phone = zelle.replace(/[^+\d]/g, '');
      if (!EMAIL.test(zelle) && !/^\+?\d{7,15}$/.test(phone)) invalid.push('Zelle email or phone');
    }
    const paypal = short(settings.paypal, 180);
    if (paypal) {
      let parsed = null;
      try { parsed = new URL(paypal.startsWith('http') ? paypal : `https://paypal.me/${paypal.replace(/^@/, '')}`); } catch (_) { /* Invalid below. */ }
      if (!parsed || parsed.protocol !== 'https:' || !/(^|\.)paypal\.me$/i.test(parsed.hostname) || !parsed.pathname.replace(/^\//, '')) invalid.push('PayPal.me link or name');
    }
    return invalid;
  }

  function injectUI() {
    if ($('invoice-studio')) return;
    const exportActions = document.querySelector('.export-actions');
    if (exportActions) {
      const button = document.createElement('button');
      button.type = 'button';
      button.id = 'make-invoice';
      button.className = 'invoice-launch';
      button.innerHTML = 'Make invoice <span>Deposit + balance</span>';
      exportActions.append(button);
    }
    const studio = document.createElement('section');
    studio.id = 'invoice-studio';
    studio.className = 'invoice-studio';
    studio.hidden = true;
    studio.setAttribute('aria-labelledby', 'invoice-studio-title');
    studio.innerHTML = `
      <header class="invoice-app-head">
        <div><p class="eyebrow">ORDER TO INVOICE</p><h2 id="invoice-studio-title">Get the deposit handled.</h2><p>Check the client, choose the extras, then send the invoice.</p></div>
        <div class="invoice-head-actions"><button type="button" class="quiet-button" id="invoice-settings-open">Payment settings</button><button type="button" class="quiet-button" id="invoice-close">Back to flyer</button></div>
      </header>
      <div class="invoice-workspace">
        <form id="invoice-form" class="invoice-editor" autocomplete="off">
          <div class="invoice-step"><span>01</span><div><strong>Who is paying?</strong><small>Loaded from the order when available.</small></div></div>
          <label for="invoice-client-name">Client name <span>required</span></label>
          <input id="invoice-client-name" maxlength="100" required>
          <label for="invoice-client-email">Client email <span>required</span></label>
          <input id="invoice-client-email" type="email" maxlength="160" required>
          <label for="invoice-organisation">Organisation <span>optional</span></label>
          <input id="invoice-organisation" maxlength="120">
          <label for="invoice-project">Project</label>
          <input id="invoice-project" maxlength="140">
          <label for="invoice-number">Invoice number <span>change only when recovering a damaged counter</span></label>
          <input id="invoice-number" maxlength="25" required pattern="CSM-[0-9]{8}-[0-9]{2,12}" aria-describedby="invoice-number-help">
          <p class="field-help" id="invoice-number-help">Format: CSM-YYYYMMDD-NN. A new number is assigned only when you start a new invoice.</p>
          <div class="invoice-date-grid"><div><label for="invoice-date">Invoice date</label><input id="invoice-date" type="date" required></div><div><label for="invoice-due">Deposit due</label><input id="invoice-due" type="date" required></div></div>
          <div class="invoice-step invoice-items-step"><span>02</span><div><strong>What did they order?</strong><small>The flyer includes its Instagram square.</small></div></div>
          <div id="invoice-items" class="invoice-items-editor"></div>
          <label for="invoice-notes">Note to client</label>
          <textarea id="invoice-notes" rows="3" maxlength="260"></textarea>
          <p class="invoice-storage-status" id="invoice-storage-status" role="status"></p>
          <div class="invoice-editor-actions"><button type="button" class="quiet-button" id="invoice-restore" hidden>Restore saved draft</button><button type="button" class="quiet-button" id="invoice-draft-repair" hidden>Archive damaged draft</button><button type="button" class="quiet-button" id="invoice-counter-repair" hidden>Archive and reset counter</button><button type="button" class="quiet-button" id="invoice-new">Start new invoice</button></div>
        </form>
        <div class="invoice-preview-column">
          <div class="invoice-preview-head"><div><p class="eyebrow">03 / CHECK IT</p><h3>Ready to send.</h3></div><span>8.5 × 11 IN</span></div>
          <div class="invoice-preview-well" id="invoice-preview-well"><div class="invoice-preview-scale" id="invoice-preview-scale">
            <article class="invoice-page" id="invoice-page" aria-label="Invoice preview">
              <header class="invoice-letterhead"><img id="invoice-logo" src="../logo/web/cultureshyft-horizontal-color-onlight.png" alt="CultureShyft Media"><div><h1>INVOICE</h1><p id="invoice-number-view"></p><p id="invoice-due-view"></p></div></header>
              <div class="invoice-rule"></div>
              <section class="invoice-parties"><div><p class="invoice-label">FROM</p><strong>Mark Andrew · CultureShyft Media</strong><p>mark@cultureshyftmedia.com · 248-505-0050<br>cultureshyftmedia.com</p></div><div><p class="invoice-label">BILL TO</p><strong id="invoice-client-view"></strong><p id="invoice-client-details-view"></p></div></section>
              <table class="invoice-table"><thead><tr><th>ITEM</th><th>DETAILS</th><th>QTY</th><th>PRICE</th><th>TOTAL</th></tr></thead><tbody id="invoice-lines-view"></tbody></table>
              <section class="invoice-totals"><div><span>Project total</span><strong id="invoice-subtotal-view"></strong></div><div><span>Deposit due (50%)</span><strong id="invoice-deposit-view"></strong></div><div class="invoice-balance"><span>Balance on delivery</span><strong id="invoice-balance-view"></strong></div></section>
              <section class="invoice-payment"><p class="invoice-label">HOW TO PAY</p><div id="invoice-payment-view"></div><p id="invoice-note-view"></p></section>
              <footer><span>CULTURESHYFT MEDIA</span><span>MEDIA MADE TO MOVE PEOPLE.</span><span>cultureshyftmedia.com</span></footer>
            </article>
          </div></div>
          <div class="invoice-export"><div><p class="eyebrow">04 / SEND IT</p><p id="invoice-next-step" role="status">Add the client and payment details.</p></div><div class="invoice-export-actions"><button type="button" id="invoice-print">Save invoice as PDF</button><button type="button" id="invoice-png">Download receipt image <span>1080 × 1350</span></button></div><p>PDF settings: Letter, no margins, background graphics on.</p></div>
        </div>
      </div>
      <div class="invoice-settings" id="invoice-settings" hidden role="dialog" aria-modal="true" aria-labelledby="invoice-settings-title">
        <div class="invoice-settings-card"><div class="invoice-settings-head"><div><p class="eyebrow">SAVED ON THIS DEVICE</p><h3 id="invoice-settings-title">How clients pay Mark</h3></div><button type="button" class="icon-button" id="invoice-settings-close" aria-label="Close payment settings">×</button></div>
          <p>Add one or more. These details appear on every invoice and receipt image.</p>
          <form id="invoice-settings-form"><label for="invoice-cashapp">Cash App cashtag</label><input id="invoice-cashapp" maxlength="40" placeholder="$cashtag"><label for="invoice-zelle">Zelle email or phone</label><input id="invoice-zelle" maxlength="120"><label for="invoice-paypal">PayPal.me link or name</label><input id="invoice-paypal" maxlength="180" placeholder="https://paypal.me/yourname"><button type="submit">Save payment details</button><button type="button" class="invoice-repair-button" id="invoice-settings-repair" hidden>Archive damaged settings and replace them</button><p id="invoice-settings-status" role="status"></p></form>
        </div>
      </div>`;
    document.body.append(studio);
    buildItemControls();
    bindEvents();
  }

  function buildItemControls() {
    const host = $('invoice-items');
    Object.values(CATALOG).forEach(item => {
      const row = document.createElement('label');
      row.className = 'invoice-item-control';
      row.htmlFor = `invoice-qty-${item.id}`;
      row.innerHTML = `<span><strong>${item.label}</strong><small>${item.detail}</small></span><span class="invoice-item-price">${money(item.unitPrice)}</span><input id="invoice-qty-${item.id}" data-invoice-quantity="${item.id}" type="number" inputmode="numeric" min="0" max="99" step="1" value="${item.id === 'flyer' ? 1 : 0}" aria-label="${item.label} quantity">`;
      host.append(row);
    });
  }

  function sourceValues(source) {
    const supplied = source || window.factoryBrief?.collect?.() || {};
    return supplied.values && typeof supplied.values === 'object' ? supplied.values : supplied;
  }

  function populateFromBrief(source, forceNew = false) {
    const values = sourceValues(source);
    if (!currentNumber || forceNew) currentNumber = nextInvoiceNumber();
    $('invoice-number').value = currentNumber;
    $('invoice-client-name').value = short(values.clientName || values.customerName || '', 100);
    $('invoice-client-email').value = short(values.clientEmail || values.customerEmail || '', 160);
    $('invoice-organisation').value = short(values.organisation || values.organization || '', 120);
    $('invoice-project').value = short(values.headline || values.project || 'Flyer design', 140);
    $('invoice-date').value = today();
    $('invoice-due').value = addDays(today(), 14);
    $('invoice-notes').value = '50% deposit starts the project. Balance is due when the final files are delivered.';
    const quantities = {
      flyer: 1,
      extraSize: clampQuantity(values.extraSizes),
      extraEdit: clampQuantity(values.extraEdits),
      printReady: values.printReady ? 1 : 0,
      rush: values.rush ? 1 : 0
    };
    setQuantities(quantities);
  }

  function populateDemo() {
    currentNumber = DEMO.invoiceNumber;
    $('invoice-number').value = currentNumber;
    demoPayment = {...DEMO.payment};
    $('invoice-client-name').value = DEMO.clientName;
    $('invoice-client-email').value = DEMO.clientEmail;
    $('invoice-organisation').value = DEMO.organisation;
    $('invoice-project').value = DEMO.project;
    $('invoice-date').value = DEMO.invoiceDate;
    $('invoice-due').value = DEMO.dueDate;
    $('invoice-notes').value = DEMO.notes;
    setQuantities(DEMO.quantities);
  }

  function restoreDraft() {
    const draft = recoverableDraft;
    if (!draft || draft.version !== 1 || !draft.invoiceNumber) {
      $('invoice-storage-status').textContent = 'There is no readable invoice draft to restore. Your current invoice is unchanged.';
      return collectState();
    }
    currentNumber = short(draft.invoiceNumber, 32);
    $('invoice-number').value = currentNumber;
    $('invoice-client-name').value = short(draft.clientName, 100);
    $('invoice-client-email').value = short(draft.clientEmail, 160);
    $('invoice-organisation').value = short(draft.organisation, 120);
    $('invoice-project').value = short(draft.project, 140);
    $('invoice-date').value = short(draft.invoiceDate, 10);
    $('invoice-due').value = short(draft.dueDate, 10);
    $('invoice-notes').value = short(draft.notes, 260);
    const quantities = {};
    (Array.isArray(draft.lines) ? draft.lines : []).forEach(line => {
      if (Object.hasOwn(CATALOG, line?.id)) quantities[line.id] = clampQuantity(line.quantity);
    });
    setQuantities(quantities);
    recoverableDraft = null;
    $('invoice-restore').hidden = true;
    render();
    $('invoice-storage-status').textContent = `Restored ${currentNumber}. Check every detail before sending.`;
    return collectState();
  }

  function setQuantities(quantities) {
    Object.keys(CATALOG).forEach(id => { $(`invoice-qty-${id}`).value = String(clampQuantity(quantities?.[id])); });
    if (!$('invoice-qty-flyer').value || Number($('invoice-qty-flyer').value) < 1) $('invoice-qty-flyer').value = '1';
  }

  function collectLines() {
    return Object.values(CATALOG).map(item => ({...item, quantity: clampQuantity($(`invoice-qty-${item.id}`)?.value)})).filter(line => line.quantity > 0);
  }

  function collectState() {
    currentNumber = short($('invoice-number')?.value || currentNumber, 32);
    const state = {
      version: 1,
      invoiceNumber: currentNumber,
      invoiceDate: $('invoice-date')?.value || '',
      dueDate: $('invoice-due')?.value || '',
      clientName: short($('invoice-client-name')?.value, 100),
      clientEmail: short($('invoice-client-email')?.value, 160),
      organisation: short($('invoice-organisation')?.value, 120),
      project: short($('invoice-project')?.value, 140),
      notes: short($('invoice-notes')?.value, 260),
      lines: collectLines(),
      payment: paymentSettings()
    };
    state.totals = calculate(state.lines);
    return state;
  }

  function render() {
    if (!$('invoice-page')) return;
    const state = collectState();
    $('invoice-number-view').textContent = `${state.invoiceNumber} · ${displayDate(state.invoiceDate)}`;
    $('invoice-due-view').textContent = `Deposit due: ${displayDate(state.dueDate)}`;
    $('invoice-client-view').textContent = state.clientName || 'Client name needed';
    $('invoice-client-details-view').textContent = [state.clientEmail, state.organisation, state.project].filter(Boolean).join('\n');
    const linesHost = $('invoice-lines-view');
    linesHost.replaceChildren();
    state.lines.forEach(line => {
      const row = document.createElement('tr');
      [line.label, line.detail, line.quantity, money(line.unitPrice), money(line.quantity * line.unitPrice)].forEach((value, index) => {
        const cell = document.createElement('td');
        cell.textContent = String(value);
        if (index === 0) cell.className = 'invoice-line-name';
        row.append(cell);
      });
      linesHost.append(row);
    });
    $('invoice-subtotal-view').textContent = money(state.totals.subtotal);
    $('invoice-deposit-view').textContent = money(state.totals.deposit);
    $('invoice-balance-view').textContent = money(state.totals.balance);
    const paymentHost = $('invoice-payment-view');
    paymentHost.replaceChildren();
    const entries = paymentEntries(state.payment);
    if (entries.length) entries.forEach((entry, index) => {
      if (index) paymentHost.append(document.createTextNode(' · '));
      const link = document.createElement('a');
      link.textContent = entry.label;
      link.href = entry.href;
      link.rel = 'noopener noreferrer';
      paymentHost.append(link);
    });
    else paymentHost.textContent = 'Add a payment method in Settings before sending.';
    $('invoice-note-view').textContent = state.notes;
    fitPreviewText($('invoice-client-view'), 14, 8);
    fitPreviewText($('invoice-client-details-view'), 14, 8);
    fitPreviewText($('invoice-payment-view'), 12, 7);
    fitPreviewText($('invoice-note-view'), 10, 8);
    const missing = validationMissing(state);
    $('invoice-next-step').textContent = missing.length
      ? `Next: ${missing[0]}. Your invoice stays saved on this device.`
      : `Ready: collect ${money(state.totals.deposit)} now; ${money(state.totals.balance)} is due on delivery.`;
    let draftSaved = true;
    if (active && initialized && !demoMode) draftSaved = storageWrite(STORAGE.draft, state);
    $('invoice-draft-repair').hidden = !damagedStorage.has(STORAGE.draft);
    $('invoice-counter-repair').hidden = !damagedStorage.has(STORAGE.counter) && !counterNeedsManual;
    $('invoice-counter-repair').textContent = damagedStorage.has(STORAGE.counter) ? 'Archive damaged counter' : 'Save verified number';
    $('invoice-storage-status').textContent = storageWarning || (draftSaved
      ? 'Invoice changes autosave on this device.'
      : 'This draft is only on this page. Download it before closing.');
    scalePreview();
    publishReport();
  }

  function fitPreviewText(element, maximum, minimum) {
    if (!element) return;
    element.style.removeProperty('font-size');
    for (let size = maximum; size >= minimum; size -= 0.5) {
      element.style.fontSize = `${size}px`;
      if (element.scrollWidth <= element.clientWidth + 1 && element.scrollHeight <= element.clientHeight + 1) return;
    }
  }

  function validationMissing(state = collectState()) {
    const missing = [];
    if (!INVOICE_NUMBER.test(state.invoiceNumber)) missing.push('enter a unique invoice number in the shown format');
    if (!state.clientName) missing.push('add the client name');
    if (!EMAIL.test(state.clientEmail)) missing.push('add a valid client email');
    if (!state.invoiceDate) missing.push('add the invoice date');
    if (!state.dueDate) missing.push('add the deposit due date');
    if (!state.lines.length || state.totals.subtotal <= 0) missing.push('add at least one priced item');
    const invalidPayments = invalidPaymentFields(state.payment);
    if (invalidPayments.length) missing.push(`fix ${invalidPayments.join(' and ')} in Payment settings`);
    if (!paymentEntries(state.payment).length) missing.push('add Cash App, Zelle, or PayPal in Payment settings');
    return missing;
  }

  function scalePreview() {
    if (!active) return;
    const well = $('invoice-preview-well');
    const scaleBox = $('invoice-preview-scale');
    if (!well || !scaleBox) return;
    const style = getComputedStyle(well);
    const available = well.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const scale = Math.min(1, Math.max(0.1, available / 816));
    scaleBox.style.width = `${816 * scale}px`;
    scaleBox.style.height = `${1056 * scale}px`;
    $('invoice-page').style.transform = `scale(${scale})`;
  }

  function open(source) {
    injectUI();
    if (!initialized) {
      if (demoMode) populateDemo();
      else populateFromBrief(source);
      initialized = true;
    }
    active = true;
    $('invoice-studio').hidden = false;
    document.body.classList.add('invoice-open');
    document.querySelector('.workspace')?.setAttribute('aria-hidden', 'true');
    $('invoice-restore').hidden = demoMode || !recoverableDraft?.invoiceNumber || recoverableDraft.invoiceNumber === currentNumber;
    $('invoice-draft-repair').hidden = !damagedStorage.has(STORAGE.draft);
    $('invoice-counter-repair').hidden = !damagedStorage.has(STORAGE.counter) && !counterNeedsManual;
    $('invoice-counter-repair').textContent = damagedStorage.has(STORAGE.counter) ? 'Archive damaged counter' : 'Save verified number';
    render();
    $('invoice-studio').scrollIntoView({block: 'start'});
    return collectState();
  }

  function close() {
    active = false;
    $('invoice-studio').hidden = true;
    document.body.classList.remove('invoice-open', 'invoice-printing');
    document.querySelector('.workspace')?.removeAttribute('aria-hidden');
    document.querySelector('#make-invoice')?.focus();
    return collectState();
  }

  function newInvoice() {
    currentNumber = '';
    demoPayment = null;
    populateFromBrief(null, true);
    initialized = true;
    render();
    $('invoice-client-name').focus();
    return collectState();
  }

  function openSettings() {
    const settings = paymentSettings();
    $('invoice-cashapp').value = settings.cashApp;
    $('invoice-zelle').value = settings.zelle;
    $('invoice-paypal').value = settings.paypal;
    $('invoice-settings-status').textContent = '';
    $('invoice-settings-repair').hidden = !damagedStorage.has(STORAGE.settings);
    $('invoice-settings').hidden = false;
    $('invoice-cashapp').focus();
  }

  function closeSettings() {
    $('invoice-settings').hidden = true;
    $('invoice-settings-open').focus();
  }

  function saveSettings(event) {
    event.preventDefault();
    const settings = {
      cashApp: short($('invoice-cashapp').value, 40),
      zelle: short($('invoice-zelle').value, 120),
      paypal: short($('invoice-paypal').value, 180)
    };
    const invalid = invalidPaymentFields(settings);
    if (invalid.length) {
      $('invoice-settings-status').textContent = `Fix ${invalid.join(' and ')}. No payment details were saved.`;
      return;
    }
    if (!paymentEntries(settings).length) {
      $('invoice-settings-status').textContent = 'Add a valid cashtag, Zelle email or phone, or PayPal.me link. Nothing was changed.';
      return;
    }
    demoPayment = null;
    const saved = storageWrite(STORAGE.settings, settings);
    $('invoice-settings-status').textContent = saved ? 'Saved. These payment details will appear on new invoices.' : storageWarning;
    $('invoice-settings-repair').hidden = !damagedStorage.has(STORAGE.settings);
    render();
    if (saved) setTimeout(closeSettings, 500);
  }

  function repairCounter() {
    if (damagedStorage.has(STORAGE.counter)) {
      if (!repairStorage(STORAGE.counter)) { render(); return; }
      currentNumber = `CSM-${today().replace(/-/g, '')}-??`;
      counterNeedsManual = true;
      $('invoice-number').value = currentNumber;
      $('invoice-counter-repair').textContent = 'Save verified number';
      render();
      $('invoice-storage-status').textContent = `${storageWarning} Check the last invoice you sent, replace ?? with the next unused number, then choose Save verified number.`;
      return;
    }
    const number = short($('invoice-number').value, 25);
    const match = number.match(/^CSM-(\d{8})-(\d{2,12})$/);
    if (!match || match[1] !== today().replace(/-/g, '')) {
      $('invoice-storage-status').textContent = 'Enter today’s invoice number in the shown format after checking the last invoice you sent. The counter was not changed.';
      return;
    }
    if (!storageWrite(STORAGE.counter, {date: match[1], count: Number(match[2])})) {
      $('invoice-storage-status').textContent = `${storageWarning} The counter was not changed.`;
      return;
    }
    counterNeedsManual = false;
    $('invoice-counter-repair').hidden = true;
    storageWarning = '';
    render();
    $('invoice-storage-status').textContent = `${number} is now the saved counter checkpoint. New invoices will continue from it.`;
  }

  function repairDraft() {
    if (!repairStorage(STORAGE.draft)) { render(); return; }
    recoverableDraft = null;
    $('invoice-draft-repair').hidden = true;
    render();
    $('invoice-storage-status').textContent = `${storageWarning} The current draft is now saved separately.`;
  }

  function repairSettings() {
    if (!repairStorage(STORAGE.settings)) {
      $('invoice-settings-status').textContent = storageWarning;
      return;
    }
    $('invoice-settings-repair').hidden = true;
    saveSettings(new Event('submit', {cancelable: true}));
  }

  function validateForExport() {
    render();
    const state = collectState();
    const missing = validationMissing(state);
    if (!missing.length) {
      const layout = report();
      if (!layout.overflow.length) return true;
      $('invoice-next-step').textContent = `The invoice is not ready: ${layout.overflow[0]}. Shorten that field or remove an unused payment method; no text was discarded.`;
      return false;
    }
    $('invoice-next-step').textContent = `The invoice is not ready: ${missing.join('; ')}. Your work is safe on this page.`;
    const invalidForm = !$('invoice-form').reportValidity();
    if (!invalidForm && (!paymentEntries(state.payment).length || invalidPaymentFields(state.payment).length)) openSettings();
    return false;
  }

  function printInvoice() {
    if (!validateForExport()) return;
    document.body.classList.add('invoice-printing');
    render();
    window.print();
  }

  function roundedRect(context, x, y, width, height, radius) {
    context.beginPath();
    context.roundRect(x, y, width, height, radius);
    context.fill();
  }

  function wrapCanvasText(context, text, maxWidth) {
    const sourceWords = String(text || '').split(/\s+/).filter(Boolean);
    const words = [];
    sourceWords.forEach(word => {
      if (context.measureText(word).width <= maxWidth) { words.push(word); return; }
      let part = '';
      Array.from(word).forEach(character => {
        if (part && context.measureText(part + character).width > maxWidth) { words.push(part); part = character; }
        else part += character;
      });
      if (part) words.push(part);
    });
    const lines = [];
    let line = '';
    words.forEach(word => {
      const candidate = line ? `${line} ${word}` : word;
      if (line && context.measureText(candidate).width > maxWidth) { lines.push(line); line = word; }
      else line = candidate;
    });
    if (line) lines.push(line);
    return lines;
  }

  async function renderReceipt() {
    if (document.fonts) { await document.fonts.load('800 48px Manrope'); await document.fonts.ready; }
    const state = collectState();
    const canvas = document.createElement('canvas');
    canvas.width = 1080;
    canvas.height = 1350;
    const context = canvas.getContext('2d', {alpha: false});
    if (!context) throw new Error('This browser could not start the receipt image.');
    context.fillStyle = '#FFFFFF'; context.fillRect(0, 0, 1080, 1350);
    const logo = new Image(); logo.src = '../logo/web/cultureshyft-horizontal-color-onlight.png'; await logo.decode();
    context.drawImage(logo, 64, 64, 330, 330 * logo.naturalHeight / logo.naturalWidth);
    context.fillStyle = '#14151A'; context.textAlign = 'right'; context.textBaseline = 'top'; context.font = '800 56px Manrope, sans-serif'; context.fillText('INVOICE', 1016, 62);
    context.fillStyle = '#6A6E78'; context.font = '600 23px Manrope, sans-serif'; context.fillText(state.invoiceNumber, 1016, 132); context.fillText(`Deposit due ${displayDate(state.dueDate)}`, 1016, 169);
    context.fillStyle = '#FF5A1F'; context.fillRect(64, 224, 952, 8);
    context.textAlign = 'left'; context.fillStyle = '#6A6E78'; context.font = '800 18px Manrope, sans-serif'; context.fillText('BILL TO', 64, 278);
    context.fillStyle = '#14151A'; context.font = '800 34px Manrope, sans-serif'; context.fillText(state.clientName, 64, 314, 952);
    context.fillStyle = '#6A6E78'; context.font = '500 22px Manrope, sans-serif'; context.fillText([state.clientEmail, state.organisation].filter(Boolean).join(' · '), 64, 361, 952);
    let y = 436;
    context.fillStyle = '#14151A'; roundedRect(context, 64, y, 952, 56, 8);
    context.fillStyle = '#FFFFFF'; context.font = '800 18px Manrope, sans-serif'; context.fillText('ITEM', 84, y + 17); context.textAlign = 'right'; context.fillText('TOTAL', 996, y + 17); context.textAlign = 'left';
    y += 72;
    state.lines.forEach(line => {
      context.fillStyle = '#14151A'; context.font = '800 23px Manrope, sans-serif'; context.fillText(line.label, 84, y);
      context.fillStyle = '#6A6E78'; context.font = '500 18px Manrope, sans-serif'; const detail = wrapCanvasText(context, `${line.quantity} × ${money(line.unitPrice)} · ${line.detail}`, 690)[0] || '';
      context.fillText(detail, 84, y + 32); context.textAlign = 'right'; context.fillStyle = '#14151A'; context.font = '700 23px Manrope, sans-serif'; context.fillText(money(line.quantity * line.unitPrice), 996, y); context.textAlign = 'left';
      context.fillStyle = '#D8D7D2'; context.fillRect(64, y + 58, 952, 2); y += 72;
    });
    y = Math.max(y + 26, 790);
    const totalRow = (label, value, bold = false, orange = false) => {
      context.fillStyle = orange ? '#FF5A1F' : '#14151A'; context.font = `${bold ? 800 : 600} ${bold ? 31 : 24}px Manrope, sans-serif`; context.fillText(label, 530, y); context.textAlign = 'right'; context.fillText(money(value), 996, y); context.textAlign = 'left'; y += bold ? 58 : 46;
    };
    totalRow('Project total', state.totals.subtotal); totalRow('Deposit due (50%)', state.totals.deposit, true, true); totalRow('Balance on delivery', state.totals.balance);
    y += 24; context.fillStyle = '#F4F3EF'; roundedRect(context, 64, y, 952, 170, 14);
    context.fillStyle = '#14151A'; context.font = '800 18px Manrope, sans-serif'; context.fillText('HOW TO PAY', 88, y + 24);
    const paymentText = paymentEntries(state.payment).map(entry => entry.label).join(' · ');
    let paymentSize = 23;
    let paymentLines = [];
    for (; paymentSize >= 12; paymentSize -= 1) {
      context.font = `700 ${paymentSize}px Manrope, sans-serif`;
      paymentLines = wrapCanvasText(context, paymentText, 900);
      if (paymentLines.length <= 4) break;
    }
    if (paymentLines.length > 4) throw new Error('Payment details are too long for the receipt image. Shorten them in Settings; no text was discarded.');
    const paymentLineHeight = paymentSize * 1.3;
    paymentLines.forEach((line, index) => context.fillText(line, 88, y + 58 + index * paymentLineHeight));
    context.fillStyle = '#6A6E78'; context.font = '600 18px Manrope, sans-serif'; context.fillText('mark@cultureshyftmedia.com · cultureshyftmedia.com', 64, 1284);
    return canvas.toDataURL('image/png');
  }

  async function downloadReceipt() {
    if (!validateForExport()) return;
    const button = $('invoice-png');
    button.disabled = true;
    $('invoice-next-step').textContent = 'Making the receipt image…';
    try {
      const dataUrl = await renderReceipt();
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `${currentNumber || 'CultureShyft-invoice'}-receipt.png`;
      document.body.append(link); link.click(); link.remove();
      $('invoice-next-step').textContent = 'Receipt image downloaded. Open it and check every detail before texting it.';
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      runtimeErrors.push(message);
      $('invoice-next-step').textContent = `The receipt image could not download. Your invoice is safe. Try again, or use the PDF. ${message}`;
      publishReport();
    } finally { button.disabled = false; }
  }

  function elementVisible(element) {
    return Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  }

  function report() {
    const state = collectState();
    const overflow = [];
    const missing = validationMissing(state).map(item => item.replace(/^add /, ''));
    const page = $('invoice-page');
    if (page) {
      const pageBox = page.getBoundingClientRect();
      const scale = pageBox.width / 816;
      const tolerance = Math.max(0.8, scale);
      const within = (child, parent) => child.left >= parent.left - tolerance && child.top >= parent.top - tolerance && child.right <= parent.right + tolerance && child.bottom <= parent.bottom + tolerance;
      page.querySelectorAll('p,strong,span,td,th,a,h1').forEach(element => {
        if (elementVisible(element) && (element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1)) {
          overflow.push(`${element.id || element.className || element.tagName.toLowerCase()}: content exceeds box`);
        }
      });
      const panels = [...page.children].filter(elementVisible);
      panels.forEach(panel => {
        if (!within(panel.getBoundingClientRect(), pageBox)) overflow.push(`${panel.className || panel.tagName.toLowerCase()}: outside invoice page`);
      });
      for (let first = 0; first < panels.length; first += 1) {
        for (let second = first + 1; second < panels.length; second += 1) {
          const a = panels[first].getBoundingClientRect();
          const b = panels[second].getBoundingClientRect();
          const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (overlapX > tolerance && overlapY > tolerance) overflow.push(`${panels[first].className || panels[first].tagName.toLowerCase()}: overlaps ${panels[second].className || panels[second].tagName.toLowerCase()}`);
        }
      }
    }
    const logo = $('invoice-logo');
    const logoPresent = Boolean(logo?.complete && logo.naturalWidth > 0);
    const contactPresent = Boolean(page?.textContent.includes('mark@cultureshyftmedia.com'));
    if (!logoPresent) missing.push('logo');
    if (!contactPresent) missing.push('contact');
    if (!document.fonts.check('800 32px Manrope')) missing.push('Manrope font');
    const allRuntimeErrors = [...new Set([...(window.factoryRuntimeErrors || []), ...runtimeErrors])];
    if (allRuntimeErrors.length) missing.push(...allRuntimeErrors);
    const documentScrollWidth = document.documentElement.scrollWidth;
    const documentClientWidth = document.documentElement.clientWidth;
    if (documentScrollWidth > documentClientWidth + 1) overflow.push('page: horizontal scroll');
    return {
      overflow,
      missing,
      ready: active && logoPresent && !allRuntimeErrors.length,
      diagnostics: {
        layout: 'invoice',
        invoiceNumber: state.invoiceNumber,
        logoPresent,
        contactPresent,
        totals: state.totals,
        lineCount: state.lines.length,
        paymentLinks: paymentEntries(state.payment).map(entry => entry.href),
        pngSize: {width: 1080, height: 1350},
        runtimeErrors: allRuntimeErrors,
        storageWarning,
        documentScrollWidth,
        documentClientWidth,
        viewportWidth: innerWidth,
        invoiceWidth: page?.offsetWidth || 0,
        invoiceHeight: page?.offsetHeight || 0
      }
    };
  }

  function publishReport() {
    if (params.get('check') !== '1' || !active) return;
    let output = $('factory-check-report');
    if (!output) {
      output = document.createElement('script'); output.id = 'factory-check-report'; output.type = 'application/json'; document.body.append(output);
    }
    output.textContent = JSON.stringify(report());
  }

  function bindEvents() {
    $('make-invoice')?.addEventListener('click', () => open());
    $('invoice-close').addEventListener('click', close);
    $('invoice-new').addEventListener('click', newInvoice);
    $('invoice-restore').addEventListener('click', restoreDraft);
    $('invoice-draft-repair').addEventListener('click', repairDraft);
    $('invoice-counter-repair').addEventListener('click', repairCounter);
    $('invoice-settings-open').addEventListener('click', openSettings);
    $('invoice-settings-close').addEventListener('click', closeSettings);
    $('invoice-settings').addEventListener('click', event => { if (event.target === $('invoice-settings')) closeSettings(); });
    $('invoice-settings-form').addEventListener('submit', saveSettings);
    $('invoice-settings-repair').addEventListener('click', repairSettings);
    $('invoice-form').addEventListener('submit', event => event.preventDefault());
    $('invoice-form').addEventListener('input', render);
    $('invoice-print').addEventListener('click', printInvoice);
    $('invoice-png').addEventListener('click', downloadReceipt);
    window.addEventListener('afterprint', () => document.body.classList.remove('invoice-printing'));
    window.addEventListener('resize', scalePreview);
    $('invoice-logo').addEventListener('load', publishReport);
    $('invoice-logo').addEventListener('error', () => { runtimeErrors.push('The invoice logo could not load. Reload before exporting.'); render(); });
    scaleObserver = new ResizeObserver(scalePreview); scaleObserver.observe($('invoice-preview-well'));
  }

  recoverableDraft = demoMode ? null : storageRead(STORAGE.draft, null, value => Boolean(
    value && typeof value === 'object' && value.version === 1
    && typeof value.invoiceNumber === 'string' && Array.isArray(value.lines)
  ));
  injectUI();
  window.factoryInvoice = Object.freeze({
    catalog: CATALOG,
    calculate,
    calculateInvoice: calculate,
    open,
    close,
    newInvoice,
    getState: collectState,
    report,
    renderReceipt,
    paymentEntries
  });
  window.factoryReport = () => active ? report() : (typeof previousReport === 'function' ? previousReport() : {overflow: [], missing: ['factory report unavailable'], ready: false, diagnostics: {}});

  if (demoMode) open(DEMO); // Open before load so headless print captures the invoice, not the flyer.
  const priorReady = Promise.resolve(window.factoryReady);
  window.factoryReady = (async () => {
    try { await priorReady; } catch (error) { runtimeErrors.push(error instanceof Error ? error.message : String(error)); }
    if (demoMode) open(DEMO);
    await document.fonts.ready;
    try { await $('invoice-logo').decode(); } catch (_) { /* report() provides recovery detail. */ }
    render();
    return window.factoryReport();
  })();
})();
