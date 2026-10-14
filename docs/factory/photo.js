(() => {
  'use strict';
  const LIMIT = 12 * 1024 * 1024;
  const TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
  let state = {dataUrl: '', focusX: 0.5, focusY: 0.5, zoom: 1};

  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const emit = () => window.dispatchEvent(new CustomEvent('factory:photochange', {detail: getState()}));
  const getState = () => ({...state});

  function setState(next = {}, notify = true) {
    const focusX = Number(next.focusX);
    const focusY = Number(next.focusY);
    const zoom = Number(next.zoom);
    state = {
      dataUrl: typeof next.dataUrl === 'string' && /^data:image\/(jpeg|png|webp);base64,/i.test(next.dataUrl) ? next.dataUrl : '',
      focusX: clamp(Number.isFinite(focusX) ? focusX : 0.5, 0, 1),
      focusY: clamp(Number.isFinite(focusY) ? focusY : 0.5, 0, 1),
      zoom: clamp(Number.isFinite(zoom) ? zoom : 1, 1, 2.5)
    };
    if (notify) emit();
    return getState();
  }

  function loadImage(source) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('This photo could not open.'));
      image.src = source;
    });
  }

  async function fromFile(file) {
    if (!file || !TYPES.has(file.type) || file.size > LIMIT) throw new Error('Choose a JPG, PNG or WebP up to 12 MB.');
    const source = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('This photo could not be read.'));
      reader.readAsDataURL(file);
    });
    const image = await loadImage(source);
    if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 30000000) throw new Error('Choose a photo under 30 megapixels.');
    const scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('This browser could not prepare the photo.');
    context.fillStyle = '#fff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.78);
    return {dataUrl, focusX: 0.5, focusY: 0.5, zoom: 1};
  }

  function moveBy(deltaX, deltaY, width, height) {
    if (!state.dataUrl || !width || !height) return;
    setState({...state, focusX: state.focusX - deltaX / (width * state.zoom), focusY: state.focusY - deltaY / (height * state.zoom)});
  }

  window.factoryPhoto = Object.freeze({getState, setState, fromFile, moveBy, clear: () => setState({})});
})();
