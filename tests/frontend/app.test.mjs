// Frontend tests: load the real frontend/index.html + app.js into jsdom with a
// mocked fetch, and verify the contract behavior described in openapi.yaml:
// create board on load, add/delete elements with the right payloads, reload
// after mutations, and error handling (banner for network errors, console log
// for 404).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const html = readFileSync(new URL('../../frontend/index.html', import.meta.url), 'utf8');
const appJs = readFileSync(new URL('../../frontend/app.js', import.meta.url), 'utf8');

const jsonResponse = (status, data) => ({
  status,
  ok: status >= 200 && status < 300,
  statusText: String(status),
  json: async () => data,
});

// In-memory fake of the Interview Canvas API (mirrors openapi.yaml).
function createMockApi() {
  const boards = new Map();
  const calls = [];
  let boardSeq = 0;
  let elSeq = 0;

  async function fetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const path = new URL(url, 'http://localhost').pathname;
    calls.push({ method, path, body: options.body });

    if (method === 'POST' && path === '/boards') {
      const board = {
        id: `board-${++boardSeq}`,
        name: null,
        created_at: '2026-08-31T19:00:00Z',
        elements: [],
      };
      boards.set(board.id, board);
      return jsonResponse(201, board);
    }

    let m = path.match(/^\/boards\/([^/]+)$/);
    if (method === 'GET' && m) {
      const board = boards.get(m[1]);
      return board ? jsonResponse(200, board) : jsonResponse(404, { detail: 'Board not found' });
    }

    m = path.match(/^\/boards\/([^/]+)\/elements$/);
    if (method === 'POST' && m) {
      const board = boards.get(m[1]);
      if (!board) return jsonResponse(404, { detail: 'Board not found' });
      const body = JSON.parse(options.body || '{}');
      const el = { id: `el-${++elSeq}`, board_id: board.id, created_at: '2026-08-31T19:00:01Z', ...body };
      board.elements.push(el);
      return jsonResponse(201, el);
    }

    m = path.match(/^\/elements\/([^/]+)$/);
    if (method === 'DELETE' && m) {
      for (const board of boards.values()) {
        const idx = board.elements.findIndex((e) => e.id === m[1]);
        if (idx !== -1) {
          board.elements.splice(idx, 1);
          return { status: 204, ok: true, statusText: 'No Content', json: async () => null };
        }
      }
      return jsonResponse(404, { detail: 'Element not found' });
    }

    return jsonResponse(404, { detail: 'Not found' });
  }

  return { boards, calls, fetch };
}

function setupApp(fetchImpl) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'http://localhost/' });
  dom.window.fetch = fetchImpl;
  dom.window.eval(appJs); // run the IIFE inside the jsdom window
  return dom;
}

async function waitFor(fn, timeout = 2000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (fn()) return;
    await new Promise((r) => setTimeout(r, 10));
  }
  throw new Error(`waitFor: condition not met within ${timeout}ms`);
}

const click = (win, el) => el.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));

function pointerDownUp(win, el) {
  el.dispatchEvent(new win.MouseEvent('pointerdown', { bubbles: true, clientX: 0, clientY: 0 }));
  win.dispatchEvent(new win.MouseEvent('pointerup', { bubbles: true, clientX: 0, clientY: 0 }));
}

async function loadPage(api) {
  const dom = setupApp(api.fetch);
  const doc = dom.window.document;
  await waitFor(() => doc.getElementById('board').dataset.boardId);
  return { dom, doc };
}

// ---------- board creation on load ----------

test('on load: creates a board (POST /boards, no body) and renders the empty board', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);

  const bid = doc.getElementById('board').dataset.boardId;
  assert.match(bid, /^board-\d+$/);

  const createCall = api.calls.find((c) => c.method === 'POST' && c.path === '/boards');
  assert.ok(createCall, 'POST /boards should be called on load');
  assert.equal(createCall.body, undefined, 'board creation should have no body');
  assert.ok(
    api.calls.some((c) => c.method === 'GET' && c.path === `/boards/${bid}`),
    'GET /boards/{id} should be called after creation'
  );

  assert.equal(doc.querySelectorAll('.el').length, 0);
  assert.notEqual(doc.getElementById('empty-hint').style.display, 'none', 'empty hint should be visible');
});

// ---------- adding elements ----------

test('add sticky note: POSTs the contract payload and renders it', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const addCall = api.calls.find((c) => c.method === 'POST' && c.path.includes('/elements'));
  assert.ok(addCall, 'POST /boards/{id}/elements should be called');
  const payload = JSON.parse(addCall.body);
  assert.equal(payload.type, 'sticky_note');
  assert.equal(payload.width, 160);
  assert.equal(payload.height, 160);
  assert.ok(Number.isFinite(payload.x) && Number.isFinite(payload.y), 'position must be numbers');
  assert.equal(payload.text, '');

  const node = doc.querySelector('.el.sticky');
  assert.ok(node, 'sticky element should be rendered');
  assert.equal(node.style.width, '160px');
  assert.equal(node.style.height, '160px');
});

test('add rectangle and circle: POSTs correct payloads (circle width == height)', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);

  click(doc.defaultView, doc.getElementById('btn-rect'));
  click(doc.defaultView, doc.getElementById('btn-circle'));
  await waitFor(() => doc.querySelectorAll('.el').length === 2);

  const posts = api.calls.filter((c) => c.method === 'POST' && c.path.includes('/elements'));
  assert.equal(posts.length, 2);

  const rect = JSON.parse(posts[0].body);
  assert.equal(rect.type, 'rectangle');
  assert.equal(rect.width, 180);
  assert.equal(rect.height, 110);
  assert.equal(rect.text, null);

  const circle = JSON.parse(posts[1].body);
  assert.equal(circle.type, 'circle');
  assert.equal(circle.width, 130);
  assert.equal(circle.height, 130);
  assert.equal(circle.width, circle.height, 'circle must be a square (width == height)');

  assert.ok(doc.querySelector('.el.rect'));
  assert.ok(doc.querySelector('.el.circle'));
});

test('after adding, the board is reloaded from the server (server is source of truth)', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);
  const bid = doc.getElementById('board').dataset.boardId;

  const getsBefore = api.calls.filter((c) => c.method === 'GET' && c.path === `/boards/${bid}`).length;
  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const getsAfter = api.calls.filter((c) => c.method === 'GET' && c.path === `/boards/${bid}`).length;
  assert.ok(getsAfter > getsBefore, 'board should be reloaded after adding');
  assert.equal(api.boards.get(bid).elements.length, 1, 'server state should match');
});

// ---------- deleting elements ----------

test('delete: sends DELETE /elements/{id} and reloads the board', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);
  const bid = doc.getElementById('board').dataset.boardId;

  click(doc.defaultView, doc.getElementById('btn-circle'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const node = doc.querySelector('.el.circle');
  const id = node.dataset.id;
  pointerDownUp(doc.defaultView, node); // select shows the delete button
  click(doc.defaultView, node.querySelector('.delete-btn'));
  await waitFor(() => doc.querySelectorAll('.el').length === 0);

  assert.ok(api.calls.some((c) => c.method === 'DELETE' && c.path === `/elements/${id}`), 'DELETE should be sent');
  assert.equal(api.boards.get(bid).elements.length, 0, 'server state should be empty');
  assert.notEqual(doc.getElementById('empty-hint').style.display, 'none', 'empty hint should be back');
});

// ---------- error handling ----------

test('server unavailable: shows the error banner and no board is created', async () => {
  const dom = setupApp(async () => {
    throw new TypeError('Failed to fetch');
  });
  const doc = dom.window.document;

  await waitFor(() => doc.getElementById('error-banner').classList.contains('visible'));
  assert.match(doc.getElementById('error-banner').textContent, /сервер недоступен/);
  assert.ok(!doc.getElementById('board').dataset.boardId, 'no board id without a server');
});

test('404 on delete: logged to console, no error banner', async () => {
  const api = createMockApi();
  const { dom, doc } = await loadPage(api);

  const logs = [];
  dom.window.console.log = (...args) => logs.push(args.map(String).join(' '));

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const node = doc.querySelector('.el.sticky');
  const id = node.dataset.id;
  // another client deleted the element — the UI state is stale
  const bid = doc.getElementById('board').dataset.boardId;
  api.boards.get(bid).elements = [];

  pointerDownUp(doc.defaultView, node);
  click(doc.defaultView, node.querySelector('.delete-btn'));
  await waitFor(() => logs.some((l) => l.includes('404')));

  assert.ok(logs.some((l) => l.includes('Element not found')), '404 detail should be logged');
  assert.equal(doc.getElementById('error-banner').classList.contains('visible'), false, 'no banner for 404');
  assert.ok(api.calls.some((c) => c.method === 'DELETE' && c.path === `/elements/${id}`));
});
