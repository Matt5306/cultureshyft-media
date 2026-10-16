"""Independently decode the actual QR drawing rectangles without a browser.

Requires installed Node, Pillow, NumPy and OpenCV; never downloads anything.
Run this file individually: python tools/test_factory_qr.py
"""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = """
const fs = require('fs'), vm = require('vm');
const window = {qrcode: require('./docs/factory/vendor/qrcode.min.js')};
vm.runInNewContext(fs.readFileSync('./docs/factory/qr.js', 'utf8'), {window, URL});
const drawings = [];
for (const url of ['https://cultureshyftmedia.com/', 'https://example.com/' + 'x'.repeat(120)]) {
  const rects = [];
  const ctx = {save() {}, restore() {}, fillRect(...args) {rects.push([this.fillStyle, ...args]);}};
  window.factoryQR.draw(ctx, url, 0, 0, 140);
  drawings.push({url, rects});
}
const missingWindow = {};
vm.runInNewContext(fs.readFileSync('./docs/factory/qr.js', 'utf8'), {window: missingWindow, URL});
const missingResult = missingWindow.factoryQR.draw({save() {}, restore() {}, fillRect() {}}, 'https://example.com/', 0, 0, 140);
console.log(JSON.stringify({drawings, missing: {result: missingResult, error: missingWindow.factoryQR.getLastError()}}));
"""


def main():
    result = subprocess.run(
        ['node', '-e', SCRIPT], cwd=ROOT, capture_output=True, text=True,
        check=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    output = json.loads(result.stdout)
    for item in output['drawings']:
        image = Image.new('RGB', (140, 140), 'white')
        draw = ImageDraw.Draw(image)
        for color, x, y, width, height in item['rects']:
            assert all(value == round(value) for value in (x, y, width, height)), 'QR modules must use whole pixels'
            draw.rectangle((x, y, x + width - 1, y + height - 1), fill=color)
        pixels = cv2.copyMakeBorder(np.array(image), 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)
        assert decoded == item['url'], f"QR did not decode correctly at URL length {len(item['url'])}"
        print(f"PASS QR drawing independently decoded at URL length {len(item['url'])}")
    assert output['missing']['result'] is None, 'Missing QR vendor must skip drawing without throwing'
    assert output['missing']['error'] == 'The QR maker did not load.'
    print('PASS missing QR vendor reports qrError and does not abort drawing')


if __name__ == '__main__':
    main()
