'use strict';

(function () {
  const board = document.getElementById('board');
  const emptyHint = document.getElementById('empty-hint');

  const buttons = {
    sticky: document.getElementById('btn-sticky'),
    rect: document.getElementById('btn-rect'),
    circle: document.getElementById('btn-circle'),
  };

  let nextId = 1;
  let elements = [];
  let selectedId = null;
  let cascade = 0; // сдвиг новых элементов, чтобы не ложились друг на друга
  let drag = null;

  // ---------- helpers ----------

  function findElement(id) {
    return elements.find((el) => el.id === id);
  }

  function nodeFor(id) {
    return board.querySelector('.el[data-id="' + id + '"]');
  }

  function updateEmptyHint() {
    emptyHint.style.display = elements.length ? 'none' : '';
  }

  function select(id) {
    if (selectedId != null) {
      const prev = nodeFor(selectedId);
      if (prev) prev.classList.remove('selected');
    }
    selectedId = id;
    const node = nodeFor(id);
    if (node) node.classList.add('selected');
  }

  function deselect() {
    if (selectedId != null) {
      const node = nodeFor(selectedId);
      if (node) node.classList.remove('selected');
      selectedId = null;
    }
  }

  function deleteElement(id) {
    const node = nodeFor(id);
    if (node) node.remove();
    elements = elements.filter((el) => el.id !== id);
    if (selectedId === id) selectedId = null;
    updateEmptyHint();
  }

  // ---------- create ----------

  function createElement(type) {
    const boardRect = board.getBoundingClientRect();
    const id = nextId;
    nextId += 1;

    const node = document.createElement('div');
    node.className = 'el ' + type;
    node.dataset.id = String(id);
    node.style.visibility = 'hidden'; // позиционируем до показа, чтобы не мигнуть в (0,0)

    if (type === 'sticky') {
      const body = document.createElement('div');
      body.className = 'note-body';
      body.contentEditable = 'false';
      body.addEventListener('dblclick', () => startEditing(id));
      body.addEventListener('blur', () => stopEditing(id, body));
      node.appendChild(body);
    }

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'delete-btn';
    del.title = 'Delete';
    del.textContent = '\u00d7';
    node.appendChild(del);

    board.appendChild(node);

    // размеры берём из CSS (единственный источник правды)
    const w = node.offsetWidth;
    const h = node.offsetHeight;

    const offset = (cascade % 8) * 24;
    cascade += 1;

    const el = {
      id,
      type,
      x: Math.round(boardRect.width / 2 - w / 2 + offset),
      y: Math.round(boardRect.height / 2 - h / 2 + offset),
      text: '',
    };
    elements.push(el);

    node.style.left = el.x + 'px';
    node.style.top = el.y + 'px';
    node.style.visibility = 'visible';

    select(id);
    updateEmptyHint();
  }

  // ---------- sticky note editing ----------

  function startEditing(id) {
    const node = nodeFor(id);
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
    const el = findElement(id);
    if (el) el.text = body.textContent.trim();
  }

  // ---------- drag & selection ----------

  board.addEventListener('pointerdown', (e) => {
    // кнопка удаления — отдельный сценарий, drag не начинаем
    if (e.target.closest('.delete-btn')) return;

    const node = e.target.closest('.el');
    if (!node) {
      if (e.target === board || e.target === emptyHint) deselect();
      return;
    }

    const body = node.querySelector('.note-body');
    // во время редактирования текста drag не запускаем, даём работать каретке
    if (body && body.contentEditable === 'true') return;

    const id = Number(node.dataset.id);
    const el = findElement(id);
    select(id);

    drag = {
      id,
      node,
      el,
      startX: e.clientX,
      startY: e.clientY,
      origX: el.x,
      origY: el.y,
      moved: false,
    };
    node.classList.add('dragging');
    node.style.zIndex = 1000;
    try {
      node.setPointerCapture(e.pointerId);
    } catch (_) {
      /* синтетические события в тестах могут не иметь pointerId */
    }
    e.preventDefault();
  });

  window.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 3) return; // порог: клик vs перетаскивание
    drag.moved = true;
    drag.el.x = drag.origX + dx;
    drag.el.y = drag.origY + dy;
    drag.node.style.left = drag.el.x + 'px';
    drag.node.style.top = drag.el.y + 'px';
  });

  window.addEventListener('pointerup', () => {
    if (!drag) return;
    drag.node.classList.remove('dragging');
    drag.node.style.zIndex = '';
    drag = null;
  });

  // ---------- delete button ----------

  board.addEventListener('click', (e) => {
    const del = e.target.closest('.delete-btn');
    if (!del) return;
    const node = del.closest('.el');
    if (node) deleteElement(Number(node.dataset.id));
  });

  // ---------- keyboard ----------

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Delete' && e.key !== 'Backspace') return;
    const ae = document.activeElement;
    if (ae && (ae.isContentEditable || ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
    if (selectedId != null) {
      e.preventDefault();
      deleteElement(selectedId);
    }
  });

  // ---------- toolbar ----------

  Object.entries(buttons).forEach(([type, btn]) => {
    btn.addEventListener('click', () => createElement(type));
  });
})();
