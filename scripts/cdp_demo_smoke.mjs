#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';


const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const demoUrl = pathToFileURL(resolve(process.argv[2] ?? 'demo/index.html')).href;
const profile = await mkdtemp(`${tmpdir()}/test-studio-chrome-`);
const chrome = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });

try {
  const endpoint = await new Promise((resolveEndpoint, reject) => {
    const timeout = setTimeout(() => reject(new Error('Chrome DevTools endpoint timed out')), 10_000);
    chrome.stderr.on('data', chunk => {
      const match = String(chunk).match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timeout); resolveEndpoint(match[1]); }
    });
    chrome.once('exit', code => reject(new Error(`Chrome exited early: ${code}`)));
  });
  const socket = new WebSocket(endpoint);
  await new Promise((resolveOpen, reject) => {
    socket.addEventListener('open', resolveOpen, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve: done, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message)); else done(message.result);
    }
  });
  const send = (method, params = {}, sessionId) => new Promise((done, reject) => {
    const id = nextId++;
    pending.set(id, { resolve: done, reject });
    socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const target = await send('Target.createTarget', { url: demoUrl });
  const attached = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
  await send('Runtime.enable', {}, attached.sessionId);
  await new Promise(resolveWait => setTimeout(resolveWait, 300));
  const expression = `(() => {
    const title = document.querySelector('[data-testid="title"]');
    title.value = 'CDP public demo';
    title.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('#note-form').requestSubmit();
    return { value: title.value, saved: document.querySelector('[data-testid="saved-status"]').textContent,
             visible: !document.querySelector('[data-testid="saved-status"]').hidden };
  })()`;
  const evaluated = await send('Runtime.evaluate', { expression, returnByValue: true }, attached.sessionId);
  assert.deepEqual(evaluated.result.value, { value: 'CDP public demo', saved: 'Saved', visible: true });
  process.stdout.write('OK: real Chrome CDP demo passed\n');
  socket.close();
} finally {
  chrome.kill('SIGTERM');
  await rm(profile, { recursive: true, force: true });
}

