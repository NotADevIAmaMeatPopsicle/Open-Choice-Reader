# Store listing assets

Upload images for the Chrome Web Store listing. The copy that goes with them is in
`../STORE-LISTING.md`.

- `screenshot-1-popup.png` through `screenshot-3-library.png`, 1280x800, which is one
  of the two sizes the store accepts. Screenshot 1 is the extension popup rendered from
  `popup.html` and `popup.css` at 3x and scaled down, so it is the real interface rather
  than a mockup. Screenshots 2 and 3 frame the existing product captures from
  `docs/assets/screenshots/`.
- `store-icon-128.png` and `store-icon-512.png`, the listing icon. The 128 is the same
  image as `icons/icon128.png` in the extension itself.

These are excluded from the upload package by `scripts/package-extension.mjs`, since
the store takes them through the listing form and not inside the zip.
