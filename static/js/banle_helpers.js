/**
 * banle_helpers.js — Shared UI helpers for ban-le app
 *
 * - formatDateVN(): format ISO/string/Date to "DD/MM/YYYY" (Vietnamese)
 * - formatDateTimeVN(): format to "DD/MM/YYYY HH:mm"
 * - formatVND(): format number to "1.234.567 ₫" (Vietnamese accounting)
 * - formatNumberCompact(): "1.2K", "3.4M" abbreviations
 * - renderRowActions(): produce HTML for a 3-dot action menu
 * - bindRowActions(): attach click handlers to toggle menus
 * - statusPill(): produce HTML for a status pill
 * - showAlert(): simple toast alert
 *
 * Loaded automatically by base.html
 */

(function (window) {
  'use strict';

  // ---------------- DATE ----------------

  function formatDateVN(input) {
    if (input === null || input === undefined || input === '') return '—';
    const d = new Date(input);
    if (isNaN(d.getTime())) return '—';
    // Treat dates that map to 1970-01-01 (epoch zero) as "no data"
    if (d.getUTCFullYear() <= 1970) return '—';
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  }

  function formatDateTimeVN(input) {
    if (input === null || input === undefined || input === '') return '—';
    const d = new Date(input);
    if (isNaN(d.getTime())) return '—';
    if (d.getUTCFullYear() <= 1970) return '—';
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    return `${dd}/${mm}/${yyyy} ${hh}:${mi}`;
  }

  // ---------------- NUMBER ----------------

  function formatVND(n) {
    if (n === null || n === undefined || n === '' || isNaN(Number(n))) return '—';
    const num = Number(n);
    if (num === 0) return '0 ₫';
    // Use vi-VN locale for thousands separator
    return num.toLocaleString('vi-VN') + ' ₫';
  }

  function formatNumberCompact(n) {
    if (n === null || n === undefined || n === '' || isNaN(Number(n))) return '—';
    const num = Number(n);
    const abs = Math.abs(num);
    if (abs >= 1e9) return (num / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (abs >= 1e6) return (num / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (abs >= 1e3) return (num / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return num.toLocaleString('vi-VN');
  }

  // ---------------- STATUS PILL ----------------

  function statusPill(label, tone) {
    const t = tone || 'gray';
    return `<span class="status-pill status-pill--${t}"><span class="status-pill__dot"></span>${label}</span>`;
  }

  // ---------------- ROW ACTIONS (3-dot menu) ----------------

  /**
   * Render a 3-dot action menu.
   * @param {string|number} rowId - unique row identifier (used for element ids)
   * @param {Array<{label:string, icon?:string, action?:string, danger?:boolean, divider?:boolean}>} items
   *   - If `divider: true`, renders a separator.
   *   - If `action` starts with "fn:", the rest is treated as a JS function call (rowId is appended as arg).
   *   - If `action` is a function name, the row id is passed as argument.
   * @returns {string} HTML
   */
  function renderRowActions(rowId, items) {
    if (!items || items.length === 0) return '<span class="text-muted">—</span>';

    const safeId = String(rowId).replace(/[^a-zA-Z0-9_-]/g, '_');
    const menuId = `rowActions-${safeId}`;
    const itemsHtml = items
      .map((item) => {
        if (item.divider) return '<div class="row-actions__divider"></div>';
        const dangerCls = item.danger ? ' row-actions__item--danger' : '';
        const icon = item.icon ? `<i class="${item.icon}"></i>` : '';
        const action = item.action || '';
        return `<button type="button" class="row-actions__item${dangerCls}" data-action="${escapeAttr(action)}">${icon}<span>${escapeHtml(item.label)}</span></button>`;
      })
      .join('');

    return `
      <div class="row-actions" data-row-id="${escapeAttr(rowId)}">
        <button type="button" class="row-actions__btn" aria-label="Thao tác" data-menu-toggle>
          <i class="fa-solid fa-ellipsis-vertical"></i>
        </button>
        <div class="row-actions__menu" role="menu" id="${menuId}">
          ${itemsHtml}
        </div>
      </div>
    `;
  }

  /**
   * Bind click handlers for all row action menus on the page.
   * - Toggle .row-actions--open when the ellipsis button is clicked
   * - Close any other open menu
   * - Close on outside click / Escape
   * - Invoke the function specified in data-action with the row id
   *
   * Convention for data-action:
   *   "editManager"         -> calls window.editManager(rowId)
   *   "fn:confirmRemove"    -> calls window.confirmRemove(rowId)
   *   "url:/admin/foo"      -> navigates to URL with rowId appended as ?id=
   */
  function bindRowActions(rootEl) {
    const root = rootEl || document;
    // Toggle handlers
    root.querySelectorAll('.row-actions [data-menu-toggle]').forEach(function (btn) {
      if (btn.__banleBound) return;
      btn.__banleBound = true;
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const wrapper = btn.closest('.row-actions');
        const wasOpen = wrapper.classList.contains('row-actions--open');
        // Close all
        document.querySelectorAll('.row-actions--open').forEach(function (el) {
          el.classList.remove('row-actions--open');
        });
        if (!wasOpen) wrapper.classList.add('row-actions--open');
      });
    });
    // Item handlers
    root.querySelectorAll('.row-actions__item').forEach(function (item) {
      if (item.__banleBound) return;
      item.__banleBound = true;
      item.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const wrapper = item.closest('.row-actions');
        const rowId = wrapper ? wrapper.getAttribute('data-row-id') : null;
        const action = item.getAttribute('data-action') || '';
        wrapper.classList.remove('row-actions--open');
        if (action.startsWith('url:')) {
          const url = action.slice(4);
          window.location.href = url + (url.includes('?') ? '&' : '?') + 'id=' + encodeURIComponent(rowId);
          return;
        }
        const fnName = action.startsWith('fn:') ? action.slice(3) : action;
        if (typeof window[fnName] === 'function') {
          window[fnName](rowId);
        } else if (typeof console !== 'undefined') {
          console.warn('[banle] action handler not found:', fnName);
        }
      });
    });
  }

  // Close menus on outside click / Escape
  document.addEventListener('click', function () {
    document.querySelectorAll('.row-actions--open').forEach(function (el) {
      el.classList.remove('row-actions--open');
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.row-actions--open').forEach(function (el) {
        el.classList.remove('row-actions--open');
      });
    }
  });

  // ---------------- TABLE THEME SYNC (CSS-ONLY) ----------------

  /**
   * Clear any stale inline styles from older code versions.
   * The actual theme colors are handled entirely by CSS rules in `app.css`:
   *   - [data-theme="dark"] .table tbody td { color: #fff !important; }
   *   - :root .table tbody td { color: #003152 !important; }
   * This avoids the timing race condition where JS setProperty() reads
   * getComputedStyle() BEFORE the browser re-evaluates CSS variables
   * on theme change, leaving the table stuck in the previous theme.
   *
   * CSS-only is the most robust solution — the browser handles theme
   * transitions natively, with no JS timing dependency.
   */
  function syncAllTablesTheme() {
    document.querySelectorAll('table, table tbody tr, table thead th, table tbody td').forEach((el) => {
      el.style.removeProperty('background');
      el.style.removeProperty('background-color');
      el.style.removeProperty('color');
      el.style.removeProperty('border-color');
    });
  }

  // Auto-run on load (clears any stale inline styles from older versions)
  document.addEventListener('DOMContentLoaded', function () {
    syncAllTablesTheme();
  });

  // Re-clear when theme attribute changes (in case old inline styles leaked)
  new MutationObserver(function (mutations) {
    for (const m of mutations) {
      if (m.attributeName === 'data-theme') {
        syncAllTablesTheme();
        break;
      }
    }
  }).observe(document.documentElement, { attributes: true });

  // Re-clear whenever new tables are added to the DOM
  new MutationObserver(function (mutations) {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1 && (node.tagName === 'TABLE' || (node.querySelector && node.querySelector('table')))) {
          syncAllTablesTheme();
          return;
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true });

  // ---------------- SKELETON ----------------

  /**
   * Render a loading placeholder (skeleton block).
   * @param {string} type - 'text' | 'text-sm' | 'text-lg' | 'circle' | 'avatar' | 'btn' | 'full'
   * @param {Object} opts - { count, className, style }
   * @returns {string} HTML
   */
  function renderSkeleton(type, opts) {
    const o = opts || {};
    const cls = 'skeleton skeleton--' + (type || 'text') + (o.className ? ' ' + o.className : '');
    const style = o.style || '';
    return `<span class="${cls}"${style ? ' style="' + style + '"' : ''}></span>`;
  }

  /**
   * Render a list of skeleton rows for a loading table.
   * @param {number} rows - number of skeleton rows (default 5)
   * @param {number} cols - number of skeleton text blocks per row (default 3)
   * @returns {string} HTML
   */
  function renderTableSkeleton(rows, cols) {
    const r = rows || 5;
    const c = cols || 3;
    let html = '<div class="table-skeleton">';
    for (let i = 0; i < r; i++) {
      html += '<div class="skeleton-row">';
      html += '<span class="skeleton skeleton--avatar"></span>';
      html += '<div class="skeleton-row__body">';
      for (let j = 0; j < c; j++) {
        const w = j === 0 ? '70%' : (j === c - 1 ? '40%' : '85%');
        html += `<span class="skeleton skeleton--text" style="width: ${w};"></span>`;
      }
      html += '</div></div>';
    }
    html += '</div>';
    return html;
  }

  /**
   * Render a simple spinner (for inline loading).
   * @returns {string} HTML
   */
  function renderSpinner(label) {
    const lbl = label || 'Đang tải...';
    return `<div class="empty-state empty-state--compact">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 24px; color: var(--text-muted);"></i>
      <p class="empty-state__description" style="margin-top: 12px;">${escapeHtml(lbl)}</p>
    </div>`;
  }

  // ---------------- ESCAPING ----------------

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeAttr(s) {
    return escapeHtml(s);
  }

  // ---------------- ALERT ----------------

  function showAlert(type, message, duration) {
    const main = document.querySelector('main') || document.body;
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert--' + (type === 'success' ? 'success' : type === 'error' ? 'error' : 'info');
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 280px; max-width: 420px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.15);';
    alertDiv.innerHTML = `
      <i class="fa-solid fa-${type === 'success' ? 'circle-check' : type === 'error' ? 'circle-exclamation' : 'circle-info'}"></i>
      <div class="alert__content">
        <p class="alert__message">${escapeHtml(message)}</p>
      </div>
      <button type="button" class="alert__close" onclick="this.parentElement.remove()" aria-label="Đóng">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;
    main.appendChild(alertDiv);
    const ttl = duration || (type === 'error' ? 8000 : 4000);
    setTimeout(() => {
      if (alertDiv.parentElement) alertDiv.remove();
    }, ttl);
  }

  // ---------------- EXPORT ----------------

  window.banleUI = {
    formatDateVN: formatDateVN,
    formatDateTimeVN: formatDateTimeVN,
    formatVND: formatVND,
    formatNumberCompact: formatNumberCompact,
    statusPill: statusPill,
    renderRowActions: renderRowActions,
    bindRowActions: bindRowActions,
    renderSkeleton: renderSkeleton,
    renderTableSkeleton: renderTableSkeleton,
    renderSpinner: renderSpinner,
    showAlert: showAlert,
    escapeHtml: escapeHtml,
    escapeAttr: escapeAttr,
    syncAllTablesTheme: syncAllTablesTheme,
  };
})(window);
