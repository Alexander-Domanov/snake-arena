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

    // PATCH /elements/{id}: partial update (mirrors the backend semantics)
    if (method === 'PATCH' && m) {
      for (const board of boards.values()) {
        const idx = board.elements.findIndex((e) => e.id === m[1]);
        if (idx !== -1) {
          const body = JSON.parse(options.body || '{}');
          board.elements[idx] = { ...board.elements[idx], ...body };
          return jsonResponse(200, board.elements[idx]);
        }
      }
      return jsonResponse(404, { detail: 'Element not found' });
    }

    return jsonResponse(404, { detail: 'Not found' });
  }

  return { boards, calls, fetch };
}

function setupApp(fetchImpl, url = 'http://localhost/') {
  const dom = new JSDOM(html, { runScripts: 'outside-only', url });
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

// pointerdown on the element, then a real move on the window, then pointerup
function dragBy(win, el, dx, dy) {
  el.dispatchEvent(new win.MouseEvent('pointerdown', { bubbles: true, clientX: 0, clientY: 0 }));
  win.dispatchEvent(new win.MouseEvent('pointermove', { bubbles: true, clientX: dx, clientY: dy }));
  win.dispatchEvent(new win.MouseEvent('pointerup', { bubbles: true, clientX: dx, clientY: dy }));
}

// double-click to enter edit mode, set text, then blur (fires stopEditing)
function editText(win, body, text) {
  body.dispatchEvent(new win.MouseEvent('dblclick', { bubbles: true }));
  body.textContent = text;
  body.dispatchEvent(new win.FocusEvent('blur'));
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

// ---------- joining a board by link (?board=<id>) ----------

const EXISTING_ID = '11111111-1111-4111-8111-111111111111';
const MISSING_ID = '22222222-2222-4222-8222-222222222222';

function seedBoard(api, id = EXISTING_ID) {
  api.boards.set(id, {
    id,
    name: null,
    created_at: '2026-08-31T19:00:00Z',
    elements: [
      {
        id: 'el-pre',
        board_id: id,
        type: 'sticky_note',
        x: 10,
        y: 20,
        width: 160,
        height: 160,
        text: 'Joined!',
        created_at: '2026-08-31T19:00:01Z',
      },
    ],
  });
}

test('open ?board=<id>: joins the existing board, does NOT create a new one, shows the share link', async () => {
  const api = createMockApi();
  seedBoard(api);
  const dom = setupApp(api.fetch, `http://localhost/?board=${EXISTING_ID}`);
  const doc = dom.window.document;

  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  assert.equal(doc.getElementById('board').dataset.boardId, EXISTING_ID);
  assert.equal(
    api.calls.filter((c) => c.method === 'POST' && c.path === '/boards').length,
    0,
    'no new board should be created when joining by link'
  );
  assert.ok(
    api.calls.some((c) => c.method === 'GET' && c.path === `/boards/${EXISTING_ID}`),
    'GET /boards/{id} should be called'
  );

  const note = doc.querySelector('.el .note-body');
  assert.ok(note, 'sticky note from the joined board should be rendered');
  assert.equal(note.textContent, 'Joined!');

  const link = doc.getElementById('board-link');
  assert.ok(link.value.includes(`?board=${EXISTING_ID}`), 'share link should contain the board id');
  assert.equal(doc.getElementById('btn-copy-link').disabled, false, 'copy button should be enabled');
});

test('open ?board=<unknown>: shows an error, clears the bad id and creates a new board', async () => {
  const api = createMockApi();
  const dom = setupApp(api.fetch, `http://localhost/?board=${MISSING_ID}`);
  const doc = dom.window.document;

  await waitFor(() => doc.getElementById('error-banner').classList.contains('visible'));
  assert.match(doc.getElementById('error-banner').textContent, new RegExp(MISSING_ID));
  assert.match(doc.getElementById('error-banner').textContent, /не найдена/);

  // fallback: a fresh board is created and the URL now points to it
  await waitFor(() => doc.getElementById('board').dataset.boardId);
  const newId = doc.getElementById('board').dataset.boardId;
  assert.notEqual(newId, MISSING_ID, 'the bad id must not be reused');
  assert.equal(
    api.calls.filter((c) => c.method === 'POST' && c.path === '/boards').length,
    1,
    'exactly one new board should be created'
  );
  assert.ok(dom.window.location.search.includes('board='), 'URL should point to the new board');
  assert.ok(!dom.window.location.search.includes(MISSING_ID), 'bad id should be gone from the URL');
});

test('after creating a board: the URL and the share link contain ?board=<id>', async () => {
  const api = createMockApi();
  const dom = setupApp(api.fetch);
  const doc = dom.window.document;

  await waitFor(() => doc.getElementById('board').dataset.boardId);
  const bid = doc.getElementById('board').dataset.boardId;

  assert.equal(dom.window.location.search, `?board=${bid}`, 'URL should be updated to the board link');
  assert.equal(doc.getElementById('board-link').value, `http://localhost/?board=${bid}`);
  assert.equal(doc.getElementById('btn-copy-link').disabled, false);
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

// ---------- persistent editing (PATCH /elements/{id}) ----------

test('edit text on blur: sends PATCH {text} and the server state is updated', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);
  const bid = doc.getElementById('board').dataset.boardId;

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const node = doc.querySelector('.el.sticky');
  const id = node.dataset.id;
  const body = node.querySelector('.note-body');

  editText(doc.defaultView, body, 'Rate limiter notes');

  await waitFor(() => api.calls.some((c) => c.method === 'PATCH' && c.path === `/elements/${id}`));

  const patchCall = api.calls.find((c) => c.method === 'PATCH' && c.path === `/elements/${id}`);
  assert.deepEqual(JSON.parse(patchCall.body), { text: 'Rate limiter notes' }, 'PATCH body should carry only text');
  assert.equal(api.boards.get(bid).elements[0].text, 'Rate limiter notes', 'server state should reflect the edit');
});

test('edit with unchanged text: no PATCH is sent', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const body = doc.querySelector('.el.sticky .note-body');
  editText(doc.defaultView, body, ''); // same as the initial empty text

  await new Promise((r) => setTimeout(r, 30));
  assert.equal(api.calls.filter((c) => c.method === 'PATCH').length, 0, 'no PATCH for unchanged text');
});

test('drag: on pointerup sends PATCH {x, y} (only after movement)', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);
  const bid = doc.getElementById('board').dataset.boardId;

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const node = doc.querySelector('.el.sticky');
  const id = node.dataset.id;
  const origX = parseFloat(node.style.left);
  const origY = parseFloat(node.style.top);

  dragBy(doc.defaultView, node, 60, 40);

  await waitFor(() => api.calls.some((c) => c.method === 'PATCH' && c.path === `/elements/${id}`));

  const patchCall = api.calls.find((c) => c.method === 'PATCH' && c.path === `/elements/${id}`);
  const body = JSON.parse(patchCall.body);
  assert.equal(body.x, origX + 60, 'PATCH x should be the new left position');
  assert.equal(body.y, origY + 40, 'PATCH y should be the new top position');
  assert.equal(api.boards.get(bid).elements[0].x, origX + 60, 'server x should be updated');
  assert.equal(api.boards.get(bid).elements[0].y, origY + 40, 'server y should be updated');
});

test('click without movement: no PATCH for position', async () => {
  const api = createMockApi();
  const { doc } = await loadPage(api);

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const node = doc.querySelector('.el.sticky');
  pointerDownUp(doc.defaultView, node); // select, no move

  await new Promise((r) => setTimeout(r, 30));
  assert.equal(api.calls.filter((c) => c.method === 'PATCH').length, 0, 'no PATCH without movement');
});

test('PATCH 404 (element deleted by another client): logged, no banner, local text kept', async () => {
  const api = createMockApi();
  const { dom, doc } = await loadPage(api);
  const bid = doc.getElementById('board').dataset.boardId;

  const logs = [];
  dom.window.console.log = (...args) => logs.push(args.map(String).join(' '));

  click(doc.defaultView, doc.getElementById('btn-sticky'));
  await waitFor(() => doc.querySelectorAll('.el').length === 1);

  const body = doc.querySelector('.el.sticky .note-body');
  // another client deleted the element while this user was editing
  api.boards.get(bid).elements = [];

  editText(doc.defaultView, body, 'lost edit');

  await waitFor(() => logs.some((l) => l.includes('404')));
  assert.ok(logs.some((l) => l.includes('Element not found')), '404 detail should be logged');
  assert.equal(doc.getElementById('error-banner').classList.contains('visible'), false, 'no banner for 404');
  assert.equal(body.textContent, 'lost edit', 'local edit should stay visible (no rollback)');
});
