'use strict';

(function () {
  // Относительные пути: в проде фронтенд и API живут на одном origin
  // (FastAPI раздаёт статику). В dev — тоже: uvicorn на :8000 отдаёт и UI, и API.
  const API_BASE = '';

  const board = document.getElementById('board');
  const emptyHint = document.getElementById('empty-hint');
  const errorBanner = document.getElementById('error-banner');
  const boardLink = document.getElementById('board-link');
  const copyBtn = document.getElementById('btn-copy-link');

  const buttons = {
    sticky: document.getElementById('btn-sticky'),
    rect: document.getElementById('btn-rect'),
    circle: document.getElementById('btn-circle'),
  };

  // Размеры новых элементов — отправляются на сервер в POST /boards/{id}/elements
  const SIZES = {
    sticky: { width: 160, height: 160 },
    rect: { width: 180, height: 110 },
    circle: { width: 130, height: 130 }, // для круга width == height
  };

  // Типы из openapi.yaml -> CSS-классы прототипа
  const CLASS_BY_TYPE = {
    sticky_note: 'sticky',
    rectangle: 'rect',
    circle: 'circle',
  };

  // Ключи кнопок тулбара -> типы из openapi.yaml
  const API_TYPE = {
    sticky: 'sticky_note',
    rect: 'rectangle',
    circle: 'circle',
  };

  let boardId = null; // создаётся при загрузке страницы (POST /boards)
  let elements = [];  // кэш элементов, полученных с сервера
  let selectedId = null;
  let drag = null;

  // ---------- API ----------

  async function api(path, options = {}) {
    const res = await fetch(API_BASE + path, options);
    if (!res.ok) {
      const err = new Error(`HTTP ${res.status} ${res.statusText}`);
      err.status = res.status;
      err.body = await res.json().catch(() => null);
      throw err;
    }
    return res.status === 204 ? null : res.json();
  }

  // ---------- ошибки ----------

  function showError(message) {
    console.error('[Interview Canvas]', message);
    errorBanner.textContent = message;
    errorBanner.classList.add('visible');
    clearTimeout(showError._timer);
    showError._timer = setTimeout(() => errorBanner.classList.remove('visible'), 5000);
  }

  function errorDetail(err) {
    const d = err && err.body && err.body.detail;
    if (Array.isArray(d) && d.length) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
    if (typeof d === 'string') return d;
    return '';
  }

  function handleApiError(err, context) {
    if (err && err.status === 404) {
      // по ТЗ: 404 (доска/элемент не найдены) — только лог в консоль
      console.log(`[Interview Canvas] ${context}: 404 — ${errorDetail(err) || 'not found'}`);
      return;
    }
    const detail = errorDetail(err);
    const message = err && err.status
      ? `${context}: ${err.message}${detail ? ` — ${detail}` : ''}`
      : `${context}: сервер недоступен (${API_BASE}). Запусти бэкенд: uv run uvicorn backend.main:app --reload`;
    showError(message);
  }

  // ---------- загрузка ----------

  async function createBoard() {
    const data = await api('/boards', { method: 'POST' }); // без тела, как в ТЗ
    boardId = data.id;
    board.dataset.boardId = boardId; // удобно для отладки и тестов
    syncUrlWithBoard();
  }

  async function loadBoard() {
    const data = await api(`/boards/${boardId}`);
    elements = data.elements;
    renderAll();
    renderShareInfo();
  }

  // ---------- доска по ссылке (?board=<id>) ----------

  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function boardIdFromUrl() {
    const id = new URLSearchParams(window.location.search).get('board');
    return id && UUID_RE.test(id) ? id : null;
  }

  function syncUrlWithBoard() {
    const url = new URL(window.location.href);
    url.searchParams.set('board', boardId);
    url.hash = '';
    window.history.replaceState(null, '', url.toString());
  }

  function clearBoardIdFromUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete('board');
    window.history.replaceState(null, '', url.toString());
  }

  function shareUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set('board', boardId);
    url.hash = '';
    return url.toString();
  }

  function renderShareInfo() {
    const value = boardId ? shareUrl() : '';
    if (boardLink) boardLink.value = value;
    if (copyBtn) copyBtn.disabled = !boardId;
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const value = shareUrl();
      try {
        await navigator.clipboard.writeText(value);
      } catch (_) {
        // Clipboard API недоступна (http/file, старые браузеры) — fallback через execCommand
        try {
          const tmp = document.createElement('textarea');
          tmp.value = value;
          document.body.appendChild(tmp);
          tmp.select();
          document.execCommand('copy');
          tmp.remove();
        } catch (_) {
          /* пользователь скопирует ссылку из поля вручную */
        }
      }
    });
  }

  // ---------- мутации (после каждой — перезагрузка доски с сервера) ----------

  // PATCH /elements/{id}: partial update (x, y, text). Обновляет локальный
  // кэш ответом сервера; при ошибке показывает баннер, но НЕ откатывает
  // изменения — пользователь видит свой результат, а повторная попытка
  // произойдёт при следующем действии или перезагрузке страницы.
  async function updateElementOnServer(id, patch) {
    try {
      const updated = await api(`/elements/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      const idx = elements.findIndex((x) => String(x.id) === String(id));
      if (idx !== -1) elements[idx] = updated;
    } catch (err) {
      handleApiError(err, 'Сохранение изменений');
    }
  }

  async function addElementToServer(type) {
    if (!boardId) {
      showError('Доска ещё не создана. Проверь, что бэкенд запущен, и обнови страницу.');
      return;
    }
    const boardRect = board.getBoundingClientRect();
    const size = SIZES[type];
    // небольшой сдвиг от центра, чтобы новые элементы не ложились ровно друг на друга
    const offset = (elements.length % 8) * 24;
    const payload = {
      type: API_TYPE[type],
      x: Math.round(boardRect.width / 2 - size.width / 2 + offset),
      y: Math.round(boardRect.height / 2 - size.height / 2 + offset),
      width: size.width,
      height: size.height,
      text: type === 'sticky' ? '' : null, // text опционален; для фигур — null
    };
    try {
      await api(`/boards/${boardId}/elements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      await loadBoard();
    } catch (err) {
      handleApiError(err, 'Добавление элемента');
    }
  }

  async function deleteElementFromServer(id) {
    try {
      await api(`/elements/${id}`, { method: 'DELETE' });
      await loadBoard();
    } catch (err) {
      handleApiError(err, 'Удаление элемента');
    }
  }

  // ---------- отрисовка ----------

  function renderAll() {
    board.querySelectorAll('.el').forEach((node) => node.remove());
    selectedId = null;
    elements.forEach((el) => renderElement(el));
    updateEmptyHint();
  }

  function renderElement(el) {
    const node = document.createElement('div');
    node.className = 'el ' + (CLASS_BY_TYPE[el.type] || el.type);
    node.dataset.id = String(el.id);
    node.style.left = el.x + 'px';
    node.style.top = el.y + 'px';
    node.style.width = el.width + 'px';
    node.style.height = el.height + 'px';

    if (el.type === 'sticky_note') {
      const body = document.createElement('div');
      body.className = 'note-body';
      body.contentEditable = 'false';
      body.textContent = el.text || '';
      body.addEventListener('blur', () => stopEditing(el.id, body));
      node.appendChild(body);
      // dblclick вешаем на node, а не на .note-body: drag делает
      // setPointerCapture, и dblclick приходит с target = .el.
      node.addEventListener('dblclick', (e) => {
        if (e.target.closest('.delete-btn')) return;
        startEditing(el.id);
      });
    }

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'delete-btn';
    del.title = 'Delete';
    del.textContent = '\u00d7';
    node.appendChild(del);

    board.appendChild(node);
  }

  function updateEmptyHint() {
    emptyHint.style.display = elements.length ? 'none' : '';
  }

  function select(id) {
    if (selectedId != null) {
      const prev = board.querySelector('.el[data-id="' + selectedId + '"]');
      if (prev) prev.classList.remove('selected');
    }
    selectedId = id;
    const node = board.querySelector('.el[data-id="' + id + '"]');
    if (node) node.classList.add('selected');
  }

  function deselect() {
    if (selectedId != null) {
      const node = board.querySelector('.el[data-id="' + selectedId + '"]');
      if (node) node.classList.remove('selected');
      selectedId = null;
    }
  }

  // ---------- sticky note: редактирование текста (сохраняется PATCH'ем по blur) ----------

  function startEditing(id) {
    const node = board.querySelector('.el[data-id="' + id + '"]');
    if (!node) return;
    const body = node.querySelector('.note-body');
    if (!body) return;
    body.contentEditable = 'true';
    body.classList.add('editing');
    body.focus();
    const range = document.createRange();
    range.selectNodeContents(body);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function stopEditing(id, body) {
    body.contentEditable = 'false';
    body.classList.remove('editing');
    const el = elements.find((x) => String(x.id) === String(id));
    if (!el) return;
    const newText = body.textContent.trim();
    const changed = newText !== (el.text || '');
    el.text = newText; // локально — сразу, чтобы UI не «откатывался» при ошибке сети
    // Персистим на сервер по blur (не по каждому символу). Если текст не
    // менялся — запрос не шлём.
    if (changed && boardId) {
      updateElementOnServer(id, { text: newText });
    }
  }

  // ---------- drag (позиция персистится PATCH'ем по pointerup) ----------

  board.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.delete-btn')) return;

    const node = e.target.closest('.el');
    if (!node) {
      if (e.target === board || e.target === emptyHint) deselect();
      return;
    }

    const body = node.querySelector('.note-body');
    if (body && body.contentEditable === 'true') return; // редактируем текст — drag не начинаем

    const id = String(node.dataset.id);
    select(id);
    const el = elements.find((x) => String(x.id) === id);

    drag = {
      id,
      node,
      el,
      startX: e.clientX,
      startY: e.clientY,
      origX: parseFloat(node.style.left),
      origY: parseFloat(node.style.top),
      moved: false,
    };
    node.classList.add('dragging');
    node.style.zIndex = 1000;
    try {
      node.setPointerCapture(e.pointerId);
    } catch (_) {
      /* синтетические события в тестах могут не иметь pointerId */
    }
    // НЕ вызываем e.preventDefault() здесь: canceling pointerdown подавляет
    // генерацию click/dblclick, и двойной клик по стикеру не откроет редактор.
    // Запрет выделения/скролла включается в pointermove при реальном сдвиге.
  });

  window.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 3) return;
    if (!drag.moved) {
      // Драг реально начался — теперь запрещаем выделение/скролл.
      // (Раньше preventDefault был в pointerdown и ломал dblclick.)
      e.preventDefault();
    }
    drag.moved = true;
    const x = drag.origX + dx;
    const y = drag.origY + dy;
    drag.node.style.left = x + 'px';
    drag.node.style.top = y + 'px';
    if (drag.el) {
      drag.el.x = x;
      drag.el.y = y;
    }
  });

  window.addEventListener('pointerup', () => {
    if (!drag) return;
    const { id, node, moved } = drag;
    drag.node.classList.remove('dragging');
    drag.node.style.zIndex = '';
    drag = null;
    // Сохраняем позицию на сервер только по завершении движения (pointerup),
    // а не на каждый mousemove. Если элемент не двигался — запрос не шлём.
    if (moved && boardId) {
      updateElementOnServer(id, {
        x: parseFloat(node.style.left),
        y: parseFloat(node.style.top),
      });
    }
  });

  // ---------- delete button ----------

  board.addEventListener('click', (e) => {
    const del = e.target.closest('.delete-btn');
    if (!del) return;
    const node = del.closest('.el');
    if (node) deleteElementFromServer(String(node.dataset.id));
  });

  // ---------- keyboard ----------

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Delete' && e.key !== 'Backspace') return;
    const ae = document.activeElement;
    if (ae && (ae.isContentEditable || ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
    if (selectedId != null) {
      e.preventDefault();
      deleteElementFromServer(selectedId);
    }
  });

  // ---------- toolbar ----------

  Object.entries(buttons).forEach(([type, btn]) => {
    btn.addEventListener('click', () => addElementToServer(type));
  });

  // ---------- init: присоединиться по ссылке (?board=<id>) или создать новую доску ----------

  (async function init() {
    const joinId = boardIdFromUrl();
    if (joinId) {
      // пользователь открыл ссылку на существующую доску — не создаём новую
      boardId = joinId;
      board.dataset.boardId = joinId;
      try {
        await loadBoard();
      } catch (err) {
        if (err && err.status === 404) {
          // доски с таким id нет — показываем ошибку и создаём новую
          showError(`Доска ${joinId} не найдена. Создана новая доска.`);
          boardId = null;
          delete board.dataset.boardId;
          clearBoardIdFromUrl();
          try {
            await createBoard();
            await loadBoard();
          } catch (err2) {
            handleApiError(err2, 'Создание доски');
          }
        } else {
          handleApiError(err, 'Загрузка доски');
        }
      }
    } else {
      try {
        await createBoard();
        await loadBoard();
      } catch (err) {
        handleApiError(err, 'Создание доски');
      }
    }
  })();
})();
