#!/usr/bin/env node
// Builds the Chrome Web Store upload package from browser-extension/.
//
// The store wants a zip whose manifest.json sits at the ROOT, not inside a
// folder, which is the most common reason a first upload is rejected. It also
// wants only what the extension actually runs: tests and the developer README
// are stripped so a reviewer reads the extension rather than the repository.
//
// Usage: node scripts/package-extension.mjs [outputDir]
// Default output: dist/extension/

import { createWriteStream } from 'node:fs';
import { mkdir, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDeflateRaw } from 'node:zlib';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'browser-extension');
const OUT_DIR = resolve(process.argv[2] ?? join(ROOT, 'dist', 'extension'));

// Everything not listed here stays out of the upload.
const EXCLUDE_DIRS = new Set(['tests', 'store-assets', 'node_modules', '.git']);
const EXCLUDE_FILES = new Set(['README.md', 'STORE-LISTING.md', 'PRIVACY.md', '.DS_Store']);

async function collect(dir, base = SRC) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (EXCLUDE_DIRS.has(entry.name)) continue;
      out.push(...(await collect(full, base)));
    } else {
      if (EXCLUDE_FILES.has(entry.name)) continue;
      out.push({ full, name: relative(base, full).split(sep).join('/') });
    }
  }
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

function crc32(buf) {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
  }
  return ~c >>> 0;
}

const deflate = (buf) => new Promise((res, rej) => {
  const chunks = [];
  const z = createDeflateRaw({ level: 9 });
  z.on('data', (d) => chunks.push(d));
  z.on('end', () => res(Buffer.concat(chunks)));
  z.on('error', rej);
  z.end(buf);
});

async function writeZip(files, target) {
  const out = createWriteStream(target);
  const central = [];
  let offset = 0;
  const write = (b) => { out.write(b); offset += b.length; };

  for (const f of files) {
    const raw = await readFile(f.full);
    const comp = await deflate(raw);
    const name = Buffer.from(f.name, 'utf8');
    const crc = crc32(raw);

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6);   // UTF-8 names
    local.writeUInt16LE(8, 8);        // deflate
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(comp.length, 18);
    local.writeUInt32LE(raw.length, 22);
    local.writeUInt16LE(name.length, 26);

    const start = offset;
    write(local); write(name); write(comp);

    const cen = Buffer.alloc(46);
    cen.writeUInt32LE(0x02014b50, 0);
    cen.writeUInt16LE(20, 4);
    cen.writeUInt16LE(20, 6);
    cen.writeUInt16LE(0x0800, 8);
    cen.writeUInt16LE(8, 10);
    cen.writeUInt32LE(crc, 16);
    cen.writeUInt32LE(comp.length, 20);
    cen.writeUInt32LE(raw.length, 24);
    cen.writeUInt16LE(name.length, 28);
    cen.writeUInt32LE(start, 42);
    central.push(Buffer.concat([cen, name]));
  }

  const cenStart = offset;
  for (const c of central) write(c);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(central.length, 8);
  end.writeUInt16LE(central.length, 10);
  end.writeUInt32LE(offset - cenStart, 12);
  end.writeUInt32LE(cenStart, 16);
  write(end);

  await new Promise((res, rej) => { out.on('close', res); out.on('error', rej); out.end(); });
}

const manifest = JSON.parse(await readFile(join(SRC, 'manifest.json'), 'utf8'));
for (const size of ['16', '32', '48', '128']) {
  const icon = manifest.icons?.[size];
  if (!icon) throw new Error(`manifest.icons is missing the ${size}px entry, which the store requires`);
  await stat(join(SRC, icon));
}

const files = await collect(SRC);
if (!files.some((f) => f.name === 'manifest.json')) {
  throw new Error('manifest.json is not at the root of the package');
}

await mkdir(OUT_DIR, { recursive: true });
const target = join(OUT_DIR, `open-choice-reader-extension-${manifest.version}-chrome.zip`);
await writeZip(files, target);

const size = (await stat(target)).size;
console.log(`${target}\n${files.length} files, ${size} bytes`);
for (const f of files) console.log(`  ${f.name}`);
